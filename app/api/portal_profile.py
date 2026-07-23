"""Endpoints de Fotos/Documentos do Portal do Artista (feature 176).

Só orquestra e serializa — a validação de upload e a persistência moram em
`app/talent_portal/portal_ops.py` (reaproveitando `app/cadastro/cadastro_ops.py` para os
limites de extensão/tamanho, fonte única — Princípio I).
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.portal_auth import current_talent, portal_api_login_required
from app.api_utils import json_error
from app.talent_portal import portal_ops

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
