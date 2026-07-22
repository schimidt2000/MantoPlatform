"""Endpoint de LEITURA do painel de RH (feature 166, US6 — Cauda Administrativa).

`app/rh` não tem lógica de negócio própria além de checar permissões — sem módulo `_ops`,
mesma exceção de "sem núcleo a extrair" das fatias anteriores quando não há regra a reusar.
"""

from typing import Any

from flask import jsonify
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error


@api_bp.route("/rh/dashboard")
@api_login_required
def api_rh_dashboard() -> Any:
    """Painel de RH: indica se o usuário também gerencia usuários (feature 166)."""
    if not current_user.has_permission("rh.view"):
        return json_error("Sem permissão", 403)
    return jsonify({"can_manage_users": current_user.has_permission("user.manage")})
