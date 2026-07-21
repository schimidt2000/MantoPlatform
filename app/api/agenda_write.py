"""Endpoints de ESCRITA da Agenda/Eventos (feature 146). Fatia US1: escalar casting.

Cada ação reusa o núcleo em `app/calendar/casting_ops.py` (mesma lógica do handler Jinja) e
devolve o evento no formato de leitura da feature 145. As ações Jinja seguem intactas.
"""

from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify, request, session
from flask_login import current_user

from app.api import api_bp
from app.api.agenda_read import serialize_event_detail
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import CalendarEvent, EventRole

_TZ_SP = ZoneInfo("America/Sao_Paulo")


def _can_edit_event() -> bool:
    """Mesmo gate do POST de /events/<id> (`_CAN_EDIT_EVENT`) — paridade com o Jinja."""
    from app.calendar.routes import _CAN_EDIT_EVENT

    return any(r.name.upper() in _CAN_EDIT_EVENT for r in current_user.roles)


@api_bp.route("/roles/<int:role_id>/assign", methods=["POST"])
@api_login_required
def api_assign_role(role_id: int) -> Any:
    """Escala/atualiza/desescala o talento de um cargo (data-model.md)."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_edit_event():
        return json_error("Sem permissão", 403)

    event = CalendarEvent.query.get(role.event_id)
    data = request.get_json(silent=True) or {}
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    from app.calendar.casting_ops import assign_role

    assign_role(
        event,
        role,
        talent_id=data.get("talent_id"),
        cache_value=data.get("cache_value"),
        travel_cache=data.get("travel_cache"),
        actor_name=current_user.name,
        is_superadmin=is_superadmin,
        tz=_TZ_SP,
    )

    impersonate = session.get("impersonate_role")
    return jsonify(serialize_event_detail(event, current_user, impersonate))
