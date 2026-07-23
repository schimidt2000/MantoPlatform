"""Endpoints de autenticação do Portal do Artista (feature 176).

Sessão própria do talento — reaproveita a MESMA chave de sessão (`talent_id`) já usada por
`app/talent_portal/routes.py` (Jinja legado), para que um talento autenticado numa versão
continue autenticado na outra (pesquisa em `research.md` §1). Auth por decorator (só verifica
sessão, não papel — Talent não tem RBAC), paridade de propósito com `api_login_required`.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request, session
from werkzeug.wrappers import Response

from app.api import api_bp
from app.api_utils import json_error
from app.models import Talent
from app.talent_portal import portal_ops


def current_talent() -> Talent | None:
    """Talento da sessão atual, ou `None` se não autenticado."""
    tid = session.get("talent_id")
    if not tid:
        return None
    return Talent.query.get(tid)


def portal_api_login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Exige sessão de talento válida, respondendo 401 JSON (mesmo padrão de `api_login_required`)."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_talent() is None:
            return json_error("Não autenticado", 401)
        return view(*args, **kwargs)

    return wrapped


def _talent_to_dict(talent: Talent) -> dict:
    return {
        "id": talent.id,
        "full_name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "photo_face_url": talent.photo_face_path,
        "photo_full_url": talent.photo_full_path,
    }


@api_bp.route("/portal/auth/login", methods=["POST"])
def api_portal_login() -> Any:
    data = request.get_json(silent=True) or {}
    login_value = data.get("login", "")
    password = data.get("password", "")

    talent = portal_ops.find_talent_by_login(login_value)
    if not talent or not talent.check_password(password):
        return json_error("CPF/e-mail ou senha incorretos.", 401)

    session.clear()
    session["talent_id"] = talent.id
    session.permanent = True

    body = _talent_to_dict(talent)
    body["must_redirect_to_classic"] = portal_ops.needs_classic_portal_flow(talent)
    return jsonify(body)


@api_bp.route("/portal/auth/logout", methods=["POST"])
def api_portal_logout() -> tuple[Response, int]:
    session.pop("talent_id", None)
    return "", 204


@api_bp.route("/portal/auth/me")
def api_portal_me() -> Any:
    talent = current_talent()
    if talent is None:
        return json_error("Não autenticado", 401)
    return jsonify(_talent_to_dict(talent))
