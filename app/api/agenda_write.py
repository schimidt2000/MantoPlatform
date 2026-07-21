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


def _can_casting() -> bool:
    """Gate específico das ações de casting que o exigem (ex.: remover cargo)."""
    return any(
        r.name.upper() in (RoleName.CASTING, RoleName.SUPERADMIN) for r in current_user.roles
    )


def _event_detail_json(event: Any) -> Any:
    """Serializa o evento atualizado com o RBAC do usuário atual (resposta padrão das escritas)."""
    impersonate = session.get("impersonate_role")
    return jsonify(serialize_event_detail(event, current_user, impersonate))


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
    return _event_detail_json(event)


@api_bp.route("/events/<int:event_id>/roles", methods=["POST"])
@api_login_required
def api_add_role(event_id: int) -> Any:
    """Adiciona um cargo ao evento (feature 147)."""
    if not _can_edit_event():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    data = request.get_json(silent=True) or {}
    character_name = (data.get("character_name") or "").strip()
    if not character_name:
        return json_error("Informe o nome do personagem", 400, {"character_name": "Obrigatório"})

    from app.calendar.casting_ops import add_role

    add_role(
        event,
        character_name=character_name,
        talent_id=data.get("talent_id"),
        cache_value=data.get("cache_value"),
        role_type=data.get("role_type", "character"),
        actor_name=current_user.name,
        tz=_TZ_SP,
    )
    return _event_detail_json(event)


@api_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@api_login_required
def api_delete_role(role_id: int) -> Any:
    """Remove um cargo (feature 147). Cargo com convite aceito só sai por superadmin."""
    role = EventRole.query.get(role_id)
    if role is None:
        return json_error("Cargo não encontrado", 404)
    if not _can_casting():
        return json_error("Sem permissão", 403)
    event = CalendarEvent.query.get(role.event_id)
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    from app.calendar.casting_ops import delete_role

    removed = delete_role(
        event, role, is_superadmin=is_superadmin, actor_name=current_user.name, tz=_TZ_SP
    )
    if not removed:
        return json_error("Cargo com convite aceito só pode ser removido por um superadmin", 403)
    return _event_detail_json(event)
