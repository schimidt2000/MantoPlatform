"""Endpoint do resumo do dashboard (`GET /api/dashboard`)."""

from typing import Any

from flask import jsonify, session
from flask_login import current_user

from app.api import api_bp
from app.api.dashboard_service import build_dashboard_summary
from app.api_utils import api_login_required


@api_bp.route("/dashboard")
@api_login_required
def api_dashboard() -> Any:
    """Retorna o resumo da home filtrado pelo papel do usuário autenticado."""
    impersonate = session.get("impersonate_role")
    return jsonify(build_dashboard_summary(current_user, impersonate))
