"""Núcleo de Figurino como fonte única de lógica (feature 154).

Mesmo padrão de `casting_ops.py`/`event_ops.py`/`observation_ops.py`: cada função recebe
parâmetros explícitos (sem `request.form`, `flash` ou `current_user`), para ser reusada pelos
dois adaptadores finos — o handler Jinja (`app/figurino/routes.py`) e os endpoints JSON
(`app/api/figurino_read.py`/`app/api/figurino_write.py`). Upload/rotação/remoção de foto
(feature 155) recebem o `FileStorage`/direção já extraídos pelo wrapper.
"""

import json
import logging

from app.models import EventRole, FigurinoMissingDismissal, FigurinoSheet

logger = logging.getLogger(__name__)


def list_sheets() -> dict:
    """Lista as fichas de figurino + personagens já usados em eventos sem ficha correspondente
    (feature 154; cobertura por `figurino_sheet_id` e descarte de alertas, feature 183).

    Um cargo de evento (`EventRole`) é considerado "coberto" quando já aponta para uma ficha
    (`figurino_sheet_id`) OU quando seu nome normalizado bate com alguma ficha cadastrada. Um
    personagem sem cobertura só aparece em `chars_without_sheet` se ainda tiver algum
    `EventRole.id` fora de um descarte vigente (`FigurinoMissingDismissal`) — ver
    `dismiss_missing_character`/`associate_missing_character`.

    Não usa a mesma query de `figurinos()` (Jinja) — aquela view tem sua própria lógica inline,
    puramente por nome, mantida intacta (feature 183, FR-015).
    """
    from .drive_service import normalize_name

    sheets = FigurinoSheet.query.order_by(FigurinoSheet.character_name.asc()).all()
    sheet_norms = {s.character_name_norm for s in sheets if s.character_name_norm}

    roles = (
        EventRole.query.with_entities(
            EventRole.id, EventRole.character_name, EventRole.figurino_sheet_id
        )
        .filter(EventRole.character_name.isnot(None))
        .all()
    )

    missing_by_norm: dict[str, dict] = {}
    for role_id, char_name, sheet_id in roles:
        if not char_name or sheet_id is not None:
            continue
        norm = normalize_name(char_name)
        if norm in sheet_norms:
            continue
        entry = missing_by_norm.setdefault(norm, {"character_name": char_name, "role_ids": []})
        entry["role_ids"].append(role_id)

    dismissals = {
        d.character_name_norm: set(json.loads(d.event_role_ids))
        for d in FigurinoMissingDismissal.query.all()
    }

    chars_without_sheet = []
    for norm, entry in missing_by_norm.items():
        dismissed_ids = dismissals.get(norm)
        if dismissed_ids is not None and set(entry["role_ids"]).issubset(dismissed_ids):
            continue
        chars_without_sheet.append({"character_name": entry["character_name"], "character_name_norm": norm})
    chars_without_sheet.sort(key=lambda c: c["character_name"])

    # Manutenções abertas por ficha (feature 225b): é o que faz um defeito relatado numa festa
    # chegar em quem vai separar o figurino da próxima. Uma consulta só para todas as fichas.
    from app.figurino.producao_ops import alertas_por_ficha

    alertas = alertas_por_ficha()

    return {
        "items": [
            {
                "id": s.id,
                "character_name": s.character_name,
                "pieces": s.pieces_list,
                "tags": s.tags_list,
                "notes": s.notes,
                "photo_url": s.photo_url,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "manutencao": alertas.get(s.id),
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


def _clean_tags(tags: list[str] | None) -> list[str]:
    """Normaliza tags: `strip()`, descarta vazias, dedup case-insensitive preservando a primeira
    grafia usada (feature 183)."""
    seen: set[str] = set()
    result = []
    for tag in tags or []:
        name = (tag or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    return result


def create_sheet(
    *,
    character_name: str,
    pieces: list[dict] | None,
    notes: str | None,
    tags: list[str] | None = None,
) -> FigurinoSheet | None:
    """Cria uma ficha de figurino sem foto (upload fora desta fatia). Paridade com
    `new_sheet` — recusa (devolve None) se `character_name` vier vazio."""
    from .. import db
    from .drive_service import normalize_name

    character_name = (character_name or "").strip()
    if not character_name:
        return None

    clean_pieces = _clean_pieces(pieces)
    clean_tags = _clean_tags(tags)
    sheet = FigurinoSheet(
        character_name=character_name,
        character_name_norm=normalize_name(character_name),
        pieces=json.dumps(clean_pieces, ensure_ascii=False) if clean_pieces else None,
        tags=json.dumps(clean_tags, ensure_ascii=False) if clean_tags else None,
        notes=(notes or "").strip() or None,
    )
    db.session.add(sheet)
    return sheet


def edit_sheet(
    sheet: FigurinoSheet,
    *,
    character_name: str,
    pieces: list[dict] | None,
    notes: str | None,
    tags: list[str] | None = None,
) -> bool:
    """Edita nome/peças/notas/tags de uma ficha existente (sem tocar na foto). Paridade com
    `edit_sheet` — recusa (devolve False) se `character_name` vier vazio."""
    from datetime import datetime

    from .drive_service import normalize_name

    character_name = (character_name or "").strip()
    if not character_name:
        return False

    clean_pieces = _clean_pieces(pieces)
    clean_tags = _clean_tags(tags)
    sheet.character_name = character_name
    sheet.character_name_norm = normalize_name(character_name)
    sheet.pieces = json.dumps(clean_pieces, ensure_ascii=False) if clean_pieces else None
    sheet.tags = json.dumps(clean_tags, ensure_ascii=False) if clean_tags else None
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


def _pending_role_ids_for_norm(character_name_norm: str) -> list[int]:
    """IDs de `EventRole` atualmente sem ficha (`figurino_sheet_id` nulo) cujo nome normalizado
    bate com `character_name_norm` (feature 183)."""
    from .drive_service import normalize_name

    roles = (
        EventRole.query.with_entities(EventRole.id, EventRole.character_name)
        .filter(EventRole.figurino_sheet_id.is_(None))
        .filter(EventRole.character_name.isnot(None))
        .all()
    )
    return [role_id for role_id, name in roles if normalize_name(name) == character_name_norm]


def dismiss_missing_character(character_name_norm: str, *, dismissed_by: int | None) -> bool:
    """Descarta o alerta de "personagem sem ficha" para as ocorrências atuais daquele nome
    (feature 183). Um `EventRole` novo criado depois do descarte faz o personagem reaparecer.

    Returns:
        `False` se não houver nenhum cargo pendente para esse nome (nada a descartar).
    """
    from datetime import datetime

    from .. import db

    role_ids = _pending_role_ids_for_norm(character_name_norm)
    if not role_ids:
        return False

    existing = FigurinoMissingDismissal.query.filter_by(
        character_name_norm=character_name_norm
    ).first()
    if existing:
        merged = sorted(set(json.loads(existing.event_role_ids)) | set(role_ids))
        existing.event_role_ids = json.dumps(merged)
        existing.dismissed_at = datetime.utcnow()
        existing.dismissed_by = dismissed_by
    else:
        db.session.add(
            FigurinoMissingDismissal(
                character_name_norm=character_name_norm,
                event_role_ids=json.dumps(role_ids),
                dismissed_by=dismissed_by,
            )
        )
    return True


def associate_missing_character(character_name_norm: str, *, sheet_id: int) -> int:
    """Vincula todos os cargos de evento pendentes daquele personagem à ficha escolhida
    (feature 183) — seta `EventRole.figurino_sheet_id`.

    Returns:
        Quantos cargos foram atualizados (`0` se a ficha não existir ou não houver pendentes).
    """
    from .. import db
    from .drive_service import normalize_name

    sheet = FigurinoSheet.query.get(sheet_id)
    if sheet is None:
        return 0

    roles = (
        EventRole.query.filter(EventRole.figurino_sheet_id.is_(None))
        .filter(EventRole.character_name.isnot(None))
        .all()
    )
    updated = 0
    for role in roles:
        if normalize_name(role.character_name) == character_name_norm:
            role.figurino_sheet_id = sheet_id
            updated += 1
    if updated:
        db.session.flush()
    return updated


_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def save_figurino_photo(sheet: FigurinoSheet, *, file_storage) -> str | None:
    """Salva/substitui a foto de uma ficha de figurino (feature 155). Paridade com o bloco de
    upload já existente em `new_sheet`/`edit_sheet` — apaga a foto anterior antes de salvar.

    Returns:
        Mensagem de erro amigável, ou `None` em caso de sucesso.
    """
    import os
    from datetime import datetime

    from app.storage import delete_file, save_file

    if file_storage is None or not file_storage.filename:
        return "Nenhum arquivo selecionado."
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in _IMAGE_EXTS:
        return "Use JPG, PNG ou WEBP."

    if sheet.photo_filename:
        delete_file(sheet.photo_filename)
    sheet.photo_filename = save_file(file_storage, "figurino_photos")
    sheet.updated_at = datetime.utcnow()
    return None


def remove_figurino_photo(sheet: FigurinoSheet) -> None:
    """Remove a foto de uma ficha de figurino (ação nova, feature 155). No-op seguro se vazia."""
    from datetime import datetime

    from app.storage import delete_file

    if sheet.photo_filename:
        delete_file(sheet.photo_filename)
        sheet.photo_filename = None
        sheet.updated_at = datetime.utcnow()


def rotate_figurino_photo(sheet: FigurinoSheet, *, direction: str) -> str | None:
    """Gira 90° a foto de uma ficha de figurino. Paridade exata com `rotate_photo` — só
    funciona para foto local (`/uploads/...`), mesma limitação de hoje.

    Returns:
        Mensagem de erro amigável, ou `None` em caso de sucesso.
    """
    import os
    from datetime import datetime

    from flask import current_app

    if not sheet.photo_filename:
        return "Sem foto para girar."
    photo_url = sheet.photo_filename
    if not photo_url.startswith("/uploads/"):
        return "Formato de foto não suportado para rotação."

    rel_path = photo_url[len("/uploads/") :]
    abs_path = os.path.join(current_app.config["UPLOAD_FOLDER"], rel_path)

    try:
        from PIL import Image

        img = Image.open(abs_path)
        degrees = -90 if direction == "cw" else 90
        img = img.rotate(degrees, expand=True)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(abs_path, format="JPEG", quality=92, subsampling=0)
        sheet.updated_at = datetime.utcnow()
    except Exception as exc:  # noqa: BLE001 — falha ao girar não pode quebrar a requisição
        logger.warning("falha ao girar foto da ficha de figurino %s: %s", sheet.id, exc)
        return f"Erro ao girar foto: {exc}"
    return None
