"""Endpoints de ESCRITA das Tags NFC (feature 255). Gate: `ARTISTA_3D` ou `SUPERADMIN`.

Só existem duas escritas — gerar lote avulso e editar os campos mutáveis (evento, situação,
observações). **Não há DELETE por contrato**: a tag física é eterna; a linha idem.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.impressoes3d_read import require_3d_access
from app.api.nfc_read import _serialize_admin_tag
from app.api_utils import api_login_required, json_error
from app.impressoes3d import nfc_ops
from app.models import NfcTag


@api_bp.route("/3d/nfc/lote", methods=["POST"])
@api_login_required
def api_3d_nfc_batch() -> Any:
    """Gera um lote de tags avulsas (estoque, sem evento) — JSON `{item_id, quantity}`."""
    denied = require_3d_access()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        created = nfc_ops.generate_batch(body.get("item_id"), body.get("quantity"))
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tags": [_serialize_admin_tag(t) for t in created]})


@api_bp.route("/3d/nfc/<int:tag_id>", methods=["PATCH"])
@api_login_required
def api_3d_nfc_update(tag_id: int) -> Any:
    """Edita uma tag: `event_id` (null desassocia), `is_active`, `notes` — campo ausente não altera."""
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)

    body = request.get_json(silent=True) or {}
    try:
        nfc_ops.update_tag(
            tag,
            # `...` = "não alterar" (None é válido: desassocia). `client_id` é a cliente
            # DIRETA — campanha/brinde sem show; independente do evento.
            event_id=body["event_id"] if "event_id" in body else ...,
            client_id=body["client_id"] if "client_id" in body else ...,
            is_active=body.get("is_active"),
            notes=body.get("notes"),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tag": _serialize_admin_tag(tag)})
