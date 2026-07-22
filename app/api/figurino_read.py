"""Endpoint de LEITURA de Figurino (feature 154).

Reusa o núcleo em `app/figurino/figurino_ops.py`. Leitura aberta a qualquer usuário
autenticado, sem gate de papel — paridade com `figurinos()` (Jinja).
"""

from typing import Any

from flask import jsonify

from app.api import api_bp
from app.api_utils import api_login_required


@api_bp.route("/figurino")
@api_login_required
def api_figurino_list() -> Any:
    """Lista as fichas de figurino + personagens sem ficha correspondente (feature 154)."""
    from app.figurino.figurino_ops import list_sheets

    return jsonify(list_sheets())
