"""Endpoints de LEITURA da gestão de usuários (feature 167, US6 — Cauda Administrativa).

Reusa, sem duplicar, o núcleo já extraído em `app/admin/user_ops.py` — os endpoints aqui só
validam RBAC e serializam. Gate `require_users_access` reimplementado como função, paridade
com `app/admin/routes.py::require_users_access` (SUPERADMIN ou FINANCEIRO).
"""

from typing import Any

from flask import jsonify
from flask_login import current_user

from app.admin import user_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import Role, SalaryHistory, User


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_users_access() -> Any:
    if not _has_role(RoleName.SUPERADMIN, RoleName.FINANCEIRO):
        return json_error("Sem permissão", 403)
    return None


def _salary_summary(salary: SalaryHistory | None) -> dict | None:
    if salary is None:
        return None
    return {
        "amount": salary.salary,
        "payment_type": salary.payment_type,
        "start_date": salary.start_date.isoformat(),
        "notes": salary.notes or "",
    }


def _user_summary(user: User, salary: SalaryHistory | None) -> dict:
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
        "salary": _salary_summary(salary),
    }


@api_bp.route("/admin/users")
@api_login_required
def api_admin_users_list() -> Any:
    """Lista de usuários com o salário vigente de cada um (feature 167)."""
    denied = _require_users_access()
    if denied:
        return denied
    items = [_user_summary(u, salary) for u, salary in user_ops.list_users_with_salary()]
    all_roles = [{"id": r.id, "name": r.name} for r in Role.query.order_by(Role.name.asc()).all()]
    return jsonify({"items": items, "all_roles": all_roles})


@api_bp.route("/admin/users/<int:user_id>")
@api_login_required
def api_admin_user_detail(user_id: int) -> Any:
    """Ficha de um usuário, com o histórico completo de salário (feature 167)."""
    denied = _require_users_access()
    if denied:
        return denied
    user = User.query.get(user_id)
    if user is None:
        return json_error("Usuário não encontrado", 404)
    current_salary = user.salary_histories.filter_by(end_date=None).first()
    history = user.salary_histories.order_by(SalaryHistory.start_date.desc()).all()
    return jsonify(
        {
            **_user_summary(user, current_salary),
            "salary_history": [
                {
                    "id": s.id,
                    "amount": s.salary,
                    "payment_type": s.payment_type,
                    "start_date": s.start_date.isoformat(),
                    "end_date": s.end_date.isoformat() if s.end_date else None,
                    "notes": s.notes or "",
                }
                for s in history
            ],
            "all_roles": [
                {"id": r.id, "name": r.name} for r in Role.query.order_by(Role.name.asc()).all()
            ],
        }
    )
