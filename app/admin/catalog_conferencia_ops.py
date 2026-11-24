"""Núcleo da conferência de personagens do catálogo (feature 360).

A leitura assistida das fotos propôs, para cada item do catálogo sem elenco e sem ficha, o tipo do
item e os personagens que aparecem. Este módulo guarda a proposta, calcula a fila do que ainda está
pendente e registra o que a pessoa que confere decide.

Três regras que valem para o módulo inteiro:

* **A conferência não toca o catálogo.** Nada aqui escreve em ``catalog_items``,
  ``catalog_characters``, ``catalog_item_images`` nem ``figurino_sheets``. Gravar o conferido é a
  feature seguinte, que lê estas tabelas.
* **A fila é uma consulta, não uma lista guardada** (``filtro_da_fila``): item que ganha elenco ou
  ficha no catálogo some sozinho; item novo aparece como "sem leitura".
* **Conferido trava.** Toda escrita relê a conferência com ``FOR UPDATE`` e recusa item conferido,
  para o "conferir" de uma pessoa não cruzar com a edição de outra.

Puro: não importa ``flask.request``. As rotas ficam em ``app/api/admin_catalogo_conferencia_*``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.models import (
    CatalogCharacter,
    CatalogConferencia,
    CatalogConferenciaPersonagem,
    CatalogItem,
    CatalogItemImage,
    FigurinoSheet,
    User,
)
from app.utils import audit, strip_accents_lower

logger = logging.getLogger(__name__)

TIPOS = ("tema", "dupla", "avulso", "generico")
TIPOS_COM_ELENCO = ("tema", "dupla")
TIPO_COM_FICHA_PROPRIA = "avulso"
DECISAO_CRIAR = "criar"
DECISOES = (DECISAO_CRIAR, "nao_criar")
ORIGEM_LEITURA = "leitura"
ORIGEM_MANUAL = "manual"
SITUACAO_A_CONFERIR = "a_conferir"
SITUACAO_CONFERIDO = "conferido"
SITUACAO_SEM_LEITURA = "sem_leitura"
SITUACOES = (SITUACAO_A_CONFERIR, SITUACAO_CONFERIDO, SITUACAO_SEM_LEITURA)
NOME_MAX = 200
OBSERVACAO_MAX = 1000
GRUPO_MAX = 120
LEITURA_PATH = Path(__file__).resolve().parent / "dados" / "leitura_personagens.json"
# Chave do `pg_advisory_xact_lock` da carga: dois cliques em "Carregar leitura" entram em fila.
TRAVA_DA_CARGA = 360

CODIGO_CONFERIDO = "conferido"
CODIGO_NAO_CONFERIDO = "nao_conferido"
CODIGO_DA_LEITURA = "da_leitura"

MSG_ITEM_NAO_ENCONTRADO = "Item não encontrado."
MSG_SEM_LEITURA = "Este item ainda não tem leitura."
MSG_PERSONAGEM_NAO_ENCONTRADO = "Personagem não encontrado."
MSG_CONFERIDO = "Este item já foi conferido. Reabra o item para alterar."
MSG_NAO_CONFERIDO = "Este item não está conferido."
MSG_DA_LEITURA = 'Personagem da leitura não pode ser excluído. Marque como "Não criar".'
MSG_TEMA_SEM_PERSONAGEM = (
    "Um tema precisa de pelo menos um personagem. Mantenha um personagem ou altere o tipo do item."
)
MSG_FICHA_SO_EM_AVULSO = "Só item avulso tem ficha própria. Num tema, a ficha é de cada personagem."
AVISO_FOTO_SUMIU = "A foto escolhida pela leitura não está mais na galeria do item."
AVISO_FICHA_SUMIU = "A ficha sugerida ({ficha}) não existe mais."
MOTIVO_ITEM_INEXISTENTE = "O item não existe mais no catálogo."
MOTIVO_TIPO_DESCONHECIDO = "A leitura traz um tipo desconhecido."


class ConferenciaValidationError(Exception):
    """Dado recusado: a mensagem vai para o campo ``field`` da tela (400)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class ConferenciaConflito(Exception):
    """O estado não permite a ação (409); ``codigo`` diz à tela o que fazer."""

    def __init__(self, codigo: str, message: str) -> None:
        super().__init__(message)
        self.codigo = codigo
        self.message = message


class ConferenciaNaoEncontrada(Exception):
    """Item, leitura ou personagem inexistente (404)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ── a fila ──────────────────────────────────────────────────────────────────────────────────────


def filtro_da_fila() -> tuple:
    """As condições que fazem um item estar pendente — a única definição da fila.

    Ativo, sem ficha própria, sem elenco e que não é a página própria de um personagem de outro
    tema (nesse caso o item já está organizado: a ficha é do personagem).
    """
    tem_elenco = (
        select(CatalogCharacter.id)
        .where(CatalogCharacter.catalog_item_id == CatalogItem.id)
        .exists()
    )
    e_pagina_propria = (
        select(CatalogCharacter.id).where(CatalogCharacter.own_item_id == CatalogItem.id).exists()
    )
    return (
        CatalogItem.is_active.is_(True),
        CatalogItem.figurino_sheet_id.is_(None),
        ~tem_elenco,
        ~e_pagina_propria,
    )


def _situacao(tem_leitura: bool, conferido_em: datetime | None) -> str:
    if not tem_leitura:
        return SITUACAO_SEM_LEITURA
    return SITUACAO_CONFERIDO if conferido_em else SITUACAO_A_CONFERIR


def situacao_de(conferencia: CatalogConferencia | None) -> str:
    """Situação de um item a partir da conferência dele (``None`` = sem leitura)."""
    return _situacao(conferencia is not None, conferencia.conferido_em if conferencia else None)


def _iso_sp(carimbo: datetime | None) -> str | None:
    # Import tardio: `comando_ops` puxa meio marketing; o helper é o mesmo da 345 (UTC → São Paulo).
    from app.marketing.comando_ops import iso_sp

    return iso_sp(carimbo)


def _linhas_da_fila() -> list[dict]:
    """A fila inteira numa consulta só, em ordem alfabética sem acento (e ``id`` no empate)."""
    conf, pers, img = CatalogConferencia, CatalogConferenciaPersonagem, CatalogItemImage
    total_personagens = (
        select(func.count(pers.id))
        .where(pers.conferencia_id == conf.id)
        .correlate(conf)
        .scalar_subquery()
    )
    capa = (
        select(img.url)
        .where(img.item_id == CatalogItem.id)
        .order_by(img.position, img.id)
        .limit(1)
        .correlate(CatalogItem)
        .scalar_subquery()
    )
    linhas = (
        db.session.query(
            CatalogItem.id,
            CatalogItem.name,
            capa,
            conf.id,
            conf.tipo,
            conf.tipo_lido,
            conf.conferido_em,
            User.name,
            total_personagens,
        )
        .outerjoin(conf, conf.catalog_item_id == CatalogItem.id)
        .outerjoin(User, User.id == conf.conferido_por_id)
        .filter(*filtro_da_fila())
        .all()
    )
    itens = [_linha_da_fila(*linha) for linha in linhas]
    # Ordena em Python: a ordem do Postgres depende do collation e não bate com a busca sem acento.
    return sorted(itens, key=lambda i: (strip_accents_lower(i["nome"]), i["id"]))


def _linha_da_fila(
    item_id: int,
    nome: str,
    capa: str | None,
    conferencia_id: int | None,
    tipo: str | None,
    tipo_lido: str | None,
    conferido_em: datetime | None,
    conferido_por: str | None,
    personagens: int | None,
) -> dict:
    tem_leitura = conferencia_id is not None
    return {
        "id": item_id,
        "nome": nome,
        "capa_url": capa,
        "situacao": _situacao(tem_leitura, conferido_em),
        "tipo": tipo,
        "tipo_lido": tipo_lido,
        "personagens": (personagens or 0) if tipo in TIPOS_COM_ELENCO else 0,
        "conferido_em": _iso_sp(conferido_em),
        "conferido_por": conferido_por,
    }


def _contadores(itens: list[dict]) -> dict:
    por_tipo = {tipo: {"total": 0, "conferidos": 0} for tipo in TIPOS}
    totais = {situacao: 0 for situacao in SITUACOES}
    for item in itens:
        totais[item["situacao"]] += 1
        if item["tipo"] in por_tipo:
            por_tipo[item["tipo"]]["total"] += 1
            por_tipo[item["tipo"]]["conferidos"] += item["situacao"] == SITUACAO_CONFERIDO
    return {
        "fila": len(itens),
        "a_conferir": totais[SITUACAO_A_CONFERIR],
        "conferidos": totais[SITUACAO_CONFERIDO],
        "sem_leitura": totais[SITUACAO_SEM_LEITURA],
        "por_tipo": por_tipo,
    }


def _filtrar(
    itens: list[dict], tipo: str | None, situacao: str | None, busca: str | None
) -> list[dict]:
    """Aplica os filtros da tela. Valor desconhecido é ignorado (filtro vazio), nunca erro."""
    termo = strip_accents_lower(busca or "").strip()
    if tipo in TIPOS:
        itens = [i for i in itens if i["tipo"] == tipo]
    if situacao in SITUACOES:
        itens = [i for i in itens if i["situacao"] == situacao]
    if termo:
        itens = [i for i in itens if termo in strip_accents_lower(i["nome"])]
    return itens


def listar_fila(
    tipo: str | None = None, situacao: str | None = None, busca: str | None = None
) -> dict:
    """Fila da conferência com contadores (sempre da fila inteira) e o estado da leitura."""
    itens = _linhas_da_fila()
    return {
        "contadores": _contadores(itens),
        "leitura": _estado_da_leitura(),
        "itens": _filtrar(itens, tipo, situacao, busca),
    }


@lru_cache(maxsize=2)
def _ids_do_arquivo(mtime: float) -> tuple[int, ...]:
    """Ids dos itens do arquivo da leitura; a chave ``mtime`` invalida o cache quando ele muda."""
    return tuple(item["id"] for item in ler_arquivo_da_leitura() if isinstance(item.get("id"), int))


def _estado_da_leitura() -> dict:
    """Quantos itens o arquivo tem e quantos ainda faltam carregar (mostra "Carregar leitura")."""
    try:
        ids = _ids_do_arquivo(LEITURA_PATH.stat().st_mtime)
    except (OSError, ValueError) as exc:
        logger.warning("Arquivo da leitura de personagens ilegível: %s", exc)
        return {"itens_no_arquivo": 0, "a_carregar": 0}
    existentes = {i for (i,) in db.session.query(CatalogItem.id).filter(CatalogItem.id.in_(ids))}
    carregados = {
        i
        for (i,) in db.session.query(CatalogConferencia.catalog_item_id).filter(
            CatalogConferencia.catalog_item_id.in_(ids)
        )
    }
    return {"itens_no_arquivo": len(ids), "a_carregar": len(existentes - carregados)}


# ── o item ──────────────────────────────────────────────────────────────────────────────────────


def _ficha_dict(ficha: FigurinoSheet | None) -> dict | None:
    if ficha is None:
        return None
    return {"id": ficha.id, "nome": ficha.character_name, "foto_url": ficha.photo_url}


def _foto_dict(personagem: CatalogConferenciaPersonagem) -> dict | None:
    """A foto e o recorte, ou ``None`` se a imagem saiu da galeria ou o recorte não é válido."""
    if not personagem.tem_foto or personagem.imagem is None:
        return None
    return {
        "url": personagem.imagem.url,
        "largura": personagem.foto_largura,
        "altura": personagem.foto_altura,
        "recorte": personagem.recorte_list,
    }


def serializar_personagem(personagem: CatalogConferenciaPersonagem) -> dict:
    """Um personagem proposto, com o proposto pela leitura ao lado do decidido."""
    foto = _foto_dict(personagem)
    return {
        "id": personagem.id,
        "origem": personagem.origem,
        "nome": personagem.nome,
        "nome_lido": personagem.nome_lido,
        "foto": foto,
        "ficha": _ficha_dict(personagem.ficha),
        "ficha_sugerida": _ficha_dict(personagem.ficha_sugerida),
        "aviso": personagem.aviso,
        "sem_foto_lido": personagem.sem_foto_lido,
        # Sem foto utilizável, só resta criar sem foto — mesmo que a marca gravada diga outra coisa
        # (a imagem pode ter saído da galeria depois da carga).
        "sem_foto": personagem.sem_foto or foto is None,
        "decisao": personagem.decisao,
        "observacao": personagem.observacao,
    }


def serializar_conferencia(conferencia: CatalogConferencia | None) -> dict | None:
    """O bloco ``conferencia`` do contrato (``None`` = item sem leitura)."""
    if conferencia is None:
        return None
    return {
        "tipo": conferencia.tipo,
        "tipo_lido": conferencia.tipo_lido,
        "nota": conferencia.nota,
        "acao": conferencia.acao,
        "grupo": conferencia.grupo,
        "lote": conferencia.lote,
        "ficha": _ficha_dict(conferencia.ficha),
        "ficha_sugerida": _ficha_dict(conferencia.ficha_sugerida),
        "observacao": conferencia.observacao,
        "conferido_em": _iso_sp(conferencia.conferido_em),
        "conferido_por": conferencia.conferido_por.name if conferencia.conferido_por else None,
        "personagens": [serializar_personagem(p) for p in conferencia.personagens],
    }


def resposta_da_conferencia(conferencia: CatalogConferencia) -> dict:
    """O que toda rota de decisão devolve: a conferência como ficou e a situação do item."""
    return {
        "conferencia": serializar_conferencia(conferencia),
        "situacao": situacao_de(conferencia),
    }


def _carregar_conferencia(item_id: int) -> CatalogConferencia | None:
    pers = CatalogConferenciaPersonagem
    return (
        CatalogConferencia.query.filter_by(catalog_item_id=item_id)
        .options(
            selectinload(CatalogConferencia.personagens).options(
                joinedload(pers.imagem), joinedload(pers.ficha), joinedload(pers.ficha_sugerida)
            ),
            joinedload(CatalogConferencia.ficha),
            joinedload(CatalogConferencia.ficha_sugerida),
            joinedload(CatalogConferencia.conferido_por),
        )
        .first()
    )


def _vizinhos(
    item: CatalogItem, tipo: str | None, busca: str | None
) -> tuple[int | None, int | None]:
    """O item a conferir anterior e o próximo na ordem da fila, respeitando ``tipo`` e ``busca``."""
    candidatos = _filtrar(_linhas_da_fila(), tipo, SITUACAO_A_CONFERIR, busca)
    chave = (strip_accents_lower(item.name), item.id)
    antes = [c["id"] for c in candidatos if (strip_accents_lower(c["nome"]), c["id"]) < chave]
    depois = [c["id"] for c in candidatos if (strip_accents_lower(c["nome"]), c["id"]) > chave]
    return (antes[-1] if antes else None, depois[0] if depois else None)


def detalhe_do_item(item_id: int, tipo: str | None = None, busca: str | None = None) -> dict:
    """Tudo o que a tela de um item precisa numa ida ao servidor.

    Raises:
        ConferenciaNaoEncontrada: o item não existe no catálogo.
    """
    item = db.session.get(CatalogItem, item_id)
    if item is None:
        raise ConferenciaNaoEncontrada(MSG_ITEM_NAO_ENCONTRADO)
    conferencia = _carregar_conferencia(item_id)
    na_fila = db.session.query(
        select(CatalogItem.id).where(CatalogItem.id == item_id, *filtro_da_fila()).exists()
    ).scalar()
    anterior_id, proximo_id = _vizinhos(item, tipo, busca)
    return {
        "item": {
            "id": item.id,
            "nome": item.name,
            "categorias": [c.name for c in item.categories],
            "fotos": [{"id": imagem.id, "url": imagem.url} for imagem in item.images],
        },
        "na_fila": bool(na_fila),
        "situacao": situacao_de(conferencia),
        "conferencia": serializar_conferencia(conferencia),
        "anterior_id": anterior_id,
        "proximo_id": proximo_id,
    }


# ── decisões ────────────────────────────────────────────────────────────────────────────────────


def _travar_por_item(item_id: int) -> CatalogConferencia:
    """Trava e relê a conferência do item. Decidir só depois daqui (``docs/00`` §6, item 26)."""
    if db.session.get(CatalogItem, item_id) is None:
        raise ConferenciaNaoEncontrada(MSG_ITEM_NAO_ENCONTRADO)
    db.session.flush()
    conferencia = (
        CatalogConferencia.query.filter_by(catalog_item_id=item_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if conferencia is None:
        raise ConferenciaNaoEncontrada(MSG_SEM_LEITURA)
    return conferencia


def _travar_por_personagem(
    personagem_id: int,
) -> tuple[CatalogConferencia, CatalogConferenciaPersonagem]:
    personagem = db.session.get(CatalogConferenciaPersonagem, personagem_id)
    if personagem is None:
        raise ConferenciaNaoEncontrada(MSG_PERSONAGEM_NAO_ENCONTRADO)
    db.session.flush()
    conferencia = (
        CatalogConferencia.query.filter_by(id=personagem.conferencia_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    return conferencia, personagem


def _exigir_aberta(conferencia: CatalogConferencia) -> None:
    if conferencia.conferido_em is not None:
        raise ConferenciaConflito(CODIGO_CONFERIDO, MSG_CONFERIDO)


def _nome_valido(valor: Any) -> str:
    nome = valor.strip() if isinstance(valor, str) else ""
    if not nome:
        raise ConferenciaValidationError("nome", "Informe o nome do personagem.")
    if len(nome) > NOME_MAX:
        raise ConferenciaValidationError("nome", f"O nome pode ter até {NOME_MAX} caracteres.")
    return nome


def _observacao_valida(valor: Any) -> str | None:
    texto = valor.strip() if isinstance(valor, str) else ""
    if len(texto) > OBSERVACAO_MAX:
        raise ConferenciaValidationError(
            "observacao", f"A observação pode ter até {OBSERVACAO_MAX} caracteres."
        )
    return texto or None


def _ficha_valida(valor: Any) -> int | None:
    """``None`` tira a ficha; um id precisa existir. ``True``/texto não são id."""
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ConferenciaValidationError("ficha_id", "Ficha de figurino não encontrada.")
    if db.session.get(FigurinoSheet, valor) is None:
        raise ConferenciaValidationError("ficha_id", "Ficha de figurino não encontrada.")
    return valor


def _tipo_valido(valor: Any) -> str:
    if valor not in TIPOS:
        raise ConferenciaValidationError("tipo", "Selecione um tipo válido.")
    return valor


def _mudancas_do_item(conferencia: CatalogConferencia, campos: dict) -> dict:
    """Valida tudo antes de gravar qualquer coisa; devolve só o que muda."""
    mudancas: dict[str, Any] = {}
    if "tipo" in campos:
        mudancas["tipo"] = _tipo_valido(campos["tipo"])
    if "observacao" in campos:
        mudancas["observacao"] = _observacao_valida(campos["observacao"])
    if "ficha_id" in campos:
        ficha_id = _ficha_valida(campos["ficha_id"])
        tipo_final = mudancas.get("tipo", conferencia.tipo)
        if ficha_id is not None and tipo_final != TIPO_COM_FICHA_PROPRIA:
            raise ConferenciaValidationError("ficha_id", MSG_FICHA_SO_EM_AVULSO)
        mudancas["ficha_id"] = ficha_id
    return mudancas


def alterar_item(item_id: int, campos: dict) -> CatalogConferencia:
    """Corrige o tipo, a ficha (só em avulso) e a observação do item. Campo ausente não muda.

    Raises:
        ConferenciaNaoEncontrada: item inexistente ou sem leitura.
        ConferenciaConflito: item já conferido.
        ConferenciaValidationError: tipo, ficha ou observação inválidos.
    """
    conferencia = _travar_por_item(item_id)
    _exigir_aberta(conferencia)
    for campo, valor in _mudancas_do_item(conferencia, campos).items():
        setattr(conferencia, campo, valor)
    db.session.commit()
    return _carregar_conferencia(item_id)


def conferir(item_id: int, usuario_id: int) -> CatalogConferencia:
    """Marca o item como conferido, com quem e quando.

    Tema e dupla precisam de ao menos um personagem com a decisão "criar": sem nenhum, o tipo está
    errado e é isso que a pessoa precisa corrigir.

    Raises:
        ConferenciaNaoEncontrada: item inexistente ou sem leitura.
        ConferenciaConflito: item já conferido.
        ConferenciaValidationError: tema ou dupla sem personagem a criar (campo ``tipo``).
    """
    conferencia = _travar_por_item(item_id)
    _exigir_aberta(conferencia)
    if conferencia.tipo in TIPOS_COM_ELENCO and not any(
        p.decisao == DECISAO_CRIAR for p in conferencia.personagens
    ):
        raise ConferenciaValidationError("tipo", MSG_TEMA_SEM_PERSONAGEM)
    conferencia.conferido_em = datetime.utcnow()
    conferencia.conferido_por_id = usuario_id
    audit("edit", "CatalogConferencia", conferencia.id, conferencia.item.name, "Item conferido")
    db.session.commit()
    return _carregar_conferencia(item_id)


def reabrir(item_id: int) -> CatalogConferencia:
    """Devolve o item para "a conferir", preservando todas as decisões.

    Raises:
        ConferenciaNaoEncontrada: item inexistente ou sem leitura.
        ConferenciaConflito: o item não está conferido.
    """
    conferencia = _travar_por_item(item_id)
    if conferencia.conferido_em is None:
        raise ConferenciaConflito(CODIGO_NAO_CONFERIDO, MSG_NAO_CONFERIDO)
    conferencia.conferido_em = None
    conferencia.conferido_por_id = None
    audit(
        "edit", "CatalogConferencia", conferencia.id, conferencia.item.name, "Conferência reaberta"
    )
    db.session.commit()
    return _carregar_conferencia(item_id)


def acrescentar_personagem(item_id: int, nome: Any, ficha_id: Any = None) -> CatalogConferencia:
    """Acrescenta ao elenco proposto um personagem que a leitura não viu. Entra sem foto, no fim.

    Raises:
        ConferenciaNaoEncontrada: item inexistente ou sem leitura.
        ConferenciaConflito: item já conferido.
        ConferenciaValidationError: nome vazio ou longo; ficha inexistente.
    """
    conferencia = _travar_por_item(item_id)
    _exigir_aberta(conferencia)
    nome_ok, ficha_ok = _nome_valido(nome), _ficha_valida(ficha_id)
    ultima = max((p.position for p in conferencia.personagens), default=-1)
    db.session.add(
        CatalogConferenciaPersonagem(
            conferencia_id=conferencia.id,
            position=ultima + 1,
            origem=ORIGEM_MANUAL,
            nome=nome_ok,
            ficha_id=ficha_ok,
            sem_foto_lido=True,
            sem_foto=True,
            decisao=DECISAO_CRIAR,
        )
    )
    db.session.commit()
    return _carregar_conferencia(item_id)


def _sem_foto_valido(personagem: CatalogConferenciaPersonagem, valor: Any) -> bool:
    if not isinstance(valor, bool):
        raise ConferenciaValidationError(
            "sem_foto", "Informe se o personagem será criado sem foto."
        )
    if valor is False and not personagem.tem_foto:
        raise ConferenciaValidationError("sem_foto", "Este personagem não tem foto na leitura.")
    return valor


def _mudancas_do_personagem(personagem: CatalogConferenciaPersonagem, campos: dict) -> dict:
    """Valida tudo antes de gravar qualquer coisa; devolve só o que muda."""
    mudancas: dict[str, Any] = {}
    if "nome" in campos:
        mudancas["nome"] = _nome_valido(campos["nome"])
    if "ficha_id" in campos:
        mudancas["ficha_id"] = _ficha_valida(campos["ficha_id"])
    if "decisao" in campos:
        if campos["decisao"] not in DECISOES:
            raise ConferenciaValidationError("decisao", "Selecione criar ou não criar.")
        mudancas["decisao"] = campos["decisao"]
    if "sem_foto" in campos:
        mudancas["sem_foto"] = _sem_foto_valido(personagem, campos["sem_foto"])
    if "observacao" in campos:
        mudancas["observacao"] = _observacao_valida(campos["observacao"])
    return mudancas


def alterar_personagem(personagem_id: int, campos: dict) -> CatalogConferencia:
    """Corrige nome, ficha, decisão, "criar sem foto" e observação. Campo ausente não muda.

    O nome e a ficha propostos pela leitura (``nome_lido``, ``ficha_sugerida_id``) nunca mudam.

    Raises:
        ConferenciaNaoEncontrada: personagem inexistente.
        ConferenciaConflito: item já conferido.
        ConferenciaValidationError: qualquer campo inválido.
    """
    conferencia, personagem = _travar_por_personagem(personagem_id)
    _exigir_aberta(conferencia)
    for campo, valor in _mudancas_do_personagem(personagem, campos).items():
        setattr(personagem, campo, valor)
    db.session.commit()
    return _carregar_conferencia(conferencia.catalog_item_id)


def excluir_personagem(personagem_id: int) -> CatalogConferencia:
    """Exclui um personagem acrescentado à mão. O da leitura não se exclui: marca-se "não criar".

    Raises:
        ConferenciaNaoEncontrada: personagem inexistente.
        ConferenciaConflito: item já conferido, ou personagem que veio da leitura.
    """
    conferencia, personagem = _travar_por_personagem(personagem_id)
    _exigir_aberta(conferencia)
    if personagem.origem != ORIGEM_MANUAL:
        raise ConferenciaConflito(CODIGO_DA_LEITURA, MSG_DA_LEITURA)
    db.session.delete(personagem)
    db.session.commit()
    return _carregar_conferencia(conferencia.catalog_item_id)


# ── a carga da leitura ──────────────────────────────────────────────────────────────────────────


def ler_arquivo_da_leitura() -> list[dict]:
    """Os itens do arquivo versionado da leitura (``app/admin/dados/leitura_personagens.json``)."""
    conteudo = json.loads(LEITURA_PATH.read_text(encoding="utf-8"))
    return list(conteudo.get("itens") or [])


def _juntar_aviso(aviso: str | None, extra: str) -> str:
    return f"{aviso.rstrip('.')}. {extra}" if aviso else extra


def _indice_de_fotos(item_ids: list[int]) -> dict[tuple[int, str], int]:
    """``(item, nome do arquivo) → id da imagem``: a leitura conhece a foto pelo nome do arquivo."""
    linhas = db.session.query(
        CatalogItemImage.id, CatalogItemImage.item_id, CatalogItemImage.url
    ).filter(CatalogItemImage.item_id.in_(item_ids))
    return {(item_id, url.rsplit("/", 1)[-1]): imagem_id for imagem_id, item_id, url in linhas}


def _fichas_existentes(dados: list[dict]) -> set[int]:
    citadas = {d.get("ficha_id") for d in dados}
    citadas |= {p.get("ficha_id") for d in dados for p in d.get("personagens") or []}
    ids = [f for f in citadas if isinstance(f, int)]
    return {i for (i,) in db.session.query(FigurinoSheet.id).filter(FigurinoSheet.id.in_(ids))}


def _ficha_da_leitura(bruto: dict, fichas: set[int]) -> tuple[int | None, str | None]:
    """A ficha sugerida, se ainda existe; senão ``None`` e o aviso de que ela sumiu."""
    ficha_id = bruto.get("ficha_id")
    if not isinstance(ficha_id, int):
        return None, None
    if ficha_id in fichas:
        return ficha_id, None
    rotulo = f"{ficha_id} {bruto.get('ficha_nome') or ''}".strip()
    return None, AVISO_FICHA_SUMIU.format(ficha=rotulo)


def _novo_personagem(
    bruto: dict, posicao: int, item_id: int, fotos: dict[tuple[int, str], int], fichas: set[int]
) -> CatalogConferenciaPersonagem:
    ficha_id, aviso_ficha = _ficha_da_leitura(bruto, fichas)
    aviso = bruto.get("aviso") or None
    imagem_id, recorte, dims = None, bruto.get("recorte"), bruto.get("dims") or [None, None]
    sem_foto = bool(bruto.get("sem_foto")) or not bruto.get("foto") or not recorte
    if not sem_foto:
        imagem_id = fotos.get((item_id, bruto["foto"]))
        if imagem_id is None:
            sem_foto, aviso = True, _juntar_aviso(aviso, AVISO_FOTO_SUMIU)
    if aviso_ficha:
        aviso = _juntar_aviso(aviso, aviso_ficha)
    nome = str(bruto.get("nome") or "").strip()[:NOME_MAX] or "Sem nome"
    return CatalogConferenciaPersonagem(
        position=posicao,
        origem=ORIGEM_LEITURA,
        nome_lido=nome,
        nome=nome,
        imagem_id=imagem_id,
        recorte=json.dumps(recorte) if imagem_id else None,
        foto_largura=dims[0] if imagem_id else None,
        foto_altura=dims[1] if imagem_id else None,
        ficha_sugerida_id=ficha_id,
        ficha_id=ficha_id,
        aviso=aviso,
        sem_foto_lido=sem_foto,
        sem_foto=sem_foto,
        decisao=DECISAO_CRIAR,
    )


def _nova_conferencia(
    bruto: dict, fotos: dict[tuple[int, str], int], fichas: set[int]
) -> CatalogConferencia:
    ficha_id, aviso_ficha = _ficha_da_leitura(bruto, fichas)
    acao = bruto.get("acao") or None
    if aviso_ficha:
        acao = _juntar_aviso(acao, aviso_ficha)
    conferencia = CatalogConferencia(
        catalog_item_id=bruto["id"],
        tipo_lido=bruto["tipo"],
        tipo=bruto["tipo"],
        nota=bruto.get("nota") or None,
        acao=acao,
        grupo=(bruto.get("grupo") or None),
        ficha_sugerida_id=ficha_id,
        ficha_id=ficha_id,
        lote=str(bruto.get("lote") or "")[:10] or None,
    )
    if conferencia.grupo:
        conferencia.grupo = conferencia.grupo[:GRUPO_MAX]
    for posicao, personagem in enumerate(bruto.get("personagens") or []):
        conferencia.personagens.append(
            _novo_personagem(personagem, posicao, bruto["id"], fotos, fichas)
        )
    return conferencia


def _motivo_para_ignorar(bruto: dict, existentes: set[int]) -> str | None:
    if bruto.get("id") not in existentes:
        return MOTIVO_ITEM_INEXISTENTE
    if bruto.get("tipo") not in TIPOS:
        return MOTIVO_TIPO_DESCONHECIDO
    return None


def carregar_leitura(dados: list[dict]) -> dict:
    """Carrega a leitura, acrescentando só os itens que ainda não têm conferência.

    Idempotente: item que já tem conferência é pulado sempre, tenha decisão humana ou não. A trava
    consultiva enfileira dois cliques simultâneos e o ``UNIQUE(catalog_item_id)`` é a segunda
    barreira. Tolera o que sumiu desde a leitura: item inexistente é ignorado (e listado), foto que
    saiu da galeria vira "sem foto" e ficha excluída vira "sem ficha", os dois com aviso.

    Returns:
        ``{"itens_novos", "personagens_novos", "ja_existiam", "ignorados": [{id, nome, motivo}]}``.
    """
    db.session.execute(db.text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": TRAVA_DA_CARGA})
    ids = [d["id"] for d in dados if isinstance(d.get("id"), int)]
    existentes = {i for (i,) in db.session.query(CatalogItem.id).filter(CatalogItem.id.in_(ids))}
    ja_carregados = {
        i
        for (i,) in db.session.query(CatalogConferencia.catalog_item_id).filter(
            CatalogConferencia.catalog_item_id.in_(ids)
        )
    }
    fotos, fichas = _indice_de_fotos(ids), _fichas_existentes(dados)
    resumo: dict[str, Any] = {
        "itens_novos": 0,
        "personagens_novos": 0,
        "ja_existiam": 0,
        "ignorados": [],
    }
    for bruto in dados:
        motivo = _motivo_para_ignorar(bruto, existentes)
        if motivo:
            resumo["ignorados"].append(
                {"id": bruto.get("id"), "nome": bruto.get("nome"), "motivo": motivo}
            )
        elif bruto["id"] in ja_carregados:
            resumo["ja_existiam"] += 1
        else:
            conferencia = _nova_conferencia(bruto, fotos, fichas)
            db.session.add(conferencia)
            ja_carregados.add(bruto["id"])
            resumo["itens_novos"] += 1
            resumo["personagens_novos"] += len(conferencia.personagens)
    if resumo["itens_novos"]:
        audit(
            "create",
            "CatalogConferencia",
            None,
            "Leitura de personagens",
            f"Carga da leitura: {resumo['itens_novos']} itens, {resumo['personagens_novos']} personagens",
        )
    db.session.commit()
    return resumo
