"""Endpoints de ESCRITA do módulo de Impressões 3D (feature 200).

CRUD do Acervo (`/api/3d/acervo`, multipart — foto de preview + arquivo 3D) e gestão dos
presentes vinculados a um evento (`/api/events/<id>/3d-gifts`). Reusa, sem duplicar,
`app.impressoes3d.impressoes3d_ops`. Gate: `ARTISTA_3D` ou `SUPERADMIN`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.impressoes3d_read import require_3d_access
from app.api_utils import api_login_required, json_error
from app.constants import EVENT_TYPE_SHOW, RoleName
from app.impressoes3d import impressoes3d_ops as ops
from app.models import Acervo3DItem, CalendarEvent, Event3DGift


def _form_flag(field: str) -> bool | None:
    """Lê um booleano de `request.form`; `None` quando o campo não foi enviado."""
    if field not in request.form:
        return None
    return request.form.get(field, "").strip().lower() in ("1", "true")


def _model_files() -> list:
    """Arquivos 3D enviados no multipart (feature 201 — N por peça).

    Aceita `files` (múltiplos) e o `file` singular da feature 200, para nenhum cliente antigo
    quebrar ao enviar um arquivo só.
    """
    return request.files.getlist("files") + request.files.getlist("file")


def _remove_file_ids() -> set[int]:
    """Ids de arquivos 3D marcados para remoção (`remove_file_ids[]`)."""
    return {int(x) for x in request.form.getlist("remove_file_ids[]") if x.isdigit()}


# ── Acervo 3D ────────────────────────────────────────────────────────────────


@api_bp.route("/3d/acervo", methods=["POST"])
@api_login_required
def api_3d_acervo_create() -> Any:
    """Cadastra uma peça no Acervo 3D (multipart: `photo` + um ou mais `files`)."""
    denied = require_3d_access()
    if denied:
        return denied
    try:
        item = ops.create_acervo_item(
            name=request.form.get("name", ""),
            photo_file=request.files.get("photo"),
            model_files=_model_files(),
        )
    except ops.Impressao3DValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_acervo_item(item, 0)), 201


@api_bp.route("/3d/acervo/<int:item_id>", methods=["PATCH"])
@api_login_required
def api_3d_acervo_update(item_id: int) -> Any:
    """Edita uma peça do Acervo (nome, ativo/inativo, foto, e acrescenta/remove arquivos 3D)."""
    denied = require_3d_access()
    if denied:
        return denied
    item = Acervo3DItem.query.get(item_id)
    if item is None:
        return json_error("Peça do Acervo não encontrada", 404)
    try:
        ops.update_acervo_item(
            item,
            name=request.form.get("name") if "name" in request.form else None,
            is_active=_form_flag("is_active"),
            photo_file=request.files.get("photo"),
            model_files=_model_files(),
            remove_file_ids=_remove_file_ids(),
            # `...` = não alterar; string vazia = desabilitar NFC do item (feature 255).
            nfc_prefix=request.form["nfc_prefix"] if "nfc_prefix" in request.form else ...,
        )
    except ops.Impressao3DValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_acervo_item(item, Event3DGift.query.filter_by(item_id=item.id).count()))


@api_bp.route("/3d/acervo/<int:item_id>", methods=["DELETE"])
@api_login_required
def api_3d_acervo_delete(item_id: int) -> Any:
    """Exclui uma peça do Acervo.

    Por padrão é bloqueado enquanto houver evento vinculado — o caminho é inativar a peça.
    Com `?force=true` a exclusão acontece mesmo assim, **desvinculando de todos os eventos**:
    é irreversível e some com o presente da tela dos eventos e da Fila de Impressão, então
    exige SUPERADMIN (o Artista 3D continua só com o caminho seguro).
    """
    denied = require_3d_access()
    if denied:
        return denied
    item = Acervo3DItem.query.get(item_id)
    if item is None:
        return json_error("Peça do Acervo não encontrada", 404)

    force = request.args.get("force", "").strip().lower() in ("1", "true")
    if force and not any(r.name.upper() == RoleName.SUPERADMIN for r in current_user.roles):
        return json_error("Apenas o super admin pode excluir uma peça já usada em eventos", 403)

    try:
        ops.delete_acervo_item(item, force=force)
    except ops.Impressao3DValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return "", 204


# ── Presentes 3D de um evento ────────────────────────────────────────────────


def _load_gift(event_id: int, gift_id: int) -> Event3DGift | None:
    """Carrega o presente garantindo que ele pertence ao evento da URL."""
    return Event3DGift.query.filter_by(id=gift_id, event_id=event_id).first()


@api_bp.route("/events/<int:event_id>/3d-gifts", methods=["POST"])
@api_login_required
def api_event_3d_gift_create(event_id: int) -> Any:
    """Vincula uma peça do Acervo ao evento como Presente 3D (JSON)."""
    denied = require_3d_access()
    if denied:
        return denied
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if event.event_type != EVENT_TYPE_SHOW:
        return json_error("Presente 3D só pode ser vinculado a eventos do tipo SHOW", 400)

    body = request.get_json(silent=True) or {}
    try:
        gift = ops.add_event_gift(
            event,
            item_id=body.get("item_id"),
            quantity=body.get("quantity", 1),
            deadline_date=body.get("deadline_date"),
            notes=body.get("notes"),
            status=body.get("status"),
        )
    except ops.Impressao3DValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_gift(gift)), 201


@api_bp.route("/events/<int:event_id>/3d-gifts/<int:gift_id>", methods=["PATCH"])
@api_login_required
def api_event_3d_gift_update(event_id: int, gift_id: int) -> Any:
    """Edita um Presente 3D do evento — inclui a troca rápida de status na Fila (JSON)."""
    denied = require_3d_access()
    if denied:
        return denied
    gift = _load_gift(event_id, gift_id)
    if gift is None:
        return json_error("Presente 3D não encontrado", 404)

    body = request.get_json(silent=True) or {}
    try:
        ops.update_event_gift(
            gift,
            status=body.get("status"),
            quantity=body.get("quantity"),
            # `...` = "não alterar" (None é válido: limpa o prazo).
            deadline_date=body["deadline_date"] if "deadline_date" in body else ...,
            notes=body.get("notes"),
            item_id=body.get("item_id"),
        )
    except ops.Impressao3DValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_gift(gift))


@api_bp.route("/events/<int:event_id>/3d-gifts/<int:gift_id>", methods=["DELETE"])
@api_login_required
def api_event_3d_gift_delete(event_id: int, gift_id: int) -> Any:
    """Remove o vínculo de um Presente 3D com o evento."""
    denied = require_3d_access()
    if denied:
        return denied
    gift = _load_gift(event_id, gift_id)
    if gift is None:
        return json_error("Presente 3D não encontrado", 404)
    ops.delete_event_gift(gift)
    return "", 204


# ── Dispensa da pendência "show sem presente" (feature 202) ──────────────────


@api_bp.route("/events/<int:event_id>/3d-dismissal", methods=["POST"])
@api_login_required
def api_event_3d_dismiss(event_id: int) -> Any:
    """Marca o evento como "não leva presente 3D", tirando-o da lista de pendências."""
    denied = require_3d_access()
    if denied:
        return denied
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    if event.event_type != EVENT_TYPE_SHOW:
        return json_error("Só eventos do tipo SHOW geram pendência de presente 3D", 400)
    ops.dismiss_event(event, dismissed_by=current_user.id)
    return jsonify({"event_id": event.id, "dismissed": True})


@api_bp.route("/events/<int:event_id>/3d-dismissal", methods=["DELETE"])
@api_login_required
def api_event_3d_undismiss(event_id: int) -> Any:
    """Desfaz a dispensa, devolvendo o evento à lista de pendências."""
    denied = require_3d_access()
    if denied:
        return denied
    event = CalendarEvent.query.get(event_id)
    if event is None:
        return json_error("Evento não encontrado", 404)
    ops.undismiss_event(event)
    return "", 204
