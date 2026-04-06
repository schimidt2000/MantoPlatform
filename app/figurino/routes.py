import json
import os
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from app.models import FigurinoSheet, EventRole
from app.storage import save_file, delete_file
from .. import db

figurino_bp = Blueprint("figurino", __name__)

_ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _parse_pieces(form) -> list:
    """Parse piece_names[] + piece_qtys[] from form into [{"name", "qty"}] list."""
    names = form.getlist("piece_names[]")
    qtys  = form.getlist("piece_qtys[]")
    result = []
    for name, qty_str in zip(names, qtys):
        name = name.strip()
        if name:
            try:
                qty = max(1, int(qty_str or "1"))
            except ValueError:
                qty = 1
            result.append({"name": name, "qty": qty})
    return result


# ── Listing ────────────────────────────────────────────────────

@figurino_bp.route("/figurinos")
@login_required
def figurinos():
    from .drive_service import normalize_name

    sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sheet_norms = {s.character_name_norm for s in sheets if s.character_name_norm}

    all_chars = db.session.query(EventRole.character_name).distinct().all()
    chars_without_sheet = sorted(
        {c[0] for c in all_chars if c[0] and normalize_name(c[0]) not in sheet_norms}
    )

    return render_template(
        "figurinos.html",
        sheets=sheets,
        chars_without_sheet=chars_without_sheet,
    )


# ── Create ─────────────────────────────────────────────────────

@figurino_bp.route("/figurinos/new", methods=["GET", "POST"])
@login_required
def new_sheet():
    from .drive_service import normalize_name

    if request.method == "POST":
        character_name = request.form.get("character_name", "").strip()
        if not character_name:
            flash("Nome do personagem é obrigatório.")
            return render_template("figurino_form.html", sheet=None,
                                   pieces=_parse_pieces(request.form) or [{"name": "", "qty": 1}],
                                   title="Nova Ficha de Figurino")

        pieces = _parse_pieces(request.form)
        notes = request.form.get("notes", "").strip()

        photo_url = None
        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            ext = os.path.splitext(photo_file.filename)[1].lower()
            if ext in _ALLOWED_PHOTO_EXTENSIONS:
                photo_url = save_file(photo_file, "figurino_photos")

        sheet = FigurinoSheet(
            character_name=character_name,
            character_name_norm=normalize_name(character_name),
            photo_filename=photo_url,
            pieces=json.dumps(pieces, ensure_ascii=False) if pieces else None,
            notes=notes or None,
        )
        db.session.add(sheet)
        from app.utils import audit
        audit("create", "figurino", None, character_name, "Ficha de figurino criada")
        db.session.commit()
        flash(f'Ficha de "{character_name}" criada com sucesso!')
        return redirect(url_for("figurino.figurinos"))

    return render_template("figurino_form.html", sheet=None,
                           pieces=[{"name": "", "qty": 1}],
                           title="Nova Ficha de Figurino")


# ── Edit ───────────────────────────────────────────────────────

@figurino_bp.route("/figurinos/<int:sheet_id>/edit", methods=["GET", "POST"])
@login_required
def edit_sheet(sheet_id: int):
    from .drive_service import normalize_name

    sheet = FigurinoSheet.query.get_or_404(sheet_id)

    if request.method == "POST":
        character_name = request.form.get("character_name", "").strip()
        if not character_name:
            flash("Nome do personagem é obrigatório.")
            return render_template("figurino_form.html", sheet=sheet,
                                   pieces=sheet.pieces_list or [{"name": "", "qty": 1}],
                                   title=f"Editar — {sheet.character_name}")

        pieces = _parse_pieces(request.form)
        notes = request.form.get("notes", "").strip()

        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            ext = os.path.splitext(photo_file.filename)[1].lower()
            if ext in _ALLOWED_PHOTO_EXTENSIONS:
                delete_file(sheet.photo_filename)
                sheet.photo_filename = save_file(photo_file, "figurino_photos")

        sheet.character_name = character_name
        sheet.character_name_norm = normalize_name(character_name)
        sheet.pieces = json.dumps(pieces, ensure_ascii=False) if pieces else None
        sheet.notes = notes or None
        sheet.updated_at = datetime.utcnow()
        from app.utils import audit
        audit("edit", "figurino", sheet.id, character_name, "Ficha de figurino editada")
        db.session.commit()
        flash(f'Ficha de "{character_name}" atualizada!')
        return redirect(url_for("figurino.figurinos"))

    return render_template("figurino_form.html", sheet=sheet,
                           pieces=sheet.pieces_list or [{"name": "", "qty": 1}],
                           title=f"Editar — {sheet.character_name}")


# ── Print: single sheet ────────────────────────────────────────

@figurino_bp.route("/figurinos/<int:sheet_id>/print")
@login_required
def print_sheet(sheet_id: int):
    sheet = FigurinoSheet.query.get_or_404(sheet_id)
    items = [{"sheet": sheet, "pieces": sheet.pieces_list, "role": None, "talent": None}]
    return render_template("figurino_print.html", items=items, event=None,
                           title=f"Ficha: {sheet.character_name}")


# ── Print: all sheets for an event ────────────────────────────

@figurino_bp.route("/figurinos/print-event/<int:event_id>")
@login_required
def print_event_figurinos(event_id: int):
    from app.models import CalendarEvent
    from .drive_service import normalize_name

    event = CalendarEvent.query.get_or_404(event_id)

    items = []
    for role in event.roles:
        sheet = role.figurino_sheet
        if not sheet:
            norm = normalize_name(role.character_name)
            sheet = FigurinoSheet.query.filter_by(character_name_norm=norm).first()

        items.append({
            "role": role,
            "sheet": sheet,
            "pieces": sheet.pieces_list if sheet else [],
            "talent": role.talent,
        })

    return render_template("figurino_print.html", items=items, event=event,
                           title=f"Figurinos — {event.title}")


# ── Delete ─────────────────────────────────────────────────────

@figurino_bp.route("/figurinos/<int:sheet_id>/delete", methods=["POST"])
@login_required
def delete_sheet(sheet_id: int):
    sheet = FigurinoSheet.query.get_or_404(sheet_id)

    delete_file(sheet.photo_filename)

    from app.utils import audit
    audit("delete", "figurino", sheet.id, sheet.character_name, "Ficha de figurino removida")
    EventRole.query.filter_by(figurino_sheet_id=sheet_id).update({"figurino_sheet_id": None})
    db.session.delete(sheet)
    db.session.commit()
    flash("Ficha removida do catálogo.")
    return redirect(url_for("figurino.figurinos"))
