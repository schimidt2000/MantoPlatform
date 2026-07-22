"""Endpoints de LEITURA de Talentos (feature 154).

Reusa o núcleo em `app/talents/talent_ops.py` (mesma lógica dos handlers Jinja). Leitura aberta
a qualquer usuário autenticado, sem gate de papel — paridade com `list_talents`/`talent_detail`.
"""

from datetime import datetime, timedelta
from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.models import Talent


def _can_edit_talent() -> bool:
    """Mesmo gate de `_can_edit_talent` (Jinja) — CASTING ou SUPERADMIN."""
    from flask_login import current_user

    from app.constants import RoleName

    return any(r.name in (RoleName.SUPERADMIN, RoleName.CASTING) for r in current_user.roles)


@api_bp.route("/talents/directory")
@api_login_required
def api_talents_directory() -> Any:
    """Busca/filtra talentos paginados (feature 154)."""
    from app.talents.talent_ops import search_talents

    args = request.args
    height_value = args.get("height_value")
    result = search_talents(
        status=args.get("status", "active"),
        q=args.get("q", ""),
        ja_trabalhou=args.get("ja_trabalhou", "0") == "1",
        language=args.getlist("language"),
        race=args.getlist("race"),
        top=args.getlist("top"),
        bottom=args.getlist("bottom"),
        shoe=args.getlist("shoe"),
        height_op=args.get("height_op", "gte"),
        height_value=height_value,
        passport=args.getlist("passport"),
        tags=args.getlist("tag"),
        character=args.get("character", ""),
        page=args.get("page", 1, type=int),
    )
    return jsonify(result)


@api_bp.route("/talents/<int:talent_id>")
@api_login_required
def api_talent_detail(talent_id: int) -> Any:
    """Perfil completo de um talento, com histórico de eventos (feature 154)."""
    from app.talents.talent_ops import get_talent_profile

    talent = Talent.query.get(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)

    date_from_str = request.args.get("date_from", "")
    date_to_str = request.args.get("date_to", "")
    date_from = None
    date_to = None
    try:
        if date_from_str:
            date_from = datetime.fromisoformat(date_from_str)
    except ValueError:
        pass
    try:
        if date_to_str:
            date_to = datetime.fromisoformat(date_to_str) + timedelta(days=1)
    except ValueError:
        pass

    result = get_talent_profile(talent, date_from=date_from, date_to=date_to)
    result["can_edit"] = _can_edit_talent()
    return jsonify(result)
