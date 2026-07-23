"""Lógica de agregação do resumo da home/dashboard — fonte única (Princípio I).

As mesmas consultas de tarefas de casting/figurino/dispensados são usadas pela view Jinja
`home` (`app/__init__.py`) e pelo endpoint JSON `GET /api/dashboard`. Extraídas aqui para
não existirem em duas versões paralelas quando a Fundação (feature 144) migra a home.
"""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, not_

from app import db
from app.constants import RoleName
from app.models import CalendarEvent, EventPayment, EventRole, SiteSetting


def dashboard_cutoff() -> datetime:
    """Data de corte das tarefas: `release_date` configurada ou hoje."""
    settings = SiteSetting.query.get(1)
    release = settings.release_date if settings and settings.release_date else date.today()
    return datetime(release.year, release.month, release.day)


def _base_filters(cutoff: datetime) -> dict[str, Any]:
    """Filtros compartilhados pelas consultas de tarefas (mesmos da view `home`)."""
    from app.calendar.routes import PRESENCE_CHARACTER

    return {
        "not_presence": EventRole.character_name != PRESENCE_CHARACTER,
        "exclude_ensaios": not_(CalendarEvent.title.like("🟧 ENSAIO%")),
        "future_events": CalendarEvent.start_at >= cutoff,
        "not_dismissed": EventRole.dismissed_at.is_(None),
    }


def compute_casting_tasks(cutoff: datetime) -> dict[str, Any]:
    """Pendências, convites recusados e contagens de casting (exclui presença/dispensados)."""
    f = _base_filters(cutoff)
    pending = (
        EventRole.query.filter(EventRole.talent_id.is_(None), f["not_presence"], f["not_dismissed"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    rejected_invites = (
        EventRole.query.filter(EventRole.invite_status == "rejected")
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    total = (
        EventRole.query.filter(f["not_presence"], f["not_dismissed"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .count()
    )
    done = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.invite_status != "rejected",
            f["not_presence"],
            f["not_dismissed"],
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .count()
    )
    return {"pending": pending, "rejected_invites": rejected_invites, "total": total, "done": done}


def compute_figurino_tasks(cutoff: datetime) -> dict[str, Any]:
    """Pendências e contagens de figurino (roles com talento, sem figurino, exceto extras)."""
    f = _base_filters(cutoff)
    pending = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.figurino_done_at.is_(None),
            EventRole.invite_status != "rejected",
            EventRole.role_type != "extra",
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    total = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.invite_status != "rejected",
            EventRole.role_type != "extra",
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .count()
    )
    return {"pending": pending, "total": total, "done": total - len(pending)}


def compute_dismissed_casting_tasks(cutoff: datetime) -> list[EventRole]:
    """Cargos de casting dispensados (feature 108) — só o SUPERADMIN vê e restaura."""
    f = _base_filters(cutoff)
    return (
        EventRole.query.filter(EventRole.dismissed_at.isnot(None), f["not_presence"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"])
        .order_by(EventRole.dismissed_at.desc())
        .all()
    )


def serialize_task_ref(role: EventRole) -> dict[str, Any]:
    """Referência enxuta de um cargo/evento para o JSON do dashboard (data-model.md)."""
    event = role.event
    return {
        "role_id": role.id,
        "event_id": role.event_id,
        "event_title": event.title if event else "",
        "character_name": role.character_name,
        "start_at": event.start_at.isoformat() if event and event.start_at else None,
    }


_SEVERITY_ORDER = {"atrasado": 0, "vencido": 1, "urgent": 2, "warn": 3, "info": 4}


def compute_comercial_pending(cutoff: datetime) -> list[dict[str, Any]]:
    """Cobranças pendentes (saldo em aberto) por evento.

    Extraída de `app/__init__.py::home()` (política: à vista, ou 50% no ato + 50% até 2 dias
    antes do evento; `futuro`/`faturado` têm data combinada própria via `payment_due_date`) —
    fonte única para Jinja e API, mesmo padrão de `compute_casting_tasks`.

    Args:
        cutoff: data de corte das tarefas (mesma usada pelas demais consultas do dashboard).

    Returns:
        Lista de pendências (``event`` é o objeto ``CalendarEvent`` cru), ordenada por
        severidade e depois por data do evento. Use `serialize_comercial_pending` para o JSON.
    """
    from zoneinfo import ZoneInfo

    f = _base_filters(cutoff)
    today_sp = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    sale_events = (
        CalendarEvent.query.filter(
            CalendarEvent.sale_value.isnot(None),
            CalendarEvent.sale_value > 0,
            f["future_events"],
            f["exclude_ensaios"],
        )
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    received_by_event = dict(
        db.session.query(
            EventPayment.event_id,
            func.coalesce(func.sum(EventPayment.amount), 0),
        )
        .filter(EventPayment.event_id.in_([e.id for e in sale_events] or [0]))
        .group_by(EventPayment.event_id)
        .all()
    )

    pending: list[dict[str, Any]] = []
    for ev in sale_events:
        sale = float(ev.sale_value)
        received = float(received_by_event.get(ev.id, 0))
        saldo = sale - received
        if saldo <= 0:
            continue
        ev_date = ev.start_at.date() if ev.start_at else None
        is_past = bool(ev_date and ev_date < today_sp)
        due_date = None
        if ev.payment_method in ("futuro", "faturado") and ev.payment_due_date:
            due_date = ev.payment_due_date
            severity = "vencido" if due_date <= today_sp else "info"
        elif is_past:
            severity = "atrasado"
        else:
            days_left = (ev_date - today_sp).days if ev_date else None
            if days_left is not None and days_left <= 2:
                severity = "urgent"
            elif received < sale * 0.5:
                severity = "warn"
            else:
                continue
        pending.append(
            {
                "event": ev,
                "sale": sale,
                "received": received,
                "saldo": saldo,
                "severity": severity,
                "due_date": due_date,
                "is_past": is_past,
            }
        )

    pending.sort(key=lambda p: (_SEVERITY_ORDER[p["severity"]], p["event"].start_at or datetime.max))
    return pending


def serialize_comercial_pending(item: dict[str, Any]) -> dict[str, Any]:
    """Serializa um item de `compute_comercial_pending` para o JSON do dashboard."""
    ev = item["event"]
    due_date = item["due_date"]
    return {
        "event_id": ev.id,
        "event_title": ev.title,
        "start_at": ev.start_at.isoformat() if ev.start_at else None,
        "sale": item["sale"],
        "received": item["received"],
        "saldo": item["saldo"],
        "severity": item["severity"],
        "due_date": due_date.isoformat() if due_date else None,
    }


def compute_performance(start_dt: datetime | None, end_dt: datetime | None) -> dict[str, Any]:
    """Agregado de Performance (SUPERADMIN): casting/figurino done/total e entrada total.

    Extraída de `app/__init__.py::home()` (linhas ~528-576) — fonte única para Jinja e API.

    Args:
        start_dt: início do período (inclusive), ou ``None`` se o período for inválido.
        end_dt: fim do período (exclusive), ou ``None`` se o período for inválido.

    Returns:
        Dicionário com `casting_total`, `casting_done`, `figurino_total`, `figurino_done` e
        `money_total` (zerados quando o período é inválido).
    """
    empty = {
        "casting_total": 0,
        "casting_done": 0,
        "figurino_total": 0,
        "figurino_done": 0,
        "money_total": 0.0,
    }
    if start_dt is None or end_dt is None:
        return empty

    exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
    perf_filter = and_(
        CalendarEvent.start_at >= start_dt, CalendarEvent.start_at < end_dt, exclude_ensaios
    )
    casting_total = EventRole.query.join(CalendarEvent).filter(perf_filter).count()
    casting_done = (
        EventRole.query.filter(EventRole.assigned_at.isnot(None))
        .join(CalendarEvent)
        .filter(perf_filter)
        .count()
    )
    figurino_total = casting_total
    figurino_done = (
        EventRole.query.filter(EventRole.figurino_done_at.isnot(None))
        .join(CalendarEvent)
        .filter(perf_filter)
        .count()
    )
    money_total = (
        db.session.query(func.coalesce(func.sum(EventRole.cache_value), 0))
        .join(CalendarEvent)
        .filter(perf_filter, EventRole.assigned_at.isnot(None))
        .scalar()
    )
    return {
        "casting_total": casting_total,
        "casting_done": casting_done,
        "figurino_total": figurino_total,
        "figurino_done": figurino_done,
        "money_total": float(money_total),
    }


def resolve_performance_period(
    perf_range: str, perf_start: str | None, perf_end: str | None
) -> tuple[datetime | None, datetime | None]:
    """Resolve `perf_range`/`perf_start`/`perf_end` (query params) num intervalo `[start, end)`.

    Mesma regra do Jinja: `"30"` = últimos 30 dias; `"custom"` exige `perf_start`/`perf_end`
    ISO válidos com `start <= end`; qualquer outro valor (inclusive `"7"`/ausente) = últimos 7
    dias. Datas inválidas ou fora de ordem retornam ``(None, None)`` (fallback silencioso).
    """
    if perf_range == "30":
        end_dt = datetime.utcnow()
        return end_dt - timedelta(days=30), end_dt
    if perf_range == "custom":
        if not perf_start or not perf_end:
            return None, None
        try:
            start_dt = datetime.fromisoformat(perf_start)
            end_dt = datetime.fromisoformat(perf_end) + timedelta(days=1)
        except ValueError:
            return None, None
        if start_dt > end_dt:
            return None, None
        return start_dt, end_dt
    end_dt = datetime.utcnow()
    return end_dt - timedelta(days=7), end_dt


def _is_real_superadmin(user: Any) -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in user.roles)


def _effective_has_role(user: Any, impersonate: str | None, name: str) -> bool:
    """Papel efetivo, respeitando a impersonação do SUPERADMIN (mesma lógica da view home)."""
    if impersonate and _is_real_superadmin(user):
        return impersonate.upper() == name.upper()
    return any(r.name.upper() == name.upper() for r in user.roles)


def build_dashboard_summary(
    user: Any,
    impersonate: str | None,
    perf_range: str = "7",
    perf_start: str | None = None,
    perf_end: str | None = None,
) -> dict[str, Any]:
    """Monta o resumo do dashboard para o endpoint JSON, filtrado por papel.

    Args:
        user: Usuário autenticado (``current_user``).
        impersonate: Papel impersonado na sessão, ou ``None``.
        perf_range: período do painel Performance (``"7"``, ``"30"`` ou ``"custom"``).
        perf_start: início do período customizado (ISO date), quando ``perf_range="custom"``.
        perf_end: fim do período customizado (ISO date), quando ``perf_range="custom"``.

    Returns:
        Dicionário no formato de `data-model.md` (seções ``None`` = sem permissão).
    """
    cutoff = dashboard_cutoff()
    is_superadmin = _is_real_superadmin(user) and not impersonate
    show_casting = _effective_has_role(user, impersonate, RoleName.CASTING) or is_superadmin
    show_figurino = _effective_has_role(user, impersonate, RoleName.FIGURINO) or is_superadmin
    show_financeiro = _effective_has_role(user, impersonate, RoleName.FINANCEIRO) or is_superadmin
    show_comercial = (
        _effective_has_role(user, impersonate, RoleName.COMERCIAL)
        or show_financeiro
        or is_superadmin
    )

    casting: dict[str, Any] | None = None
    if show_casting:
        raw = compute_casting_tasks(cutoff)
        casting = {
            "pending": [serialize_task_ref(r) for r in raw["pending"]],
            "rejected_invites": [serialize_task_ref(r) for r in raw["rejected_invites"]],
            "total": raw["total"],
            "done": raw["done"],
        }

    figurino: dict[str, Any] | None = None
    if show_figurino:
        raw_fig = compute_figurino_tasks(cutoff)
        figurino = {
            "pending": [serialize_task_ref(r) for r in raw_fig["pending"]],
            "total": raw_fig["total"],
            "done": raw_fig["done"],
        }

    financeiro: dict[str, Any] | None = None
    if show_financeiro:
        from app.gastos.routes import ensure_recurring_entries, recurring_alerts

        today = date.today()
        ensure_recurring_entries(today.year, today.month)
        alerts = recurring_alerts(today)
        financeiro = {"recurring_expense_alerts": [_serialize_alert(a) for a in alerts]}

    comercial: dict[str, Any] | None = None
    if show_comercial:
        comercial = {
            "pending_payments": [
                serialize_comercial_pending(p) for p in compute_comercial_pending(cutoff)
            ]
        }

    performance: dict[str, Any] | None = None
    if is_superadmin:
        start_dt, end_dt = resolve_performance_period(perf_range, perf_start, perf_end)
        if start_dt is not None and end_dt is not None:
            perf = compute_performance(start_dt, end_dt)
            # `end_dt` é exclusive (para a query); `perf_range="custom"` já entra com +1 dia
            # para cobrir o dia inteiro (ver `resolve_performance_period`) — subtrai de volta
            # só para exibição, sem afetar a contagem.
            display_end = end_dt - timedelta(days=1) if perf_range == "custom" else end_dt
            performance = {
                "range": perf_range,
                "start": start_dt.date().isoformat(),
                "end": display_end.date().isoformat(),
                **perf,
            }

    dismissed = (
        [serialize_task_ref(r) for r in compute_dismissed_casting_tasks(cutoff)]
        if is_superadmin
        else []
    )

    return {
        "casting": casting,
        "figurino": figurino,
        "comercial": comercial,
        "financeiro": financeiro,
        "performance": performance,
        "dismissed_casting": dismissed,
    }


def _serialize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Serializa um alerta de conta recorrente (shape de `recurring_alerts`).

    O alerta é ``{"conta": RecurringExpense, "estado": str, "entry": RecurringExpenseEntry|None}``.
    O valor vem do lançamento do mês quando já existe (``a_pagar``); senão, do valor
    esperado da conta (``aguardando``).
    """
    conta = alert["conta"]
    entry = alert.get("entry")
    amount = entry.amount if entry is not None else conta.amount
    return {
        "name": conta.name,
        "due_day": conta.due_day,
        "amount": float(amount) if amount is not None else None,
    }
