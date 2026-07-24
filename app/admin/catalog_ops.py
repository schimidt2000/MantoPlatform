"""Núcleo de negócio da gestão de catálogo (feature 169, US6 — Cauda Administrativa).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/admin/routes.py` quanto pelos endpoints de API (`app/api/admin_catalogo_read.py`,
`app/api/admin_catalogo_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

import json

from app import db
from app.catalogo.importer import _rewrite_public_url, _slugify
from app.catalogo.media import classify_video_url
from app.models import CatalogCategory, CatalogItem, CatalogItemImage
from app.storage import delete_file, save_file
from app.utils import audit

_ALLOWED_CATALOG_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class CatalogValidationError(Exception):
    """Erro de validação de negócio (nome/foto obrigatórios, extensão inválida)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def unique_catalog_slug(name: str) -> str:
    """Gera um slug único para um novo `CatalogItem` a partir do nome."""
    base = _slugify(name)
    slug = base
    n = 2
    while CatalogItem.query.filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def create_or_reuse_category(name: str) -> CatalogCategory:
    """Cria (ou reaproveita, por slug) uma categoria do catálogo."""
    clean_name = (name or "").strip()
    if not clean_name:
        raise CatalogValidationError("name", "Nome da categoria é obrigatório.")
    slug = _slugify(clean_name)
    category = CatalogCategory.query.filter_by(slug=slug).first()
    if not category:
        category = CatalogCategory(name=clean_name, slug=slug)
        db.session.add(category)
        db.session.commit()
    return category


def all_tags() -> list[str]:
    """Todas as tags distintas já usadas em qualquer produto do catálogo (dedupe por slug)."""
    seen: dict[str, str] = {}
    for (raw_tags,) in db.session.query(CatalogItem.tags).filter(CatalogItem.tags.isnot(None)):
        try:
            tags = json.loads(raw_tags) if raw_tags else []
        except (ValueError, TypeError):
            tags = []
        for tag in tags:
            key = _slugify(tag)
            if key and key not in seen:
                seen[key] = tag
    return sorted(seen.values(), key=str.lower)


def _normalize_tags(raw_tags: list[str], known_tags: list[str]) -> list[str]:
    """Reaproveita a grafia já existente de uma tag quando bate (case/acento-insensitive)."""
    by_key = {_slugify(t): t for t in known_tags}
    result: list[str] = []
    seen_keys: set[str] = set()
    for tag in raw_tags:
        key = _slugify(tag)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        result.append(by_key.get(key, tag))
    return result


def validate_photo_extensions(files) -> None:
    """Recusa arquivos fora de `_ALLOWED_CATALOG_PHOTO_EXTENSIONS` (feature 141)."""
    import os

    rejected = []
    for f in files.getlist("new_photos"):
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in _ALLOWED_CATALOG_PHOTO_EXTENSIONS:
            rejected.append(f.filename)
    if rejected:
        raise CatalogValidationError(
            "photos", "Arquivo(s) não suportado(s) (use JPG, PNG ou WebP): " + ", ".join(rejected)
        )


def apply_photos(item: CatalogItem, form, files) -> None:
    """Aplica remoções, reordenação, novos uploads e escolha de capa nas fotos de um item.

    Ordem: remove → aplica `photo_order` manual nas restantes → adiciona novas → resolve capa
    (explícita → primeira nova → primeira restante), sempre recolocando a capa em `position=0`.
    Chamar `validate_photo_extensions` antes desta função.
    """
    remove_ids = {int(x) for x in form.getlist("remove_photo_ids[]") if x.isdigit()}
    for img in list(item.images):
        if img.id in remove_ids:
            delete_file(img.url)
            db.session.delete(img)
    db.session.flush()

    remaining = (
        CatalogItemImage.query.filter_by(item_id=item.id)
        .order_by(CatalogItemImage.position.asc())
        .all()
    )

    order_raw = form.get("photo_order", "")
    if order_raw:
        order_ids = [int(x) for x in order_raw.split(",") if x.isdigit()]
        by_id = {im.id: im for im in remaining}
        ordered = [by_id[i] for i in order_ids if i in by_id]
        ordered += [im for im in remaining if im.id not in set(order_ids)]
        remaining = ordered

    next_pos = len(remaining)
    new_images = []
    for f in files.getlist("new_photos"):
        if not f or not f.filename:
            continue
        url = _rewrite_public_url(save_file(f, "catalog_photos"))
        img = CatalogItemImage(item_id=item.id, url=url, position=next_pos)
        db.session.add(img)
        new_images.append(img)
        next_pos += 1
    db.session.flush()

    cover_raw = form.get("cover_photo_id", "")
    cover_index_raw = form.get("new_photo_cover_index", "")
    cover = None
    if cover_raw.isdigit():
        cover = next((im for im in remaining if im.id == int(cover_raw)), None)
    if cover is None and cover_index_raw.isdigit():
        idx = int(cover_index_raw)
        if 0 <= idx < len(new_images):
            cover = new_images[idx]
    if cover is None and new_images:
        cover = new_images[0]
    if cover is not None:
        others = [im for im in (remaining + new_images) if im is not cover]
        cover.position = 0
        for i, im in enumerate(others, start=1):
            im.position = i


def validate_video_url(video_url: str | None) -> None:
    """Recusa uma `video_url` preenchida mas em formato não reconhecido (feature 185)."""
    if video_url and classify_video_url(video_url) is None:
        raise CatalogValidationError(
            "video_url", "URL de vídeo não reconhecida (use Google Drive, MP4 ou Vimeo)."
        )


def create_product(
    *,
    name: str,
    description: str | None,
    tags_raw: str,
    category_ids: list[int],
    form,
    files,
    video_url: str | None = None,
) -> CatalogItem:
    """Cria um novo produto do catálogo nativamente (feature 139)."""
    clean_name = (name or "").strip()
    new_photos = [f for f in files.getlist("new_photos") if f and f.filename]
    if not clean_name:
        raise CatalogValidationError("name", "Nome do produto é obrigatório.")
    if not new_photos:
        raise CatalogValidationError("photos", "Envie ao menos uma foto.")
    validate_photo_extensions(files)
    validate_video_url(video_url)

    item = CatalogItem(
        name=clean_name,
        slug=unique_catalog_slug(clean_name),
        short_description_html=(description or "").strip() or None,
        tags=None,
        video_url=(video_url or "").strip() or None,
    )
    tags = _normalize_tags([t.strip() for t in tags_raw.split(",") if t.strip()], all_tags())
    if tags:
        item.tags = json.dumps(tags, ensure_ascii=False)
    db.session.add(item)
    db.session.flush()

    if category_ids:
        item.categories = CatalogCategory.query.filter(CatalogCategory.id.in_(category_ids)).all()

    apply_photos(item, form, files)
    audit("create", "CatalogItem", item.id, item.name, "Produto do catálogo criado")
    db.session.commit()
    return item


def update_product(
    item: CatalogItem,
    *,
    name: str,
    description: str | None,
    tags_raw: str,
    category_ids: list[int],
    form,
    files,
    video_url: str | None = None,
) -> CatalogItem:
    """Edita um produto existente do catálogo (feature 139)."""
    clean_name = (name or "").strip()
    remove_ids = {int(x) for x in form.getlist("remove_photo_ids[]") if x.isdigit()}
    new_photos = [f for f in files.getlist("new_photos") if f and f.filename]
    remaining_count = sum(1 for img in item.images if img.id not in remove_ids)
    if not clean_name:
        raise CatalogValidationError("name", "Nome do produto é obrigatório.")
    if remaining_count + len(new_photos) == 0:
        raise CatalogValidationError("photos", "O produto precisa de ao menos uma foto.")
    validate_photo_extensions(files)
    validate_video_url(video_url)

    item.name = clean_name
    item.video_url = (video_url or "").strip() or None
    item.short_description_html = (description or "").strip() or None
    tags = _normalize_tags([t.strip() for t in tags_raw.split(",") if t.strip()], all_tags())
    item.tags = json.dumps(tags, ensure_ascii=False) if tags else None
    item.categories = (
        CatalogCategory.query.filter(CatalogCategory.id.in_(category_ids)).all()
        if category_ids
        else []
    )

    apply_photos(item, form, files)
    audit("edit", "CatalogItem", item.id, item.name, "Produto do catálogo editado")
    db.session.commit()
    return item


def toggle_active(item: CatalogItem) -> CatalogItem:
    """Ativa/inativa um produto do catálogo sem apagar os dados (feature 139)."""
    item.is_active = not item.is_active
    audit(
        "edit",
        "CatalogItem",
        item.id,
        item.name,
        f"Produto marcado como {'ativo' if item.is_active else 'inativo'}",
    )
    db.session.commit()
    return item


def delete_product(item: CatalogItem) -> None:
    """Exclui definitivamente um produto do catálogo, com suas fotos (feature 139)."""
    name = item.name
    for img in list(item.images):
        delete_file(img.url)
    audit("delete", "CatalogItem", item.id, name, "Produto do catálogo excluído definitivamente")
    db.session.delete(item)
    db.session.commit()
