"""Cadastro de fornecedores dos gastos extras (feature 352).

Núcleo puro (sem `flask.request`). O gasto continua guardando o nome e a chave PIX com que foi
lançado (`SpecialExpense.supplier_name`/`supplier_pix` — é o que a Planilha de Pagamentos paga); o
cadastro só PREENCHE o gasto e dá nome único às grafias do mesmo fornecedor. Regras:

- "mesmo fornecedor" = mesmo `normalizar_nome` (banco: `UNIQUE(nome_normalizado)`);
- o gasto liga pelo id escolhido, senão pelo nome, senão cadastra (`resolver_para_gasto`);
- ligar completa o PIX e a categoria que faltam no cadastro, nunca substitui;
- renomear e juntar reescrevem o nome dos gastos ligados, nunca o PIX deles.

`gastos_ops` importa este módulo; a auditoria daqui usa `gastos_ops._log` por import tardio.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Fornecedor, SpecialExpense, User
from app.utils import strip_accents_lower

#: As categorias que a pessoa escolhe no gasto. "Devolução a cliente" e "Multa de cancelamento"
#: nascem só pelo cancelamento do evento (feature 306): nunca são padrão de um fornecedor.
CATEGORIAS_DO_FORNECEDOR: tuple[str, ...] = tuple(
    c
    for c in SpecialExpense.CATEGORIES
    if c not in (SpecialExpense.CATEGORY_DEVOLUCAO, SpecialExpense.CATEGORY_MULTA_CANCELAMENTO)
)

TAMANHO_NOME = 200
TAMANHO_PIX = 120
DESEMBOLSO_FORNECEDOR = "fornecedor"

MSG_NOME_VAZIO = "Informe o nome do fornecedor."
MSG_NOME_REPETIDO = "Já existe um fornecedor com este nome."
MSG_CATEGORIA = "Selecione uma categoria da lista."
MSG_DESTINO = "Selecione outro fornecedor."


class FornecedorValidationError(Exception):
    """Dado inválido no cadastro; `field` é a chave de `fields` que a tela aponta."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def normalizar_nome(texto: str | None) -> str:
    """Chave de "mesmo fornecedor": sem acento, minúsculas, pontuação e espaço viram um espaço.

    "Ramon / Real Produções" e "Ramon/real produções" dão `ramon real producoes`. A migration
    `f352a1b2c3d4` tem uma cópia (não importa `app/`); o verify_352 confere que as duas batem.
    """
    return re.sub(r"[^a-z0-9]+", " ", strip_accents_lower(texto or "")).strip()


def limpar_nome(texto: str | None) -> str:
    """Nome como será gravado: espaços colapsados, até `TAMANHO_NOME`."""
    return " ".join((texto or "").split())[:TAMANHO_NOME]


def limpar_pix(texto: str | None) -> str | None:
    """Chave PIX como digitada (sem bordas), ou `None` se vazia."""
    return (texto or "").strip()[:TAMANHO_PIX] or None


def categoria_valida(categoria: str | None) -> str | None:
    """A categoria se for uma das escolhíveis; senão `None`."""
    return categoria if categoria in CATEGORIAS_DO_FORNECEDOR else None


def fornecedor_por_nome(nome: str | None) -> Fornecedor | None:
    """O fornecedor (ativo ou arquivado) com o mesmo nome normalizado, se houver."""
    normalizado = normalizar_nome(nome)
    if not normalizado:
        return None
    return Fornecedor.query.filter_by(nome_normalizado=normalizado).first()


def _tocar(fornecedor: Fornecedor) -> None:
    fornecedor.updated_at = datetime.utcnow()


def _registrar(ator: User | None, fornecedor: Fornecedor, acao: str, detalhe: str) -> None:
    """Auditoria no mesmo log dos gastos. Import tardio: `gastos_ops` importa este módulo."""
    if ator is None:
        return
    from app.gastos.gastos_ops import _log

    _log(ator, "fornecedor", fornecedor.id, fornecedor.nome, acao, detalhe)


# ══════════════════════════════════════════════════════════════════
#  Leitura
# ══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Totais:
    """Quanto o fornecedor já pesou: gastos ligados, soma dos aprovados, data do último gasto."""

    gastos: int = 0
    total_aprovado: Decimal = Decimal("0")
    ultimo_gasto: date | None = None


def _totais_por_fornecedor() -> dict[int, Totais]:
    """Uma consulta agregada para a lista inteira (nunca uma por fornecedor)."""
    aprovado = case((SpecialExpense.status == "aprovado", SpecialExpense.amount), else_=0)
    linhas = (
        db.session.query(
            SpecialExpense.fornecedor_id,
            func.count(SpecialExpense.id),
            func.coalesce(func.sum(aprovado), 0),
            func.max(SpecialExpense.expense_date),
        )
        .filter(SpecialExpense.fornecedor_id.isnot(None))
        .group_by(SpecialExpense.fornecedor_id)
        .all()
    )
    return {fid: Totais(qtd, Decimal(str(soma)), ultimo) for fid, qtd, soma, ultimo in linhas}


def listar(*, apenas_ativos: bool, com_totais: bool) -> list[tuple[Fornecedor, Totais | None]]:
    """Fornecedores em ordem alfabética sem acento, com os totais quando pedidos.

    Args:
        apenas_ativos: só os não arquivados (o que quem lança gasto vê).
        com_totais: soma gastos/aprovado/último por fornecedor (só para Financeiro/Superadmin).
    """
    query = Fornecedor.query
    if apenas_ativos:
        query = query.filter(Fornecedor.ativo.is_(True))
    fornecedores = sorted(query.all(), key=lambda f: f.nome_normalizado)
    if not com_totais:
        return [(f, None) for f in fornecedores]
    totais = _totais_por_fornecedor()
    return [(f, totais.get(f.id, Totais())) for f in fornecedores]


# ══════════════════════════════════════════════════════════════════
#  O gasto liga ao fornecedor (chamado por gastos_ops)
# ══════════════════════════════════════════════════════════════════


def _por_id(fornecedor_id: object) -> Fornecedor | None:
    try:
        return (
            db.session.get(Fornecedor, int(fornecedor_id))
            if fornecedor_id not in (None, "")
            else None
        )
    except (TypeError, ValueError):
        return None


def _completar(fornecedor: Fornecedor, pix: str | None, categoria: str | None) -> None:
    """O gasto completa o cadastro que está sem PIX ou sem categoria; nunca troca o que existe."""
    mudou = False
    if not fornecedor.pix and limpar_pix(pix):
        fornecedor.pix = limpar_pix(pix)
        mudou = True
    if not fornecedor.categoria_padrao and categoria_valida(categoria):
        fornecedor.categoria_padrao = categoria
        mudou = True
    if mudou:
        _tocar(fornecedor)


def _cadastrar_pelo_gasto(
    nome: str, pix: str | None, categoria: str | None, ator: User | None
) -> Fornecedor | None:
    """Fornecedor novo a partir do gasto. Num SAVEPOINT: se outra pessoa cadastrou o mesmo nome no
    mesmo instante, o `UNIQUE` recusa, o savepoint se desfaz (o gasto em curso continua) e o gasto
    liga ao que ela criou."""
    nome_limpo = limpar_nome(nome)
    normalizado = normalizar_nome(nome_limpo)
    if not normalizado:
        return None
    novo = Fornecedor(
        nome=nome_limpo,
        nome_normalizado=normalizado,
        pix=limpar_pix(pix),
        categoria_padrao=categoria_valida(categoria),
        criado_por_id=ator.id if ator else None,
    )
    try:
        with db.session.begin_nested():
            db.session.add(novo)
    except IntegrityError:
        return fornecedor_por_nome(nome_limpo)
    _registrar(ator, novo, "create", "Fornecedor cadastrado ao lançar um gasto")
    return novo


def resolver_para_gasto(
    fornecedor_id: object, nome: str, pix: str | None, categoria: str | None, ator: User | None
) -> Fornecedor | None:
    """O fornecedor do gasto: o escolhido, senão o de mesmo nome, senão um novo (FR-005/FR-006).

    Não faz commit — roda dentro da transação do gasto. Devolve `None` só para nome sem letra nem
    número (o gasto fica sem vínculo, como antes da 352).
    """
    fornecedor = _por_id(fornecedor_id) or fornecedor_por_nome(nome)
    if fornecedor is None:
        return _cadastrar_pelo_gasto(nome, pix, categoria, ator)
    _completar(fornecedor, pix, categoria)
    return fornecedor


# ══════════════════════════════════════════════════════════════════
#  Tela do Financeiro: cadastrar, alterar, juntar
# ══════════════════════════════════════════════════════════════════


def _exigir_nome_livre(nome: str, proprio_id: int | None) -> None:
    if not normalizar_nome(nome):
        raise FornecedorValidationError("nome", MSG_NOME_VAZIO)
    existente = fornecedor_por_nome(nome)
    if existente is not None and existente.id != proprio_id:
        raise FornecedorValidationError("nome", MSG_NOME_REPETIDO)


def _ler_categoria(valor: object) -> str | None:
    if valor in (None, ""):
        return None
    if valor not in CATEGORIAS_DO_FORNECEDOR:
        raise FornecedorValidationError("categoria_padrao", MSG_CATEGORIA)
    return str(valor)


def _gravar(ator: User, fornecedor: Fornecedor, acao: str, detalhe: str) -> None:
    """Commit com a corrida do nome traduzida para o campo (o `UNIQUE` é a última palavra)."""
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise FornecedorValidationError("nome", MSG_NOME_REPETIDO) from None
    _registrar(ator, fornecedor, acao, detalhe)
    db.session.commit()


def cadastrar(dados: dict, ator: User) -> Fornecedor:
    """Cadastro pela tela do Financeiro (`nome`, `pix`, `categoria_padrao`)."""
    nome = limpar_nome(dados.get("nome"))
    _exigir_nome_livre(nome, None)
    fornecedor = Fornecedor(
        nome=nome,
        nome_normalizado=normalizar_nome(nome),
        pix=limpar_pix(dados.get("pix")),
        categoria_padrao=_ler_categoria(dados.get("categoria_padrao")),
        criado_por_id=ator.id,
    )
    db.session.add(fornecedor)
    _gravar(ator, fornecedor, "create", "Fornecedor cadastrado")
    return fornecedor


def _renomear(fornecedor: Fornecedor, nome: str) -> None:
    """O nome novo vale também nos gastos ligados (o PIX deles fica: é o do lançamento)."""
    fornecedor.nome = nome
    fornecedor.nome_normalizado = normalizar_nome(nome)
    SpecialExpense.query.filter_by(fornecedor_id=fornecedor.id).update(
        {"supplier_name": nome}, synchronize_session=False
    )


def alterar(fornecedor: Fornecedor, dados: dict, ator: User) -> Fornecedor:
    """Altera só as chaves presentes: `nome`, `pix`, `categoria_padrao`, `ativo`."""
    mudancas: list[str] = []
    if "nome" in dados:
        nome = limpar_nome(dados.get("nome"))
        _exigir_nome_livre(nome, fornecedor.id)
        if nome != fornecedor.nome:
            mudancas.append(f"nome: {fornecedor.nome} → {nome}")
            _renomear(fornecedor, nome)
    if "pix" in dados:
        fornecedor.pix = limpar_pix(dados.get("pix"))
        mudancas.append("chave PIX")
    if "categoria_padrao" in dados:
        fornecedor.categoria_padrao = _ler_categoria(dados.get("categoria_padrao"))
        mudancas.append("categoria padrão")
    if "ativo" in dados:
        fornecedor.ativo = bool(dados.get("ativo"))
        mudancas.append("reativado" if fornecedor.ativo else "arquivado")
    _tocar(fornecedor)
    _gravar(
        ator, fornecedor, "edit", "Fornecedor alterado: " + (", ".join(mudancas) or "sem mudança")
    )
    return fornecedor


def juntar(origem: Fornecedor, destino_id: object, ator: User) -> tuple[Fornecedor, int]:
    """Junta `origem` em `destino`: os gastos passam com o nome do destino, o destino completa PIX e
    categoria que não tinha, a origem deixa de existir.

    As duas linhas travam em `ORDER BY id` (`docs/00` §6.25): dois "juntar" cruzados não fecham ciclo.

    Returns:
        O destino e quantos gastos passaram para ele.
    """
    destino = _por_id(destino_id)
    if destino is None or destino.id == origem.id:
        raise FornecedorValidationError("destino_id", MSG_DESTINO)
    db.session.flush()
    travados = (
        Fornecedor.query.filter(Fornecedor.id.in_([origem.id, destino.id]))
        .order_by(Fornecedor.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    if len(travados) < 2:
        raise FornecedorValidationError("destino_id", MSG_DESTINO)
    movidos = SpecialExpense.query.filter_by(fornecedor_id=origem.id).update(
        {"fornecedor_id": destino.id, "supplier_name": destino.nome}, synchronize_session=False
    )
    _completar(destino, origem.pix, origem.categoria_padrao)
    _tocar(destino)
    _registrar(
        ator, destino, "merge", f"“{origem.nome}” juntado a este fornecedor ({movidos} gastos)"
    )
    db.session.delete(origem)
    db.session.commit()
    return destino, movidos
