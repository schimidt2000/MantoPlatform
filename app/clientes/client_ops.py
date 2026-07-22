"""Núcleo de negócio do CRM de clientes (feature 165).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/clientes/routes.py` quanto pelos endpoints de API (`app/api/clientes_read.py`,
`app/api/clientes_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, nullslast, or_

from app import db
from app.clientes.importer import normalize_phone
from app.feedback.routes import ATTENTION_TAGS, POSITIVE_TAGS
from app.models import CalendarEvent, Client, ClientFeedback, EventClient
from app.talents.routes import _parse_period
from app.utils import strip_accents_lower, unaccent_lower_sql

ALL_FEEDBACK_TAGS = POSITIVE_TAGS + ATTENTION_TAGS
_SEARCH_MIN_CHARS = 2
_SEARCH_LIMIT = 10
_LIST_LIMIT = 300
_ATTENTION_LIMIT = 10
_ATTENTION_SCORE_MAX = 2


class ClientValidationError(Exception):
    """Erro de validação de negócio (nome/telefone) — nunca vazamento de exceção de banco."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def _name_search_conditions(query: str):
    """Monta as condições de busca sem acentos (feature 114) por nome/telefone."""
    like = f"%{strip_accents_lower(query)}%"
    digits = "".join(c for c in query if c.isdigit())
    conditions = [unaccent_lower_sql(Client.name).like(like)]
    if digits:
        conditions.append(Client.phone.ilike(f"%{digits}%"))
    return conditions


def search_clients(query: str) -> list[Client]:
    """Busca clientes por nome ou telefone (sem acentos), até `_SEARCH_LIMIT` resultados."""
    q = (query or "").strip()
    if len(q) < _SEARCH_MIN_CHARS:
        return []
    return (
        Client.query.filter(or_(*_name_search_conditions(q)))
        .order_by(Client.name.asc())
        .limit(_SEARCH_LIMIT)
        .all()
    )


def quick_create_client(
    name: str,
    phone_raw: str,
    *,
    phone_display: str | None = None,
    email: str | None = None,
    company: str | None = None,
) -> tuple[Client, bool]:
    """Cria um cliente (nome + telefone) ou reaproveita o existente por telefone.

    Returns:
        Tupla (cliente, reused) — `reused=True` quando o telefone já pertencia a outro cliente.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise ClientValidationError("name", "Informe o nome do cliente.")
    phone = normalize_phone(phone_raw)
    if not phone:
        raise ClientValidationError("phone", "Telefone inválido. Inclua DDD (e DDI se houver).")

    existing = Client.query.filter_by(phone=phone).first()
    if existing:
        return existing, True

    client = Client(
        name=clean_name[:200],
        phone=phone,
        source="manual",
        phone_display=(phone_display or "").strip()[:30] or None,
        email=(email or "").strip()[:200] or None,
        company=(company or "").strip()[:200] or None,
    )
    db.session.add(client)
    db.session.commit()
    return client, False


def list_clients(query: str) -> tuple[list[Client], dict[int, int], int]:
    """Lista clientes (busca opcional), com contagem de eventos por cliente.

    Returns:
        Tupla (clientes ordenados, contagem de eventos por cliente, total geral de clientes).
    """
    counts = dict(
        db.session.query(EventClient.client_id, func.count(func.distinct(EventClient.event_id)))
        .group_by(EventClient.client_id)
        .all()
    )
    q = (query or "").strip()
    clients_query = Client.query
    if q:
        clients_query = clients_query.filter(or_(*_name_search_conditions(q)))
    clients = clients_query.order_by(Client.name.asc()).limit(_LIST_LIMIT).all()
    clients.sort(key=lambda c: (-counts.get(c.id, 0), c.name.lower()))
    total_clients = Client.query.count()
    return clients, counts, total_clients


def get_client_detail(
    client_id: int,
) -> tuple[Client, list[CalendarEvent], dict[int, str], Decimal]:
    """Ficha do cliente: eventos associados (dedup, mais recente primeiro) e total vendido.

    Returns:
        Tupla (cliente, eventos, relação por evento, total vendido). `None` se não existir.
    """
    client = Client.query.get(client_id)
    if client is None:
        return None, [], {}, Decimal("0")
    assocs = (
        EventClient.query.filter_by(client_id=client.id)
        .join(CalendarEvent)
        .order_by(nullslast(CalendarEvent.start_at.desc()))
        .all()
    )
    seen: set[int] = set()
    events: list[CalendarEvent] = []
    rel_by_event: dict[int, str] = {}
    for a in assocs:
        if a.event_id in seen or not a.event:
            continue
        seen.add(a.event_id)
        events.append(a.event)
        rel_by_event[a.event_id] = a.relationship_type
    total_sales = sum((Decimal(e.sale_value) for e in events if e.sale_value), Decimal("0"))
    return client, events, rel_by_event, total_sales


def update_client_fields(
    client: Client, *, cpf: str | None, cnpj: str | None, address: str | None
) -> None:
    """Atualiza CPF/CNPJ e endereço do cliente (edição manual, feature 119)."""
    client.cpf = (cpf or "").strip()[:20] or None
    client.cnpj = (cnpj or "").strip()[:20] or None
    client.address = (address or "").strip() or None
    db.session.commit()


def delete_client(client: Client) -> None:
    """Exclui um cliente, desvinculando antes os eventos associados (sem referências órfãs)."""
    EventClient.query.filter_by(client_id=client.id).delete()
    CalendarEvent.query.filter_by(client_id=client.id).update({"client_id": None})
    db.session.delete(client)
    db.session.commit()


@dataclass
class FeedbackSummary:
    """Resumo de avaliações das clientes, com os filtros já resolvidos."""

    feedbacks: list[ClientFeedback]
    total: int
    avg_overall: float
    clients_rated: int
    dist: dict[int, int]
    dist_max: int
    attention: list[ClientFeedback]
    clients_with_feedback: list[tuple[int, str]]
    selected_client: Client | None


def summarize_feedback(
    *,
    period: str,
    from_raw: str,
    to_raw: str,
    score: int | None,
    tag: str,
    client_id: int | None,
) -> FeedbackSummary:
    """Resumo do feedback das clientes (feature 130/131) com filtros de período/nota/tag/cliente."""
    period_norm = period if period in ("30d", "90d", "365d", "custom", "all") else "all"
    period_start, period_end = _parse_period(period_norm, from_raw, to_raw)

    tag_norm = tag if tag in ALL_FEEDBACK_TAGS else ""
    selected_client = Client.query.get(client_id) if client_id else None

    fb_query = ClientFeedback.query.join(CalendarEvent, ClientFeedback.event_id == CalendarEvent.id)
    if period_start:
        fb_query = fb_query.filter(ClientFeedback.submitted_at >= period_start)
    if period_end:
        fb_query = fb_query.filter(ClientFeedback.submitted_at < period_end)
    if score:
        fb_query = fb_query.filter(ClientFeedback.score == score)
    if tag_norm:
        fb_query = fb_query.filter(ClientFeedback.tags.ilike(f'%"{tag_norm}"%'))
    if client_id:
        fb_query = fb_query.filter(CalendarEvent.client_id == client_id)
    feedbacks = fb_query.order_by(ClientFeedback.submitted_at.desc()).all()

    total = len(feedbacks)
    avg_overall = round(sum(f.score for f in feedbacks) / total, 1) if total else 0.0
    clients_rated = len({f.event.client_id for f in feedbacks if f.event and f.event.client_id})

    dist = {s: 0 for s in range(1, 6)}
    for f in feedbacks:
        if 1 <= f.score <= 5:
            dist[f.score] += 1
    dist_max = max(dist.values()) if dist else 0

    attention = [f for f in feedbacks if f.score <= _ATTENTION_SCORE_MAX][:_ATTENTION_LIMIT]

    clients_with_feedback = (
        db.session.query(Client.id, Client.name)
        .join(CalendarEvent, CalendarEvent.client_id == Client.id)
        .join(ClientFeedback, ClientFeedback.event_id == CalendarEvent.id)
        .distinct()
        .order_by(Client.name.asc())
        .all()
    )

    return FeedbackSummary(
        feedbacks=feedbacks,
        total=total,
        avg_overall=avg_overall,
        clients_rated=clients_rated,
        dist=dist,
        dist_max=dist_max,
        attention=attention,
        clients_with_feedback=clients_with_feedback,
        selected_client=selected_client,
    )
