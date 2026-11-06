"""A linha do tempo da ficha (feature 335): os marcos da cliente, do mais novo para o mais antigo.

Só os marcos, cada um com a data e o link para o lugar de origem (decisão do dono): a conversa continua na tela de
Conversas. Tudo derivado do que existe (research R5):

- entrada na base (o Kommo ou a criação);
- o primeiro contato de cada conversa da ficha (a regra do funil, ``funil_ops``) e os contatos por anúncio;
- os orçamentos enviados (um por orçamento, no primeiro envio), os formulários, os eventos vivos e, deles (e do
  principal do grupo), os pagamentos registrados e as avaliações.

O evento cancelado fica de fora, com o pagamento e a avaliação dele, como nas listas (feature 312). As fontes gravam
em UTC ou no horário de São Paulo; a saída é ISO com o fuso, e a tela formata em São Paulo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func

from app import db
from app.constants import TZ_SP
from app.conversas import constantes as K
from app.models import (
    AnuncioMeta,
    CalendarEvent,
    Client,
    ClientFeedback,
    Conversa,
    ConversaAnuncio,
    ConversaMensagem,
    EventClient,
    EventPayment,
    FormResponse,
    OrcamentoEnvio,
    OrcamentoHistory,
    PixRecebido,
)
from app.money import format_brl

# Ordem dos marcos no mesmo instante (o anúncio chega junto da primeira mensagem).
_ORDEM = (
    "avaliacao",
    "pagamento",
    "evento",
    "formulario",
    "orcamento",
    "contato",
    "anuncio",
    "entrada",
)


def _utc(momento: datetime) -> datetime:
    return momento.replace(tzinfo=UTC)


def _sp(momento: datetime) -> datetime:
    return momento.replace(tzinfo=TZ_SP)


def _dia(valor: Any) -> str | None:
    """``dd/mm/aaaa`` de uma data, de um datetime ou de uma data ISO em texto."""
    if not valor:
        return None
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor[:10])
        except ValueError:
            return None
    return valor.strftime("%d/%m/%Y")


def _juntar(*partes: str | None) -> str | None:
    return " · ".join(p for p in partes if p) or None


def _marco(
    tipo: str,
    quando: datetime,
    titulo: str,
    detalhe: str | None = None,
    link: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"tipo": tipo, "quando": quando, "titulo": titulo, "detalhe": detalhe, "link": link}


def _entrada(ficha: Client) -> dict[str, Any]:
    quando = _sp(ficha.kommo_created_at) if ficha.kommo_created_at else _utc(ficha.created_at)
    origem = K.ORIGEM_DA_FICHA_LEGIVEL.get(ficha.source or "")
    return _marco(
        "entrada", quando, K.TITULO_DO_MARCO["entrada"], _juntar(origem, ficha.lead_origin)
    )


def _conversas(ficha: Client, com_conversas: bool) -> list[dict[str, Any]]:
    conversas = Conversa.query.filter_by(client_id=ficha.id).all()
    if not conversas:
        return []
    ids = [c.id for c in conversas]
    # O primeiro contato é a regra do funil: a primeira mensagem dela ou o primeiro contato pelo anúncio.
    recebidas = dict(
        db.session.query(ConversaMensagem.conversa_id, func.min(ConversaMensagem.momento))
        .filter(ConversaMensagem.conversa_id.in_(ids), ConversaMensagem.direcao == K.RECEBIDA)
        .group_by(ConversaMensagem.conversa_id)
        .all()
    )
    contatos = (
        db.session.query(ConversaAnuncio, AnuncioMeta.campanha_nome)
        .outerjoin(AnuncioMeta, AnuncioMeta.anuncio_id == ConversaAnuncio.anuncio_id)
        .filter(ConversaAnuncio.conversa_id.in_(ids))
        .all()
    )
    marcos = []
    primeiro_anuncio: dict[int, datetime] = {}
    for contato, campanha in contatos:
        anterior = primeiro_anuncio.get(contato.conversa_id)
        primeiro_anuncio[contato.conversa_id] = (
            min(anterior, contato.momento) if anterior else contato.momento
        )
        if contato.tipo not in (K.CONTATO_ANUNCIO, K.CONTATO_PUBLICACAO):
            continue
        anuncio = contato.tipo == K.CONTATO_ANUNCIO
        titulo = f"“{contato.titulo}”" if contato.titulo else None
        marcos.append(
            _marco(
                "anuncio",
                _utc(contato.momento),
                K.TITULO_DO_MARCO["anuncio" if anuncio else "publicacao"],
                _juntar(titulo, campanha if anuncio else None),
            )
        )
    for conversa in conversas:
        candidatos = [
            m for m in (recebidas.get(conversa.id), primeiro_anuncio.get(conversa.id)) if m
        ]
        if not candidatos:
            continue  # só mensagens da Manto: a cliente ainda não falou
        canal = K.ROTULO_DO_CANAL.get(conversa.canal, conversa.canal)
        link = {"tipo": "conversa", "id": conversa.id} if com_conversas else None
        marcos.append(
            _marco(
                "contato",
                _utc(min(candidatos)),
                K.TITULO_DO_MARCO["contato"].format(canal=canal),
                link=link,
            )
        )
    return marcos


def _orcamentos(ficha: Client, com_orcamentos: bool) -> list[dict[str, Any]]:
    """Um marco por orçamento, no primeiro envio (pela conversa da ficha ou ligado a ela)."""
    pelas_conversas = {
        oid
        for (oid,) in db.session.query(OrcamentoEnvio.orcamento_id)
        .join(Conversa, Conversa.id == OrcamentoEnvio.conversa_id)
        .filter(Conversa.client_id == ficha.id)
        .all()
    }
    ligados = {
        oid for (oid,) in db.session.query(OrcamentoHistory.id).filter_by(client_id=ficha.id).all()
    }
    ids = pelas_conversas | ligados
    if not ids:
        return []
    primeiros = dict(
        db.session.query(OrcamentoEnvio.orcamento_id, func.min(OrcamentoEnvio.created_at))
        .filter(OrcamentoEnvio.orcamento_id.in_(ids))
        .group_by(OrcamentoEnvio.orcamento_id)
        .all()
    )
    marcos = []
    for orcamento in OrcamentoHistory.query.filter(OrcamentoHistory.id.in_(ids)).all():
        quando = primeiros.get(orcamento.id) or orcamento.created_at
        link = {"tipo": "orcamento", "id": orcamento.id} if com_orcamentos else None
        detalhe = _juntar(orcamento.event_location, _dia(orcamento.event_date))
        marcos.append(
            _marco("orcamento", _utc(quando), K.TITULO_DO_MARCO["orcamento"], detalhe, link)
        )
    return marcos


def _formularios(ficha: Client) -> list[dict[str, Any]]:
    marcos = []
    for resposta in FormResponse.query.filter_by(client_id=ficha.id).all():
        festa = _dia(resposta.event_date)
        detalhe = _juntar(resposta.form_type_label, f"festa em {festa}" if festa else None)
        marcos.append(
            _marco(
                "formulario", _utc(resposta.created_at), K.TITULO_DO_MARCO["formulario"], detalhe
            )
        )
    return marcos


def _eventos(ficha: Client) -> tuple[list[dict[str, Any]], list[int]]:
    """Os eventos vivos da ficha e os ids (com o principal do grupo) para os pagamentos e as avaliações."""
    linhas = (
        db.session.query(CalendarEvent, EventClient.relationship_type)
        .join(EventClient, EventClient.event_id == CalendarEvent.id)
        .filter(EventClient.client_id == ficha.id, CalendarEvent.cancelled_at.is_(None))
        .all()
    )
    marcos, ids, vistos = [], set(), set()
    for evento, relacao in linhas:
        if evento.id in vistos:
            continue
        vistos.add(evento.id)
        ids.update(e for e in (evento.id, evento.group_leader_id) if e)
        papel = relacao if relacao and relacao != "Contratante" else None
        detalhe = _juntar(evento.title, _dia(evento.start_at), papel)
        marcos.append(
            _marco(
                "evento",
                _utc(evento.created_at),
                K.TITULO_DO_MARCO["evento"],
                detalhe,
                {"tipo": "evento", "id": evento.id},
            )
        )
    vivos = {
        eid for (eid,) in db.session.query(CalendarEvent.id).filter(
            CalendarEvent.id.in_(ids), CalendarEvent.cancelled_at.is_(None)
        ).all()
    } if ids else set()  # fmt: skip
    return marcos, sorted(vivos)


def _pagamentos(eventos: list[int]) -> list[dict[str, Any]]:
    if not eventos:
        return []
    pix = dict(
        db.session.query(PixRecebido.event_payment_id, func.min(PixRecebido.recebido_em))
        .join(EventPayment, EventPayment.id == PixRecebido.event_payment_id)
        .filter(EventPayment.event_id.in_(eventos))
        .group_by(PixRecebido.event_payment_id)
        .all()
    )
    marcos = []
    for pagamento in EventPayment.query.filter(EventPayment.event_id.in_(eventos)).all():
        # O PIX tem a hora real do dinheiro (São Paulo); o comprovante, a hora em que foi anexado (UTC).
        quando = _sp(pix[pagamento.id]) if pagamento.id in pix else _utc(pagamento.created_at)
        valor = format_brl(pagamento.amount, prefix=True) if pagamento.amount is not None else None
        detalhe = _juntar(valor, "PIX" if pagamento.origem == "pix_email" else None)
        marcos.append(_marco("pagamento", quando, K.TITULO_DO_MARCO["pagamento"], detalhe))
    return marcos


def _avaliacoes(eventos: list[int]) -> list[dict[str, Any]]:
    if not eventos:
        return []
    return [
        _marco(
            "avaliacao",
            _utc(f.submitted_at),
            K.TITULO_DO_MARCO["avaliacao"],
            f"Nota {f.score} de 5",
        )
        for f in ClientFeedback.query.filter(ClientFeedback.event_id.in_(eventos)).all()
    ]


def linha_do_tempo(
    ficha: Client, *, com_conversas: bool, com_orcamentos: bool
) -> list[dict[str, Any]]:
    """Os marcos da ficha, do mais novo para o mais antigo, até ``MARCOS_POR_VEZ`` (constantes).

    ``com_conversas``/``com_orcamentos``: a pessoa abre essas telas (só então o marco leva o link).
    """
    eventos, ids_dos_eventos = _eventos(ficha)
    marcos = [
        _entrada(ficha),
        *_conversas(ficha, com_conversas),
        *_orcamentos(ficha, com_orcamentos),
        *_formularios(ficha),
        *eventos,
        *_pagamentos(ids_dos_eventos),
        *_avaliacoes(ids_dos_eventos),
    ]
    marcos.sort(key=lambda m: (m["quando"], -_ORDEM.index(m["tipo"])), reverse=True)
    return [{**m, "quando": m["quando"].isoformat()} for m in marcos[: K.MARCOS_POR_VEZ]]
