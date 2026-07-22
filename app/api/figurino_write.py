"""Endpoints de ESCRITA de Figurino (feature 154).

Reusa o núcleo em `app/figurino/figurino_ops.py`. Gate: FIGURINO/SUPERADMIN — paridade com
`_can_edit_figurino()`. Sem upload de foto nesta fatia.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import FigurinoSheet, db


def _can_edit_figurino() -> bool:
    return any(r.name in (RoleName.SUPERADMIN, RoleName.FIGURINO) for r in current_user.roles)


@api_bp.route("/figurino", methods=["POST"])
@api_login_required
def api_figurino_create() -> Any:
    """Cria uma ficha de figurino sem foto (feature 154)."""
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import create_sheet

    body = request.get_json(silent=True) or {}
    sheet = create_sheet(
        character_name=body.get("character_name", ""),
        pieces=body.get("pieces"),
        notes=body.get("notes"),
    )
    if sheet is None:
        return json_error(
            "Nome do personagem é obrigatório.", 400, {"character_name": "Obrigatório"}
        )

    from app.utils import audit

    audit("create", "figurino", None, sheet.character_name, "Ficha de figurino criada (API)")
    db.session.commit()
    return jsonify(
        {
            "id": sheet.id,
            "character_name": sheet.character_name,
            "pieces": sheet.pieces_list,
            "notes": sheet.notes,
            "photo_url": sheet.photo_url,
        }
    ), 201


@api_bp.route("/figurino/<int:sheet_id>", methods=["PATCH"])
@api_login_required
def api_figurino_edit(sheet_id: int) -> Any:
    """Edita nome/peças/notas de uma ficha existente (feature 154)."""
    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return json_error("Ficha não encontrada", 404)
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import edit_sheet

    body = request.get_json(silent=True) or {}
    ok = edit_sheet(
        sheet,
        character_name=body.get("character_name", ""),
        pieces=body.get("pieces"),
        notes=body.get("notes"),
    )
    if not ok:
        return json_error(
            "Nome do personagem é obrigatório.", 400, {"character_name": "Obrigatório"}
        )

    from app.utils import audit

    audit("edit", "figurino", sheet.id, sheet.character_name, "Ficha de figurino editada (API)")
    db.session.commit()
    return jsonify(
        {
            "id": sheet.id,
            "character_name": sheet.character_name,
            "pieces": sheet.pieces_list,
            "notes": sheet.notes,
            "photo_url": sheet.photo_url,
        }
    )


@api_bp.route("/figurino/<int:sheet_id>", methods=["DELETE"])
@api_login_required
def api_figurino_delete(sheet_id: int) -> Any:
    """Exclui uma ficha, desvinculando cargos de evento que apontavam para ela (feature 154)."""
    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return json_error("Ficha não encontrada", 404)
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import delete_sheet
    from app.utils import audit

    audit("delete", "figurino", sheet.id, sheet.character_name, "Ficha de figurino removida (API)")
    delete_sheet(sheet)
    db.session.commit()
    return jsonify({"ok": True})


def _sheet_json(sheet: FigurinoSheet) -> dict:
    return {
        "id": sheet.id,
        "character_name": sheet.character_name,
        "pieces": sheet.pieces_list,
        "notes": sheet.notes,
        "photo_url": sheet.photo_url,
    }


@api_bp.route("/figurino/<int:sheet_id>/photo", methods=["POST"])
@api_login_required
def api_figurino_upload_photo(sheet_id: int) -> Any:
    """Envia/substitui a foto de uma ficha de figurino (feature 155)."""
    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return json_error("Ficha não encontrada", 404)
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import save_figurino_photo

    error = save_figurino_photo(sheet, file_storage=request.files.get("photo"))
    if error:
        return json_error(error, 400, {"photo": error})

    from app.utils import audit

    audit("edit", "figurino", sheet.id, sheet.character_name, "Foto enviada (API)")
    db.session.commit()
    return jsonify(_sheet_json(sheet))


@api_bp.route("/figurino/<int:sheet_id>/photo", methods=["DELETE"])
@api_login_required
def api_figurino_remove_photo(sheet_id: int) -> Any:
    """Remove a foto de uma ficha de figurino (feature 155). No-op seguro se já vazia."""
    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return json_error("Ficha não encontrada", 404)
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import remove_figurino_photo
    from app.utils import audit

    remove_figurino_photo(sheet)
    audit("edit", "figurino", sheet.id, sheet.character_name, "Foto removida (API)")
    db.session.commit()
    return jsonify(_sheet_json(sheet))


@api_bp.route("/figurino/<int:sheet_id>/photo/rotate", methods=["POST"])
@api_login_required
def api_figurino_rotate_photo(sheet_id: int) -> Any:
    """Gira 90° a foto de uma ficha de figurino (feature 155)."""
    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return json_error("Ficha não encontrada", 404)
    if not _can_edit_figurino():
        return json_error("Sem permissão", 403)

    from app.figurino.figurino_ops import rotate_figurino_photo

    body = request.get_json(silent=True) or {}
    error = rotate_figurino_photo(sheet, direction=body.get("direction", "cw"))
    if error:
        return json_error(error, 400)

    db.session.commit()
    return jsonify(_sheet_json(sheet))
