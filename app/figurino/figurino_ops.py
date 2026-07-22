"""Núcleo de Figurino como fonte única de lógica (feature 154).

Mesmo padrão de `casting_ops.py`/`event_ops.py`/`observation_ops.py`: cada função recebe
parâmetros explícitos (sem `request.form`, `flash` ou `current_user`), para ser reusada pelos
dois adaptadores finos — o handler Jinja (`app/figurino/routes.py`) e os endpoints JSON
(`app/api/figurino_read.py`/`app/api/figurino_write.py`). Upload/rotação de foto ficam fora do
núcleo (adiados nesta fatia) — só o wrapper Jinja lida com arquivo.
"""

import json

from app.models import EventRole, FigurinoSheet


def list_sheets() -> dict:
    """Lista as fichas de figurino + personagens já usados em eventos sem ficha correspondente.

    Mesma lógica de `figurinos()` (Jinja).
    """
    from .. import db
    from .drive_service import normalize_name

    sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sheet_norms = {s.character_name_norm for s in sheets if s.character_name_norm}

    all_chars = db.session.query(EventRole.character_name).distinct().all()
    chars_without_sheet = sorted(
        {c[0] for c in all_chars if c[0] and normalize_name(c[0]) not in sheet_norms}
    )

    return {
        "items": [
            {
                "id": s.id,
                "character_name": s.character_name,
                "pieces": s.pieces_list,
                "notes": s.notes,
                "photo_url": s.photo_url,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sheets
        ],
        "chars_without_sheet": chars_without_sheet,
    }


def _clean_pieces(pieces: list[dict] | None) -> list[dict]:
    result = []
    for p in pieces or []:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        try:
            qty = max(1, int(p.get("qty") or 1))
        except (ValueError, TypeError):
            qty = 1
        result.append({"name": name, "qty": qty})
    return result


def create_sheet(
    *, character_name: str, pieces: list[dict] | None, notes: str | None
) -> FigurinoSheet | None:
    """Cria uma ficha de figurino sem foto (upload fora desta fatia). Paridade com
    `new_sheet` — recusa (devolve None) se `character_name` vier vazio."""
    from .. import db
    from .drive_service import normalize_name

    character_name = (character_name or "").strip()
    if not character_name:
        return None

    clean_pieces = _clean_pieces(pieces)
    sheet = FigurinoSheet(
        character_name=character_name,
        character_name_norm=normalize_name(character_name),
        pieces=json.dumps(clean_pieces, ensure_ascii=False) if clean_pieces else None,
        notes=(notes or "").strip() or None,
    )
    db.session.add(sheet)
    return sheet


def edit_sheet(
    sheet: FigurinoSheet, *, character_name: str, pieces: list[dict] | None, notes: str | None
) -> bool:
    """Edita nome/peças/notas de uma ficha existente (sem tocar na foto). Paridade com
    `edit_sheet` — recusa (devolve False) se `character_name` vier vazio."""
    from datetime import datetime

    from .drive_service import normalize_name

    character_name = (character_name or "").strip()
    if not character_name:
        return False

    clean_pieces = _clean_pieces(pieces)
    sheet.character_name = character_name
    sheet.character_name_norm = normalize_name(character_name)
    sheet.pieces = json.dumps(clean_pieces, ensure_ascii=False) if clean_pieces else None
    sheet.notes = (notes or "").strip() or None
    sheet.updated_at = datetime.utcnow()
    return True


def delete_sheet(sheet: FigurinoSheet) -> None:
    """Exclui uma ficha, desvinculando qualquer cargo de evento que apontava para ela e
    removendo o arquivo de foto já existente (se houver). Paridade com `delete_sheet`."""
    from app.storage import delete_file

    from .. import db

    delete_file(sheet.photo_filename)
    EventRole.query.filter_by(figurino_sheet_id=sheet.id).update({"figurino_sheet_id": None})
    db.session.delete(sheet)
