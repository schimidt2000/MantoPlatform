"""Endpoint do resumo do dashboard (`GET /api/dashboard`)."""

from typing import Any

from flask import jsonify, request, session
from flask_login import current_user

from app.api import api_bp
from app.api.dashboard_service import build_dashboard_summary
from app.api_utils import api_login_required


@api_bp.route("/dashboard")
@api_login_required
def api_dashboard() -> Any:
    """Retorna o resumo da home filtrado pelo papel do usuário autenticado.

    Aceita `perf_range` (``"7"``|``"30"``|``"custom"``, default ``"7"``) e, para
    ``perf_range=custom``, `perf_start`/`perf_end` (ISO date) — controlam o painel
    Performance (SUPERADMIN). Período ausente/inválido não é erro: a resposta traz
    ``performance: null`` (mesmo fallback silencioso do sistema clássico).
    """
    impersonate = session.get("impersonate_role")
    perf_range = request.args.get("perf_range", "7")
    perf_start = request.args.get("perf_start")
    perf_end = request.args.get("perf_end")
    return jsonify(
        build_dashboard_summary(current_user, impersonate, perf_range, perf_start, perf_end)
    )
