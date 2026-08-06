"""Endpoints de LEITURA de Talentos (feature 154).

Reusa o núcleo em `app/talents/talent_ops.py` (mesma lógica dos handlers Jinja). A leitura segue
aberta a qualquer usuário autenticado — paridade com `list_talents`/`talent_detail` —, mas o
PAYLOAD é redigido: dado pessoal sensível, chave PIX, documento e anotação interna só saem sob
`_can_edit_talent()` (ver `TALENT_SENSITIVE_FIELDS` em `talent_ops`).
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


@api_bp.route("/talents/bounces")
@api_login_required
def api_talents_bounces() -> Any:
    """Fila de emails devolvidos, agrupada por endereço (feature 219).

    Mesmo gate da edição de talento (CASTING/SUPERADMIN): a fila expõe telefone e email de quem
    precisa ser contatado, e quem contata é justamente quem pode editar a ficha.
    """
    from app.talents import bounce_ops

    if not _can_edit_talent():
        return json_error("Sem permissão", 403)
    include_resolved = request.args.get("resolvidos", "0") == "1"
    return jsonify(
        {
            "items": bounce_ops.pending_queue(include_resolved=include_resolved),
            "pending_count": bounce_ops.pending_count(),
        }
    )


@api_bp.route("/talents/character-suggestions")
@api_login_required
def api_talents_character_suggestions() -> Any:
    """Sugere personagens já interpretados (feature 180) — espelho JSON de
    `talents.character_suggestions`, mesma função `suggest_characters`."""
    from app.talents.talent_ops import suggest_characters

    return jsonify(suggest_characters(request.args.get("q", "")))


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

    # O bloco sensível (CPF, RG, PIX, CNH, placa e anotações internas) só sai para quem gere
    # talento. A ficha continua abrindo para os demais papéis — sem esses campos.
    can_edit = _can_edit_talent()
    result = get_talent_profile(
        talent, date_from=date_from, date_to=date_to, include_sensitive=can_edit
    )
    result["can_edit"] = can_edit
    return jsonify(result)


def _is_superadmin() -> bool:
    from flask_login import current_user

    from app.constants import RoleName

    return any(r.name == RoleName.SUPERADMIN for r in current_user.roles)


@api_bp.route("/talents/<int:talent_id>/ratings")
@api_login_required
def api_talent_ratings(talent_id: int) -> Any:
    """Avaliações recebidas/dadas por um talento (feature 180) — seção "Avaliações e Notas"."""
    from app.talents.rating_ops import get_talent_ratings_overview

    talent = Talent.query.get(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)

    overview = get_talent_ratings_overview(talent, viewer_is_superadmin=_is_superadmin())
    return jsonify(overview)
