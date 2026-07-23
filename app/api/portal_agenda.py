"""Endpoints de Agenda e Convites de casting do Portal do Artista (feature 176).

Só orquestra e serializa — a regra de negócio mora em `app/talent_portal/portal_ops.py`, sem
duplicar lógica com a view Jinja legada. RBAC = "é o dono do recurso": toda consulta já filtra
por `talent_id` da sessão (nunca aceita um id de talento vindo do cliente).
"""

from typing import Any

from flask import jsonify

from app.api import api_bp
from app.api.portal_auth import current_talent, portal_api_login_required
from app.api_utils import json_error
from app.talent_portal import portal_ops


@api_bp.route("/portal/agenda")
@portal_api_login_required
def api_portal_agenda() -> Any:
    talent = current_talent()
    return jsonify(portal_ops.get_agenda(talent))


@api_bp.route("/portal/invites/<int:role_id>/accept", methods=["POST"])
@portal_api_login_required
def api_portal_accept_invite(role_id: int) -> Any:
    talent = current_talent()
    role = portal_ops.accept_invite(talent, role_id)
    if role is None:
        return json_error("Convite não encontrado.", 404)
    return jsonify({"role_id": role.id, "invite_status": role.invite_status})


@api_bp.route("/portal/invites/<int:role_id>/reject", methods=["POST"])
@portal_api_login_required
def api_portal_reject_invite(role_id: int) -> Any:
    talent = current_talent()
    role = portal_ops.reject_invite(talent, role_id)
    if role is None:
        return json_error("Convite não encontrado.", 404)
    return jsonify({"role_id": role.id, "invite_status": role.invite_status})


@api_bp.route("/portal/roles/<int:role_id>/ack-change", methods=["POST"])
@portal_api_login_required
def api_portal_ack_change(role_id: int) -> Any:
    talent = current_talent()
    role = portal_ops.ack_event_change(talent, role_id)
    if role is None:
        return json_error("Escalação não encontrada.", 404)
    return jsonify({"role_id": role.id})
