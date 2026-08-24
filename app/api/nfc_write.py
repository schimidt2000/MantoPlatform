"""Endpoints de ESCRITA das Tags NFC (feature 255) e das entregas anexadas a elas (feature 261).
Gate: `ARTISTA_3D` ou `SUPERADMIN`.

A tag em si só tem duas escritas — gerar lote avulso e editar os campos mutáveis (evento,
situação, observações). **Não há DELETE de tag por contrato**: a tag física é eterna; a linha
idem. As entregas (vídeo, e futuramente foto/link) SÃO removíveis — são conteúdo anexado, não a
tag.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api.impressoes3d_read import require_3d_access
from app.api.nfc_read import _serialize_admin_tag
from app.api_utils import api_login_required, json_error
from app.impressoes3d import nfc_ops
from app.models import NfcTag, NfcTagDelivery


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


@api_bp.route("/3d/nfc/<int:tag_id>/entregas", methods=["POST"])
@api_login_required
def api_3d_nfc_add_delivery(tag_id: int) -> Any:
    """Envia o vídeo da tag — multipart `file` + `kind` (só `"video"` por ora) + `title` opcional.

    Substitui a entrega de vídeo ativa da tag, se houver (1 vídeo ativo por tag por ora).
    """
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)

    file_obj = request.files.get("file")
    try:
        nfc_ops.add_delivery(
            tag,
            file_obj,
            kind=(request.form.get("kind") or "video").strip(),
            title=request.form.get("title"),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tag": _serialize_admin_tag(tag)})


@api_bp.route("/3d/nfc/<int:tag_id>/entregas/<int:delivery_id>", methods=["DELETE"])
@api_login_required
def api_3d_nfc_remove_delivery(tag_id: int, delivery_id: int) -> Any:
    """Remove uma entrega (linha + arquivo do disco). Confirmação fica a cargo da UI."""
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)
    delivery = NfcTagDelivery.query.filter_by(id=delivery_id, tag_id=tag_id).first()
    if delivery is None:
        return json_error("Entrega não encontrada", 404)

    nfc_ops.remove_delivery(delivery)
    return jsonify({"tag": _serialize_admin_tag(tag)})
