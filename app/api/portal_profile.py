"""Endpoints de Perfil, Fotos/Documentos e Portfólio do Portal do Artista (features 176 e 191).

Só orquestra e serializa — a validação de upload e a persistência moram em
`app/talent_portal/portal_ops.py` (reaproveitando `app/cadastro/cadastro_ops.py` para os
limites de extensão/tamanho, fonte única — Princípio I).

RBAC = "é o dono do recurso": toda operação age sobre o talento da sessão; nenhum endpoint
aceita um `talent_id` vindo do cliente.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.portal_auth import current_talent, portal_api_login_required
from app.api_utils import json_error
from app.talent_portal import portal_ops
from app.talent_portal.portal_ops import PortalProfileError, PortalUploadError

_ALLOWED_KINDS = {"face", "full"}


@api_bp.route("/portal/profile/photo", methods=["POST"])
@portal_api_login_required
def api_portal_upload_photo() -> Any:
    talent = current_talent()
    kind = request.form.get("kind", "")
    if kind not in _ALLOWED_KINDS:
        return json_error("Tipo de foto inválido.", 400, fields={"kind": "Use 'face' ou 'full'."})

    file = request.files.get("file")
    try:
        talent = portal_ops.update_photo(talent, kind, file)
    except portal_ops.PortalUploadError as exc:
        return json_error(exc.message, 400, fields={"file": exc.message})

    return jsonify(
        {"photo_face_url": talent.photo_face_path, "photo_full_url": talent.photo_full_path}
    )


@api_bp.route("/portal/profile/document", methods=["POST"])
@portal_api_login_required
def api_portal_upload_document() -> Any:
    talent = current_talent()
    file = request.files.get("file")
    try:
        talent = portal_ops.update_document(talent, file)
    except portal_ops.PortalUploadError as exc:
        return json_error(exc.message, 400, fields={"file": exc.message})

    return jsonify({"cnh_file_url": talent.cnh_file_path})


# ── Perfil e portfólio (feature 191) ───────────────────────────────────────────


@api_bp.route("/portal/profile")
@portal_api_login_required
def api_portal_get_profile() -> Any:
    """Perfil completo do talento logado, incluindo medidas corporais e portfólio."""
    return jsonify(portal_ops.get_profile(current_talent()))


@api_bp.route("/portal/profile", methods=["PATCH"])
@portal_api_login_required
def api_portal_update_profile() -> Any:
    """Atualiza os campos de perfil que o talento pode editar (semântica de PATCH parcial)."""
    talent = current_talent()
    data = request.get_json(silent=True) or {}
    try:
        talent = portal_ops.update_profile(talent, data)
    except PortalProfileError as exc:
        fields = {exc.field: exc.message} if exc.field else None
        return json_error(exc.message, 400, fields=fields)
    return jsonify(portal_ops.get_profile(talent))


@api_bp.route("/portal/profile/media/photo", methods=["POST"])
@portal_api_login_required
def api_portal_add_portfolio_photo() -> Any:
    """Adiciona uma foto de atuação ao portfólio (limite de 3)."""
    talent = current_talent()
    try:
        portal_ops.add_portfolio_photo(talent, request.files.get("file"), request.form.get("label"))
    except PortalUploadError as exc:
        return json_error(exc.message, 400, fields={"file": exc.message})
    return jsonify(portal_ops.get_profile(talent))


@api_bp.route("/portal/profile/media/link", methods=["POST"])
@portal_api_login_required
def api_portal_add_portfolio_link() -> Any:
    """Adiciona um link de portfólio (Vimeo, YouTube…)."""
    talent = current_talent()
    data = request.get_json(silent=True) or {}
    try:
        portal_ops.add_portfolio_link(talent, data.get("url", ""), data.get("label"))
    except PortalProfileError as exc:
        fields = {exc.field: exc.message} if exc.field else None
        return json_error(exc.message, 400, fields=fields)
    return jsonify(portal_ops.get_profile(talent))


@api_bp.route("/portal/profile/media/<int:media_id>", methods=["DELETE"])
@portal_api_login_required
def api_portal_delete_portfolio_item(media_id: int) -> Any:
    """Remove uma foto ou link do portfólio do talento logado."""
    talent = current_talent()
    if not portal_ops.delete_portfolio_item(talent, media_id):
        return json_error("Item não encontrado.", 404)
    return jsonify(portal_ops.get_profile(talent))
