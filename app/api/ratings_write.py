"""Endpoints de ESCRITA de Avaliação de Casting (migração 177, US6).

Reusa, sem duplicar, o núcleo já extraído em `app/talents/rating_ops.py`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.talents import rating_ops


@api_bp.route("/ratings/modo-anonimo", methods=["POST"])
@api_login_required
def api_ratings_toggle_anonimo() -> Any:
    """Liga/desliga o modo anônimo total das avaliações (SUPERADMIN)."""
    if not rating_ops.is_superadmin(current_user):
        return json_error("Sem permissão", 403)
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled"))
    rating_ops.set_anonymous_mode(enabled, current_user)
    return jsonify({"fully_anonymous": enabled})
