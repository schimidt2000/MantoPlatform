"""Endpoints de leitura da Agenda/Eventos (`/api/agenda*`) — feature 145, US1.

Só leitura: lê do banco, nunca dispara sincronização com o Google (sync manual é ação de
escrita, fatia US5). As views Jinja `/agenda` e `/agenda/day/<date>` seguem intactas.
"""

from datetime import datetime
from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.agenda_read import build_agenda_month, serialize_event_summary
from app.api_utils import api_login_required, json_error
from app.calendar.routes import _query_month_events  # noqa: F401 (mantém dependência explícita)
from app.models import CalendarEvent


@api_bp.route("/agenda")
@api_login_required
def api_agenda() -> Any:
    """Agenda de um mês (`?ym=YYYY-MM`; sem parâmetro usa o mês atual)."""
    ym = (request.args.get("ym") or "").strip()
    if ym:
        try:
            year_str, month_str = ym.split("-")
            year, month = int(year_str), int(month_str)
            if not 1 <= month <= 12:
                raise ValueError
        except (ValueError, AttributeError):
            return json_error("Mês inválido (use YYYY-MM)", 400)
    else:
        now = datetime.now()
        year, month = now.year, now.month

    return jsonify(build_agenda_month(year, month))


@api_bp.route("/agenda/day/<date_str>")
@api_login_required
def api_agenda_day(date_str: str) -> Any:
    """Eventos de um dia específico (`date_str` = YYYY-MM-DD)."""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return json_error("Data inválida (use YYYY-MM-DD)", 400)

    day_start = datetime(day.year, day.month, day.day)
    day_end = datetime.fromordinal(day_start.toordinal() + 1)
    events = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= day_start, CalendarEvent.start_at < day_end)
        .order_by(CalendarEvent.start_at)
        .all()
    )
    return jsonify(
        {"day": day.isoformat(), "events": [serialize_event_summary(e) for e in events]}
    )
