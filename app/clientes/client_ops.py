"""Núcleo de negócio do CRM de clientes (feature 165).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/clientes/routes.py` quanto pelos endpoints de API (`app/api/clientes_read.py`,
`app/api/clientes_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, nullslast, or_
from sqlalchemy.orm import joinedload

from app import db
from app.clientes.importer import normalize_phone
from app.feedback.routes import ATTENTION_TAGS, POSITIVE_TAGS
from app.models import CalendarEvent, Client, ClientFeedback, EventClient, FormResponse
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


def list_client_form_history(client_id: int, limit: int = 100) -> list[FormResponse]:
    """Formulários preenchidos pela cliente — o registro das festas dela.

    É a fonte do "que ela já fechou" para marketing, inclusive as festas anteriores a
    2026 que não existem na agenda (decisão de 06/08/2026: o histórico vem dos
    formulários; eventos passados não são materializados no calendário). Ordena pela
    data da festa (mais recente primeiro; sem data vai para o fim).
    """
    return (
        FormResponse.query.options(joinedload(FormResponse.event))
        .filter(FormResponse.client_id == client_id)
        .order_by(nullslast(FormResponse.event_date.desc()), FormResponse.created_at.desc())
        .limit(limit)
        .all()
    )


# Meses exibidos no gráfico de novos clientes da página de clientes.
_METRICS_MONTHS = 12


def client_metrics() -> dict:
    """Métricas da página de clientes (decisão de 06/08/2026).

    * ``new_by_month``: clientes novos por mês (últimos ``_METRICS_MONTHS``), com origem
      agregada. Para importados do Kommo vale ``kommo_created_at`` (quando o lead entrou
      de fato), não a data da carga — senão a importação viraria um pico falso num mês só.
    * ``recurring_clients``: clientes com 2+ eventos distintos — alvo de recompra.
    * ``clients_with_event``: clientes com pelo menos 1 evento associado.
    """
    entered_at = db.func.coalesce(Client.kommo_created_at, Client.created_at)
    month_expr = db.func.to_char(entered_at, "YYYY-MM")
    rows = (
        db.session.query(month_expr, Client.source, func.count(Client.id))
        .group_by(month_expr, Client.source)
        .all()
    )
    by_month: dict[str, dict] = {}
    source_keys = {"whatsform_import": "formulario", "kommo_import": "kommo"}
    for month, source, count in rows:
        entry = by_month.setdefault(
            month, {"month": month, "total": 0, "formulario": 0, "kommo": 0, "manual": 0}
        )
        entry["total"] += count
        entry[source_keys.get(source, "manual")] += count
    months = sorted(by_month.values(), key=lambda m: m["month"], reverse=True)
    months = list(reversed(months[:_METRICS_MONTHS]))  # cronológico, do mais antigo ao atual

    event_counts = (
        db.session.query(EventClient.client_id, func.count(func.distinct(EventClient.event_id)))
        .group_by(EventClient.client_id)
        .all()
    )
    return {
        "new_by_month": months,
        "recurring_clients": sum(1 for _cid, n in event_counts if n >= 2),
        "clients_with_event": len(event_counts),
    }


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


def delete_feedback(feedback: ClientFeedback) -> None:
    """Exclui uma avaliação recebida incorretamente (SUPERADMIN, gate na view).

    Exclusão dura e auditada — não há soft-delete no model; o registro de auditoria é o
    rastro que sobra.
    """
    from app.utils import audit

    audit(
        "delete",
        "client_feedback",
        feedback.id,
        feedback.client_name or "Cliente",
        f"Avaliação {feedback.score}/5 do evento #{feedback.event_id} excluída",
    )
    db.session.delete(feedback)
    db.session.commit()


# Caractere de escape do LIKE nas buscas por tag. Precisa ser explícito: o padrão do
# PostgreSQL é a barra invertida, que aparece dentro do próprio texto procurado (`⏰`).
_LIKE_ESCAPE_CHAR = "!"


def _like_literal(value: str) -> str:
    """Neutraliza os curingas do LIKE (`%`, `_`) e o próprio caractere de escape."""
    for char in (_LIKE_ESCAPE_CHAR, "%", "_"):
        value = value.replace(char, _LIKE_ESCAPE_CHAR + char)
    return value


def _tag_match_conditions(tag: str) -> list:
    """Condições que casam uma tag dentro do JSON de `ClientFeedback.tags` (feature 197).

    Toda tag do formulário público começa com emoji, e as duas rotas de escrita gravam com
    `json.dumps(...)` sem `ensure_ascii=False` — o banco guarda a forma escapada
    (`["\\u23f0 Pontualidade"]`). O filtro antigo procurava o emoji literal com o LIKE padrão,
    e errava duas vezes: pelo texto (que está escapado no banco) e pela barra invertida, que o
    PostgreSQL consome como escape. Aqui procuramos as duas formas, com `ESCAPE '!'` para que
    a barra invertida valha como caractere comum.

    Args:
        tag: Tag já validada contra `ALL_FEEDBACK_TAGS`.

    Returns:
        Lista de condições SQL para combinar com `or_`.
    """
    as_written = json.dumps(tag)  # já vem com as aspas: '"\\u23f0 Pontualidade"'
    as_unicode = f'"{tag}"'  # caso alguma linha tenha sido gravada sem escapar
    return [
        ClientFeedback.tags.ilike(
            f"%{_like_literal(pattern)}%", escape=_LIKE_ESCAPE_CHAR
        )
        for pattern in (as_written, as_unicode)
    ]


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
    # Índice de excelência (feature 197): % das avaliações do recorte que são 5 estrelas.
    pct_five: float


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

    # `joinedload` (feature 197): a serialização lê `f.event.title` e `f.event.client.name` em
    # cada linha — sem isso o `lazy=True` das relações dispara 2 SELECTs por avaliação (N+1).
    fb_query = ClientFeedback.query.join(
        CalendarEvent, ClientFeedback.event_id == CalendarEvent.id
    ).options(joinedload(ClientFeedback.event).joinedload(CalendarEvent.client))
    if period_start:
        fb_query = fb_query.filter(ClientFeedback.submitted_at >= period_start)
    if period_end:
        fb_query = fb_query.filter(ClientFeedback.submitted_at < period_end)
    if score:
        fb_query = fb_query.filter(ClientFeedback.score == score)
    if tag_norm:
        fb_query = fb_query.filter(or_(*_tag_match_conditions(tag_norm)))
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
    pct_five = round(dist[5] / total * 100, 1) if total else 0.0

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
        pct_five=pct_five,
    )
