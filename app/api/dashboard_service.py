"""Lógica de agregação do resumo da home/dashboard — fonte única (Princípio I).

As mesmas consultas de tarefas de casting/figurino/dispensados são usadas pela view Jinja
`home` (`app/__init__.py`) e pelo endpoint JSON `GET /api/dashboard`. Extraídas aqui para
não existirem em duas versões paralelas quando a Fundação (feature 144) migra a home.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import not_

from app.constants import RoleName
from app.models import CalendarEvent, EventRole, SiteSetting


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


def _is_real_superadmin(user: Any) -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in user.roles)


def _effective_has_role(user: Any, impersonate: str | None, name: str) -> bool:
    """Papel efetivo, respeitando a impersonação do SUPERADMIN (mesma lógica da view home)."""
    if impersonate and _is_real_superadmin(user):
        return impersonate.upper() == name.upper()
    return any(r.name.upper() == name.upper() for r in user.roles)


def build_dashboard_summary(user: Any, impersonate: str | None) -> dict[str, Any]:
    """Monta o resumo do dashboard para o endpoint JSON, filtrado por papel.

    Args:
        user: Usuário autenticado (``current_user``).
        impersonate: Papel impersonado na sessão, ou ``None``.

    Returns:
        Dicionário no formato de `data-model.md` (seções ``None`` = sem permissão).
    """
    cutoff = dashboard_cutoff()
    is_superadmin = _is_real_superadmin(user) and not impersonate
    show_casting = _effective_has_role(user, impersonate, RoleName.CASTING) or is_superadmin
    show_figurino = _effective_has_role(user, impersonate, RoleName.FIGURINO) or is_superadmin
    show_financeiro = _effective_has_role(user, impersonate, RoleName.FINANCEIRO) or is_superadmin

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

    dismissed = (
        [serialize_task_ref(r) for r in compute_dismissed_casting_tasks(cutoff)]
        if is_superadmin
        else []
    )

    return {
        "casting": casting,
        "figurino": figurino,
        "financeiro": financeiro,
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
