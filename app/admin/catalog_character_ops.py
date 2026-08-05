"""Núcleo de negócio de Personagens filhos de um Tema do catálogo (feature 185).

Funções puras (sem `request`/`render_template`/`flash`), reusadas pelos endpoints de API em
`app/api/admin_catalogo_write.py` — fonte única, sem duplicar regra de negócio (Princípio I).
Reaproveita `CatalogValidationError` de `app.admin.catalog_ops` (mesmo contrato de erro já usado
pelo restante do catálogo) e `_slugify` de `app.catalogo.importer`.
"""

from __future__ import annotations

import os

from app import db
from app.admin.catalog_ops import CatalogValidationError
from app.catalogo.importer import _rewrite_public_url, _slugify
from app.catalogo.media import classify_video_url
from app.models import CatalogCharacter, CatalogItem, CatalogItemImage
from app.storage import copy_file, delete_file, save_file
from app.utils import audit

_ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def unique_character_slug(tema_slug: str, name: str) -> str:
    """Gera um slug único e global para um `CatalogCharacter`, prefixado pelo slug do Tema pai."""
    base = f"{tema_slug}-{_slugify(name)}"
    slug = base
    n = 2
    while CatalogCharacter.query.filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _validate_video_url(video_url: str | None) -> None:
    if video_url and classify_video_url(video_url) is None:
        raise CatalogValidationError(
            "video_url", "URL de vídeo não reconhecida (use Google Drive, MP4 ou Vimeo)."
        )


def _validate_photo_extension(photo_file) -> None:
    if not photo_file or not photo_file.filename:
        return
    ext = os.path.splitext(photo_file.filename)[1].lower()
    if ext not in _ALLOWED_PHOTO_EXTENSIONS:
        raise CatalogValidationError(
            "photo", f"Arquivo não suportado (use JPG, PNG ou WebP): {photo_file.filename}"
        )


def create_character(
    item: CatalogItem,
    *,
    name: str,
    video_url: str | None,
    figurino_sheet_id: int | None,
    photo_file,
) -> CatalogCharacter:
    """Cria um novo Personagem filho do Tema `item`."""
    clean_name = (name or "").strip()
    if not clean_name:
        raise CatalogValidationError("name", "Nome do personagem é obrigatório.")
    _validate_video_url(video_url)
    _validate_photo_extension(photo_file)

    photo_url = None
    if photo_file and photo_file.filename:
        # Mesma subpasta das fotos do Tema — a rota pública `/catalogo/midia/<arquivo>`
        # (app/catalogo/routes.py) só serve de "catalog_photos", nunca de `/uploads` geral.
        photo_url = _rewrite_public_url(save_file(photo_file, "catalog_photos"))

    next_position = len(item.characters)
    character = CatalogCharacter(
        catalog_item_id=item.id,
        name=clean_name,
        slug=unique_character_slug(item.slug, clean_name),
        photo_url=photo_url,
        video_url=(video_url or "").strip() or None,
        figurino_sheet_id=figurino_sheet_id,
        position=next_position,
    )
    db.session.add(character)
    db.session.flush()
    audit(
        "create", "CatalogCharacter", character.id, clean_name,
        f"Personagem criado em '{item.name}'",
    )
    db.session.commit()
    return character


def update_character(
    character: CatalogCharacter,
    *,
    name: str | None = None,
    video_url: str | None = None,
    figurino_sheet_id: int | None = ...,
    position: int | None = None,
    is_active: bool | None = None,
    photo_file=None,
    remove_photo: bool = False,
) -> CatalogCharacter:
    """Edita um Personagem existente. Só aplica os campos explicitamente informados.

    `figurino_sheet_id` usa `...` (Ellipsis) como sentinela de "não alterar", pois `None` é um
    valor válido (desvincular a ficha).
    """
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise CatalogValidationError("name", "Nome do personagem é obrigatório.")
        character.name = clean_name
    if video_url is not None:
        _validate_video_url(video_url)
        character.video_url = video_url.strip() or None
    if figurino_sheet_id is not ...:
        character.figurino_sheet_id = figurino_sheet_id
    if position is not None:
        character.position = position
    if is_active is not None:
        character.is_active = is_active

    _validate_photo_extension(photo_file)
    if remove_photo and character.photo_url:
        delete_file(character.photo_url)
        character.photo_url = None
    if photo_file and photo_file.filename:
        if character.photo_url:
            delete_file(character.photo_url)
        character.photo_url = _rewrite_public_url(save_file(photo_file, "catalog_photos"))

    audit("edit", "CatalogCharacter", character.id, character.name, "Personagem editado")
    db.session.commit()
    return character


def adopt_gallery_photo(character: CatalogCharacter, image: CatalogItemImage) -> CatalogCharacter:
    """Adota uma foto da galeria do Tema como foto do Personagem (drag-and-drop do admin).

    O arquivo é COPIADO (`storage.copy_file`), nunca referenciado: os fluxos de remoção
    (`update_character`, `delete_character`, `catalog_ops.apply_photos`) chamam `delete_file`
    sem saber de compartilhamento — em S3, uma URL compartilhada deixaria o outro lado com
    imagem quebrada. A foto continua na galeria.
    """
    if image.item_id != character.catalog_item_id:
        raise CatalogValidationError(
            "image_id", "A foto precisa pertencer à galeria do mesmo Tema do personagem."
        )

    new_url = copy_file(image.url, "catalog_photos")
    if not new_url:
        raise CatalogValidationError(
            "image_id", "Não foi possível copiar a foto da galeria. Tente novamente."
        )

    if character.photo_url:
        delete_file(character.photo_url)
    character.photo_url = _rewrite_public_url(new_url)

    audit(
        "edit", "CatalogCharacter", character.id, character.name,
        "Foto adotada da galeria do Tema",
    )
    db.session.commit()
    return character


def delete_character(character: CatalogCharacter) -> None:
    """Exclui definitivamente um Personagem, removendo sua foto do storage."""
    name = character.name
    character_id = character.id
    if character.photo_url:
        delete_file(character.photo_url)
    db.session.delete(character)
    audit("delete", "CatalogCharacter", character_id, name, "Personagem excluído")
    db.session.commit()


def move_characters(character_ids: list[int], target_item: CatalogItem) -> int:
    """Realoca em massa uma lista de Personagens para serem filhos de `target_item` (feature 186).

    Reatribui `catalog_item_id` numa única transação — ou tudo aplica, ou nada aplica. A posição
    de cada Personagem movido é recalculada para o final da lista de filhos de `target_item`, na
    ordem em que os `character_ids` foram informados.

    Args:
        character_ids: ids dos `CatalogCharacter` a mover.
        target_item: Tema de destino (já deve estar carregado/validado pelo chamador).

    Returns:
        Quantidade de Personagens efetivamente movidos.

    Raises:
        CatalogValidationError: `character_ids` vazio ou contém um id inexistente.
    """
    if not character_ids:
        raise CatalogValidationError("character_ids", "Selecione ao menos um personagem.")

    characters = CatalogCharacter.query.filter(CatalogCharacter.id.in_(character_ids)).all()
    if len(characters) != len(set(character_ids)):
        raise CatalogValidationError("character_ids", "Um ou mais personagens não foram encontrados.")

    next_position = len(target_item.characters)
    by_id = {c.id: c for c in characters}
    for offset, char_id in enumerate(character_ids):
        character = by_id[char_id]
        character.catalog_item_id = target_item.id
        character.position = next_position + offset
        audit(
            "edit", "CatalogCharacter", character.id, character.name,
            f"Personagem realocado para '{target_item.name}'",
        )
    db.session.commit()
    return len(characters)
