"""Endpoints de LEITURA de Avaliação de Casting (migração 177, US6).

Reusa, sem duplicar, o núcleo já extraído em `app/talents/rating_ops.py` — o endpoint aqui só
valida RBAC (autenticado, sem restrição de papel — mesma regra da view Jinja `avaliacoes()`) e
serializa.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required
from app.talents import rating_ops


@api_bp.route("/ratings")
@api_login_required
def api_ratings_overview() -> Any:
    """Panorama de avaliações (filtros de evento/categoria/período) — qualquer autenticado."""
    is_sa = rating_ops.is_superadmin(current_user)
    overview = rating_ops.build_overview(request.args, is_sa)
    return jsonify({**rating_ops.serialize_overview(overview), "is_superadmin": is_sa})
