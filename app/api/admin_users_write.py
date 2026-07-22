"""Endpoints de ESCRITA da gestão de usuários (feature 167, US6 — Cauda Administrativa).

Reusa, sem duplicar, o núcleo já extraído em `app/admin/user_ops.py`. Gate base:
`require_users_access` (SUPERADMIN/FINANCEIRO); identidade/criar/conceder-acesso/resetar-senha/
excluir exigem SUPERADMIN — mesma paridade de `app/admin/routes.py`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.admin import user_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import User


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_users_access() -> Any:
    if not _has_role(RoleName.SUPERADMIN, RoleName.FINANCEIRO):
        return json_error("Sem permissão", 403)
    return None


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email or "",
        "has_access": user.has_access,
        "is_active": bool(user.is_active),
        "receives_commission": user.receives_commission,
        "pix_key": user.pix_key or "",
        "pix_key_type": user.pix_key_type or "",
        "role_names": [r.name for r in user.roles],
        "role_ids": [r.id for r in user.roles],
    }


def _salary_input_from_json(body: dict) -> user_ops.SalaryInput | None:
    salary_body = body.get("salary")
    if not salary_body:
        return None
    return user_ops.SalaryInput(
        amount=salary_body.get("amount"),
        payment_type=salary_body.get("payment_type", ""),
        start_date=salary_body.get("start_date"),
        notes=salary_body.get("notes"),
    )


@api_bp.route("/admin/users", methods=["POST"])
@api_login_required
def api_admin_users_create() -> Any:
    """Cria um usuário (com acesso ou só-pagamento), com PIX/salário opcionais (feature 167)."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        user = user_ops.create_user(
            user_type=body.get("user_type", "access"),
            name=body.get("name", ""),
            email=body.get("email"),
            temp_password=body.get("temp_password"),
            role_ids=body.get("role_ids"),
            pix_key=body.get("pix_key"),
            pix_key_type=body.get("pix_key_type"),
            salary=_salary_input_from_json(body),
        )
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_user_summary(user)), 201


@api_bp.route("/admin/users/<int:user_id>", methods=["PATCH"])
@api_login_required
def api_admin_users_update(user_id: int) -> Any:
    """Atualiza identidade/papéis/status/comissão de um usuário (feature 167)."""
    denied = _require_superadmin()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        user_ops.update_user_identity(
            user,
            name=body.get("name", ""),
            email=body.get("email"),
            is_active=bool(body.get("is_active", True)),
            receives_commission=bool(body.get("receives_commission", True)),
            role_ids=body.get("role_ids"),
        )
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_user_summary(user))


@api_bp.route("/admin/users/<int:user_id>/pix", methods=["PATCH"])
@api_login_required
def api_admin_users_update_pix(user_id: int) -> Any:
    """Atualiza a chave PIX de um usuário (feature 167)."""
    denied = _require_users_access()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    body = request.get_json(silent=True) or {}
    user_ops.update_pix(user, pix_key=body.get("pix_key"), pix_key_type=body.get("pix_key_type"))
    return jsonify(_user_summary(user))


@api_bp.route("/admin/users/<int:user_id>/salary", methods=["POST"])
@api_login_required
def api_admin_users_add_salary(user_id: int) -> Any:
    """Registra um novo salário para o usuário, encerrando o vigente (feature 167)."""
    denied = _require_users_access()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    body = request.get_json(silent=True) or {}
    salary = user_ops.SalaryInput(
        amount=body.get("amount"),
        payment_type=body.get("payment_type", ""),
        start_date=body.get("start_date"),
        notes=body.get("notes"),
    )
    try:
        entry = user_ops.add_salary(user, salary)
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(
        {
            "id": entry.id,
            "amount": entry.salary,
            "payment_type": entry.payment_type,
            "start_date": entry.start_date.isoformat(),
        }
    )


@api_bp.route("/admin/users/<int:user_id>/grant-access", methods=["POST"])
@api_login_required
def api_admin_users_grant_access(user_id: int) -> Any:
    """Concede acesso ao sistema a uma pessoa cadastrada só para pagamento (feature 167)."""
    denied = _require_superadmin()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        user_ops.grant_access(
            user, email=body.get("email", ""), temp_password=body.get("temp_password", "")
        )
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_user_summary(user))


@api_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@api_login_required
def api_admin_users_reset_password(user_id: int) -> Any:
    """Reseta a senha de um usuário (feature 167)."""
    denied = _require_superadmin()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        user_ops.reset_password(user, temp_password=body.get("temp_password", ""))
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"ok": True})


@api_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@api_login_required
def api_admin_users_delete(user_id: int) -> Any:
    """Exclui um usuário sem histórico financeiro vinculado (feature 167)."""
    denied = _require_superadmin()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    try:
        user_ops.delete_user(user, actor_id=current_user.id)
    except user_ops.UserValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    except user_ops.UserDeletionBlockedError as exc:
        return jsonify({"error": {"message": exc.message, "blockers": exc.blockers}}), 400
    return "", 204
