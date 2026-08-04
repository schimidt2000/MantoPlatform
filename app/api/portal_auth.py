"""Endpoints de autenticação do Portal do Artista (feature 176).

Sessão própria do talento — reaproveita a MESMA chave de sessão (`talent_id`) já usada por
`app/talent_portal/routes.py` (Jinja legado), para que um talento autenticado numa versão
continue autenticado na outra (pesquisa em `research.md` §1). Auth por decorator (só verifica
sessão, não papel — Talent não tem RBAC), paridade de propósito com `api_login_required`.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request, session, url_for
from werkzeug.wrappers import Response

from app import limiter
from app.api import api_bp
from app.api_utils import json_error
from app.email_service import send_async, send_password_reset_email, send_welcome_email
from app.models import Talent
from app.talent_portal import portal_account_ops, portal_ops
from app.talent_portal.portal_account_ops import PortalAccountError


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
    """Identidade + etapas de conta pendentes — o React roteia o onboarding a partir daqui."""
    return {
        "id": talent.id,
        "full_name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "photo_face_url": talent.photo_face_path,
        "photo_full_url": talent.photo_full_path,
        "must_change_password": bool(talent.must_change_password),
        "terms_accepted": talent.terms_accepted_at is not None,
        "pending_steps": portal_account_ops.pending_account_steps(talent),
    }


def _account_error(exc: PortalAccountError, status: int = 400) -> tuple[Response, int]:
    """Traduz um `PortalAccountError` no envelope de erro padrão da API."""
    fields = {exc.field: exc.message} if exc.field else None
    return json_error(exc.message, status, fields=fields)


def _reset_url(token: str) -> str:
    """URL absoluta da tela de redefinição de senha enviada por e-mail.

    Prefere o portal React (`PORTAL_URL`, mesma base já usada pelos demais e-mails do portal);
    sem essa variável configurada, cai na rota Jinja legada — que continua funcionando, para o
    link não quebrar em ambientes onde o front novo ainda não foi publicado.
    """
    from flask import current_app

    base = (current_app.config.get("PORTAL_URL") or "").rstrip("/")
    if base:
        return f"{base}/reset-password/{token}"
    return url_for("portal.reset_password", token=token, _external=True)


@api_bp.route("/portal/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
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

    # `must_redirect_to_classic` (fatia 176) foi removido: troca de senha e aceite de termos são
    # telas React desde a 191 (`pending_steps`), e o portal Jinja deixou de ser destino de login —
    # o talento vai sempre para `/portal/*` do bundle React.
    return jsonify(_talent_to_dict(talent))


# ── Fluxos de conta (feature 191) ──────────────────────────────────────────────


@api_bp.route("/portal/auth/first-access", methods=["POST"])
@limiter.limit("5 per minute")
def api_portal_first_access() -> Any:
    """Gera senha temporária e envia o e-mail de boas-vindas para quem ainda não tem senha."""
    data = request.get_json(silent=True) or {}
    try:
        result = portal_account_ops.start_first_access(
            data.get("login", ""),
            lambda talent, temp_password: send_async(send_welcome_email, talent, temp_password),
        )
    except PortalAccountError as exc:
        return _account_error(exc)
    return jsonify({"email_hint": result.email_hint})


@api_bp.route("/portal/auth/forgot-password", methods=["POST"])
@limiter.limit("5 per minute")
def api_portal_forgot_password() -> Any:
    """Dispara o e-mail de redefinição. Responde sempre 200 — nunca revela se a conta existe."""
    data = request.get_json(silent=True) or {}
    portal_account_ops.request_password_reset(
        data.get("login", ""),
        data.get("email", ""),
        lambda talent, reset_url: send_async(send_password_reset_email, talent, reset_url),
        _reset_url,
    )
    return jsonify(
        {"message": "Se os dados conferem, enviamos um link de redefinição para o seu e-mail."}
    )


@api_bp.route("/portal/auth/reset-password/<token>")
def api_portal_check_reset_token(token: str) -> Any:
    """Diz se um token de redefinição ainda é válido, para a tela decidir o que mostrar."""
    talent = portal_account_ops.find_talent_by_reset_token(token)
    return jsonify({"valid": talent is not None})


@api_bp.route("/portal/auth/reset-password", methods=["POST"])
@limiter.limit("10 per minute")
def api_portal_reset_password() -> Any:
    """Redefine a senha a partir de um token válido recebido por e-mail."""
    data = request.get_json(silent=True) or {}
    try:
        portal_account_ops.reset_password_with_token(
            data.get("token", ""),
            data.get("new_password", ""),
            data.get("confirm_password", ""),
        )
    except PortalAccountError as exc:
        return _account_error(exc)
    return jsonify({"message": "Senha redefinida com sucesso. Faça login."})


@api_bp.route("/portal/auth/change-password", methods=["POST"])
@portal_api_login_required
def api_portal_change_password() -> Any:
    """Troca a senha do talento logado (usado no primeiro acesso e por escolha própria)."""
    data = request.get_json(silent=True) or {}
    talent = current_talent()
    try:
        portal_account_ops.change_password(
            talent, data.get("new_password", ""), data.get("confirm_password", "")
        )
    except PortalAccountError as exc:
        return _account_error(exc)
    return jsonify(_talent_to_dict(talent))


@api_bp.route("/portal/auth/accept-terms", methods=["POST"])
@portal_api_login_required
def api_portal_accept_terms() -> Any:
    """Registra o aceite dos termos de uso do talento logado."""
    talent = portal_account_ops.accept_terms(current_talent())
    return jsonify(_talent_to_dict(talent))


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
