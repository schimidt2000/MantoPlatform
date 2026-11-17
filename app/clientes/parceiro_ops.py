"""Parceiros: buffet, assessoria, agência ou outro, com a comissão declarada (feature 350).

Núcleo puro, sem commit. A comissão é só declarada (`Parceiro`): nada aqui paga ninguém. Não se
exclui parceiro — desativa-se.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func

from app import db
from app.clientes.client_ops import ClientValidationError
from app.constants import PARCEIRO_TIPOS, now_sp
from app.models import Client, Parceiro

NOME_MINIMO = 2
NOME_MAXIMO = 160
COMISSAO_MAXIMA = Decimal("100")
CENTESIMO = Decimal("0.01")
# Campo de texto opcional → limite da coluna.
_TEXTOS_OPCIONAIS = {"contato": 120, "telefone": 30, "email": 200}


def tipos() -> list[dict[str, str]]:
    """As opções do tipo, na ordem de exibição."""
    return [{"valor": valor, "rotulo": rotulo} for valor, rotulo in PARCEIRO_TIPOS.items()]


def _nome(valor: Any) -> str:
    nome = " ".join(str(valor or "").split())
    if len(nome) < NOME_MINIMO:
        raise ClientValidationError("nome", "Informe o nome do parceiro.")
    if len(nome) > NOME_MAXIMO:
        raise ClientValidationError("nome", f"Use até {NOME_MAXIMO} caracteres.")
    return nome


def _tipo(valor: Any) -> str:
    tipo = str(valor or "").strip()
    if tipo not in PARCEIRO_TIPOS:
        raise ClientValidationError("tipo", "Selecione o tipo do parceiro.")
    return tipo


def _comissao(valor: Any) -> Decimal:
    texto = str(valor if valor is not None else "0").strip().replace("%", "").replace(",", ".")
    try:
        comissao = Decimal(texto or "0")
    except InvalidOperation:
        raise ClientValidationError("comissao_percentual", "Informe a comissão em %.") from None
    if not comissao.is_finite() or comissao < 0 or comissao > COMISSAO_MAXIMA:
        raise ClientValidationError("comissao_percentual", "A comissão vai de 0% a 100%.")
    return comissao.quantize(CENTESIMO, rounding=ROUND_HALF_UP)


def _texto(valor: Any, limite: int, campo: str) -> str | None:
    texto = str(valor or "").strip()
    if len(texto) > limite:
        raise ClientValidationError(campo, f"Use até {limite} caracteres.")
    return texto or None


def _aplicar(parceiro: Parceiro, dados: dict[str, Any], *, parcial: bool) -> None:
    if not parcial or "nome" in dados:
        parceiro.nome = _nome(dados.get("nome"))
    if not parcial or "tipo" in dados:
        parceiro.tipo = _tipo(dados.get("tipo"))
    if not parcial or "comissao_percentual" in dados:
        parceiro.comissao_percentual = _comissao(dados.get("comissao_percentual"))
    for campo, limite in _TEXTOS_OPCIONAIS.items():
        if not parcial or campo in dados:
            setattr(parceiro, campo, _texto(dados.get(campo), limite, campo))
    if not parcial or "observacao" in dados:
        parceiro.observacao = str(dados.get("observacao") or "").strip() or None
    if parcial and "ativo" in dados:
        parceiro.ativo = dados.get("ativo") is True


def criar(dados: dict[str, Any]) -> Parceiro:
    """Cria o parceiro (ativo)."""
    parceiro = Parceiro(ativo=True, criado_em=now_sp(), atualizado_em=now_sp())
    _aplicar(parceiro, dados, parcial=False)
    db.session.add(parceiro)
    db.session.flush()
    return parceiro


def atualizar(parceiro: Parceiro, dados: dict[str, Any]) -> Parceiro:
    """Muda só as chaves presentes no corpo (inclusive ``ativo``)."""
    _aplicar(parceiro, dados, parcial=True)
    parceiro.atualizado_em = now_sp()
    db.session.flush()
    return parceiro


def listar(*, incluir_inativos: bool) -> list[tuple[Parceiro, int]]:
    """Os parceiros em ordem de nome, cada um com quantas fichas trouxe."""
    contagem = (
        db.session.query(Client.parceiro_id, func.count(Client.id))
        .filter(Client.parceiro_id.isnot(None))
        .group_by(Client.parceiro_id)
        .all()
    )
    por_parceiro = dict(contagem)
    consulta = Parceiro.query.order_by(Parceiro.nome)
    if not incluir_inativos:
        consulta = consulta.filter(Parceiro.ativo.is_(True))
    return [(p, por_parceiro.get(p.id, 0)) for p in consulta.all()]


def serializar(parceiro: Parceiro, clientes: int) -> dict[str, Any]:
    """O parceiro para a tela; a comissão vai como texto decimal ("10.00")."""
    return {
        "id": parceiro.id,
        "nome": parceiro.nome,
        "tipo": parceiro.tipo,
        "tipo_label": PARCEIRO_TIPOS.get(parceiro.tipo, parceiro.tipo),
        "contato": parceiro.contato,
        "telefone": parceiro.telefone,
        "email": parceiro.email,
        "comissao_percentual": str(parceiro.comissao_percentual),
        "observacao": parceiro.observacao,
        "ativo": bool(parceiro.ativo),
        "clientes": clientes,
    }
