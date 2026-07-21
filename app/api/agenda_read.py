"""Serialização de leitura da Agenda/Eventos (feature 145, US1).

Fonte única do formato JSON de leitura consumido pela SPA React. Nesta fatia cobre apenas o
RESUMO do evento (agenda); o detalhe do evento (com RBAC financeiro) entra no Incremento B.
Reaproveita os parsers e a query de mês da view Jinja (Princípio I) — não duplica lógica.
"""

from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.constants import RoleName
from app.models import (
    CalendarEvent,
    EventContract,
    EventLog,
    EventPayment,
    EventReimbursement,
    SiteSetting,
    SpecialExpense,
)


def _money(value: Any) -> float | None:
    """Converte Decimal/None em float (JSON não serializa Decimal)."""
    return float(value) if value is not None else None


def serialize_event_summary(event: CalendarEvent) -> dict[str, Any]:
    """Resumo de um evento para a lista/calendário da agenda (data-model.md: EventoResumo).

    Sem nenhum dado financeiro — a agenda não expõe valores.
    """
    # Import tardio: parsers vivem no blueprint calendar (evita import circular no boot).
    from app.calendar.routes import parse_characters, parse_event_type

    return {
        "id": event.id,
        "title": event.title,
        "event_type": parse_event_type(event.title),
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "location": event.location or None,
        "characters": parse_characters(event.title),
        "is_satellite": event.is_satellite,
        "group_name": event.group_name or None,
        "confirmed": event.confirmed_at is not None,
    }


def build_agenda_month(year: int, month: int) -> dict[str, Any]:
    """Monta a resposta da agenda de um mês: eventos + índice por dia (para o calendário).

    Usa a mesma query da view (`_query_month_events`), então o conjunto de eventos é idêntico
    ao que o sistema atual mostra. `by_day` espalha eventos de vários dias por todos os dias
    que eles cobrem dentro do mês (como o calendário Jinja).
    """
    from app.calendar.routes import _query_month_events

    events = _query_month_events(year, month)
    summaries = [serialize_event_summary(e) for e in events]

    by_day: dict[str, list[int]] = {}
    for event in events:
        if not event.start_at:
            continue
        start_day = event.start_at.date()
        end_day = event.end_at.date() if event.end_at else start_day
        cursor = start_day
        while cursor <= end_day:
            if cursor.year == year and cursor.month == month:
                by_day.setdefault(cursor.isoformat(), []).append(event.id)
            cursor = cursor.fromordinal(cursor.toordinal() + 1)

    return {"ym": f"{year:04d}-{month:02d}", "events": summaries, "by_day": by_day}


def _role_flags(user: Any, impersonate: str | None) -> dict[str, bool]:
    """Flags de visibilidade por papel, com a MESMA lógica da view `event_detail`.

    Respeita a impersonação de papel do SUPERADMIN (ver o sistema como outro papel).
    """
    is_real_sa = any(r.name == RoleName.SUPERADMIN for r in user.roles)
    active = impersonate if (impersonate and is_real_sa) else None

    def has(role: str) -> bool:
        if active:
            return active.upper() == role.upper()
        return any(r.name.upper() == role.upper() for r in user.roles)

    is_superadmin = has(RoleName.SUPERADMIN)
    return {
        "show_casting": has(RoleName.CASTING) or is_superadmin,
        "show_figurino": has(RoleName.FIGURINO) or is_superadmin,
        "show_comercial": has(RoleName.COMERCIAL) or has(RoleName.FINANCEIRO) or is_superadmin,
        "show_financeiro": has(RoleName.FINANCEIRO) or is_superadmin,
        "show_ensaio": has(RoleName.ENSAIO) or has(RoleName.CASTING) or is_superadmin,
        "is_superadmin": is_superadmin,
    }


def _serialize_logs(event_id: int) -> list[dict[str, Any]]:
    """Histórico do evento, mais recente primeiro, horário em São Paulo (como a view)."""
    tz_sp = ZoneInfo("America/Sao_Paulo")
    logs = []
    raw = (
        EventLog.query.filter_by(event_id=event_id)
        .order_by(EventLog.created_at.desc())
        .all()
    )
    for log in raw:
        dt = log.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.astimezone(tz_sp)
        logs.append(
            {
                "ts": dt.strftime("%d/%m/%Y %H:%M"),
                "actor_name": log.actor_name,
                "actor_role": log.actor_role,
                "message": log.message,
            }
        )
    return logs


def _serialize_role(role: Any, show_casting: bool) -> dict[str, Any]:
    """Um cargo do elenco. `cache_value` (cachê) só para casting/superadmin (dado do casting)."""
    data: dict[str, Any] = {
        "role_id": role.id,
        "character_name": role.character_name,
        "role_type": role.role_type,
        "talent": {"id": role.talent.id, "name": role.talent.full_name} if role.talent else None,
        "figurino_done": role.figurino_done_at is not None,
        "invite_status": role.invite_status,
        "dismissed": role.dismissed_at is not None,
    }
    if show_casting:
        data["cache_value"] = _money(role.cache_value)
    return data


def _compute_kpi(event: CalendarEvent) -> dict[str, Any]:
    """KPIs financeiros agregados pelo grupo comercial — mesma fórmula da view `event_detail`."""
    from app.calendar.routes import _group_events

    settings = SiteSetting.query.get(1)
    default_rate = Decimal(str(
        settings.default_commission_rate
        if settings and settings.default_commission_rate is not None
        else 2
    ))
    group = _group_events(event)
    kpi_event = group[0]
    rate = (
        Decimal(str(kpi_event.commission_rate))
        if kpi_event.commission_rate is not None else default_rate
    )
    cost = sum((r.cache_value or 0 for ge in group for r in ge.roles if r.talent_id), Decimal("0"))
    expenses_total = sum(
        (
            e.amount
            for e in SpecialExpense.query.filter(
                SpecialExpense.event_id.in_([ge.id for ge in group]),
                SpecialExpense.status == "aprovado",
            ).all()
        ),
        Decimal("0"),
    )
    bv_total = sum(
        (
            Decimal(a.amount_brl)
            for ge in group for a in ge.acrescimos if a.is_bv and a.amount_brl
        ),
        Decimal("0"),
    )
    sale = Decimal(kpi_event.sale_value or 0)
    base = sale - bv_total
    if base < 0:
        base = Decimal("0")
    commission = (base * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lucro = sale - Decimal(cost) - expenses_total - bv_total
    return {
        "sale_value": _money(sale),
        "cost": _money(cost),
        "expenses_total": _money(expenses_total),
        "bv_total": _money(bv_total),
        "commission": _money(commission),
        "lucro": _money(lucro),
        "rate": float(rate),
        "group_size": len(group),
        "seller": kpi_event.seller.name if kpi_event.seller else None,
    }


def _compute_cobranca(
    event: CalendarEvent, payments: list[EventPayment]
) -> dict[str, Any]:
    """Saldo em aberto + data limite da cobrança — mesma política da view."""
    today = date.today()
    policy_due = event.start_at.date() - timedelta(days=2) if event.start_at else None
    unreceived = [i for i in event.installments if not i.received]
    if event.installments:
        outstanding = sum((i.amount or 0 for i in unreceived), Decimal("0"))
        due_dates = [i.due_date for i in unreceived if i.due_date]
        due = min(due_dates) if due_dates else policy_due
    else:
        received = sum((p.amount or 0 for p in payments), Decimal("0"))
        outstanding = Decimal(event.sale_value or 0) - received
        due = event.payment_due_date or policy_due
    enabled = due is not None and due <= today and outstanding > 0
    return {
        "outstanding": _money(outstanding),
        "due": due.isoformat() if due else None,
        "enabled": bool(enabled),
    }


def serialize_event_detail(
    event: CalendarEvent, user: Any, impersonate: str | None
) -> dict[str, Any]:
    """Detalhe do evento para leitura, com RBAC (data-model.md). Blocos financeiros só
    entram no JSON conforme o papel — nunca serializados para quem não os veria (FR-003).
    """
    from app.calendar.routes import parse_characters, parse_event_type

    flags = _role_flags(user, impersonate)
    is_ensaio = event.event_type == "ENSAIO"

    data: dict[str, Any] = {
        "event": {
            "id": event.id,
            "title": event.title,
            "event_type": parse_event_type(event.title),
            "start_at": event.start_at.isoformat() if event.start_at else None,
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "location": event.location or None,
            "confirmed": event.confirmed_at is not None,
            "is_satellite": event.is_satellite,
            "group_name": event.group_name or None,
            "characters": parse_characters(event.title),
            "is_ensaio": is_ensaio,
        },
        "flags": flags,
        "logs": _serialize_logs(event.id),
    }

    # ENSAIO: painel simplificado (sem seções de show).
    if is_ensaio:
        return data

    data["elenco"] = [_serialize_role(r, flags["show_casting"]) for r in event.roles]
    data["observations"] = [
        {
            "id": o.id,
            "obs_type": o.obs_type,
            "content": o.content,
            "label": o.label,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in event.observations
    ]

    payments = (
        EventPayment.query.filter_by(event_id=event.id)
        .order_by(EventPayment.created_at.desc())
        .all()
    )

    # Bloco comercial (venda, contratos, cobrança) — COMERCIAL/FINANCEIRO/SUPERADMIN.
    if flags["show_comercial"]:
        data["venda"] = {
            "sale_value": _money(event.sale_value),
            "sale_value_gross": _money(event.sale_value_gross),
            "seller": event.seller.name if event.seller else None,
            "commission_rate": event.commission_rate,
            "payment_method": event.payment_method,
            "payment_due_date": event.payment_due_date.isoformat() if event.payment_due_date else None,
            "clients": [
                {"name": ec.client.name if ec.client else None, "relation": ec.relationship_type}
                for ec in event.event_clients
            ],
        }
        data["contratos"] = [
            {
                "id": c.id,
                "file_path": c.file_path,
                "is_signed": c.is_signed,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in EventContract.query.filter_by(event_id=event.id)
            .order_by(EventContract.created_at.desc())
            .all()
        ]
        data["cobranca"] = _compute_cobranca(event, payments)

    # KPIs, pagamentos e reembolsos — FINANCEIRO/SUPERADMIN.
    if flags["show_financeiro"]:
        data["kpi"] = _compute_kpi(event)
        data["pagamentos"] = {
            "items": [
                {
                    "id": p.id,
                    "amount": _money(p.amount),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
            "received_total": _money(sum((p.amount or 0 for p in payments), Decimal("0"))),
        }
        reembolsos = (
            EventReimbursement.query.filter_by(event_id=event.id)
            .order_by(EventReimbursement.created_at.desc())
            .all()
        )
        data["reembolsos"] = {
            "items": [
                {
                    "id": r.id,
                    "description": r.description,
                    "amount": _money(r.amount),
                    "is_collected": r.is_collected,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reembolsos
            ],
            "pendentes_total": _money(
                sum((r.amount or 0 for r in reembolsos if not r.is_collected), Decimal("0"))
            ),
        }

    return data
