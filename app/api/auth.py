"""Endpoints de autenticação da API JSON (`/api/auth/*`).

Reaproveita o mesmo mecanismo de sessão do Flask-Login usado pelo app Jinja (Q3: cookie
HttpOnly) — a única diferença é o formato de entrada/saída (JSON, sem redirect).
"""

from typing import Any

from flask import jsonify, request, session
from flask_login import current_user, login_user, logout_user
from werkzeug.wrappers import Response

from app import limiter
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import User


def serialize_user(user: User) -> dict[str, Any]:
    """Serializa o usuário autenticado no formato de `data-model.md`.

    O papel efetivo respeita a impersonação de papel do SUPERADMIN (mesma semântica da
    view `home` e dos context processors do app Jinja).
    """
    is_real_superadmin = any(r.name == RoleName.SUPERADMIN for r in user.roles)
    impersonate = session.get("impersonate_role") if is_real_superadmin else None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "roles": [r.name for r in user.roles],
        "is_superadmin": is_real_superadmin and not impersonate,
        "impersonating": impersonate,
    }


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_login() -> Any:
    """Autentica via JSON e abre a sessão de cookie."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first() if email else None
    if not user or not user.has_access or not user.check_password(password):
        return json_error("E-mail ou senha inválidos", 401)

    session.clear()
    login_user(user)
    return jsonify(serialize_user(user))


@api_bp.route("/auth/logout", methods=["POST"])
@api_login_required
def api_logout() -> Response:
    """Encerra a sessão atual."""
    logout_user()
    return Response(status=204)


@api_bp.route("/auth/me")
@api_login_required
def api_me() -> Any:
    """Retorna o usuário autenticado atual."""
    return jsonify(serialize_user(current_user))
