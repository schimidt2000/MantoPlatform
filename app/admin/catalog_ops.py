"""Núcleo de negócio da gestão de catálogo (feature 169, US6 — Cauda Administrativa).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/admin/routes.py` quanto pelos endpoints de API (`app/api/admin_catalogo_read.py`,
`app/api/admin_catalogo_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

import json

import nh3

from app import db
from app.catalogo.importer import _rewrite_public_url, _slugify
from app.catalogo.media import classify_video_url
from app.models import CatalogCategory, CatalogItem, CatalogItemImage, FigurinoSheet
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


def _save_new_photos(item: CatalogItem, files) -> list[CatalogItemImage]:
    """Persiste os arquivos de `new_photos` na ordem em que vieram.

    A `position` sai zerada de propósito: quem decide a posição final de TODAS as fotos é
    `apply_photos`, depois de resolver a ordem manual e a capa.
    """
    new_images: list[CatalogItemImage] = []
    for f in files.getlist("new_photos"):
        if not f or not f.filename:
            continue
        url = _rewrite_public_url(save_file(f, "catalog_photos"))
        img = CatalogItemImage(item_id=item.id, url=url, position=0)
        db.session.add(img)
        new_images.append(img)
    db.session.flush()
    return new_images


def _resolve_photo_order(
    order_raw: str,
    remaining: list[CatalogItemImage],
    new_images: list[CatalogItemImage],
) -> tuple[list[CatalogItemImage], bool]:
    """Ordena as fotos finais a partir do `photo_order` enviado pelo cliente.

    Cada token de `photo_order` é o id de uma foto já salva **ou** `new:<i>`, onde `i` é o
    índice do arquivo dentro de `new_photos` — é isso que permite intercalar uma foto recém
    enviada entre as antigas (antes toda foto nova ia obrigatoriamente para o fim).

    Devolve `(ordenadas, ordem_completa)`. `ordem_completa` é falso quando o cliente não citou
    todas as fotos — caso do formulário Jinja legado, que só manda os ids das existentes; o que
    ficou de fora entra no fim, preservando a ordem atual.
    """
    by_token: dict[str, CatalogItemImage] = {str(im.id): im for im in remaining}
    by_token.update({f"new:{i}": im for i, im in enumerate(new_images)})

    ordered: list[CatalogItemImage] = []
    seen: set[int] = set()
    for token in (t.strip() for t in (order_raw or "").split(",")):
        img = by_token.get(token)
        if img is not None and img.id not in seen:
            seen.add(img.id)
            ordered.append(img)

    rest = [im for im in (remaining + new_images) if im.id not in seen]
    return ordered + rest, bool(ordered) and not rest


def _resolve_cover(
    form,
    remaining: list[CatalogItemImage],
    new_images: list[CatalogItemImage],
    *,
    allow_first_new_default: bool,
) -> CatalogItemImage | None:
    """Capa escolhida explicitamente (`cover_photo_id` → `new_photo_cover_index`).

    `allow_first_new_default` mantém a regra da feature 141 — a primeira foto nova vira capa
    quando ninguém escolheu — e só vale quando o cliente NÃO mandou uma ordem completa. Com
    ordem completa a capa é simplesmente a primeira da ordem, sem promoção surpresa.
    """
    cover_raw = form.get("cover_photo_id", "")
    if cover_raw.isdigit():
        cover = next((im for im in remaining if im.id == int(cover_raw)), None)
        if cover is not None:
            return cover
    cover_index_raw = form.get("new_photo_cover_index", "")
    if cover_index_raw.isdigit() and 0 <= int(cover_index_raw) < len(new_images):
        return new_images[int(cover_index_raw)]
    if allow_first_new_default and new_images:
        return new_images[0]
    return None


def apply_photos(item: CatalogItem, form, files) -> None:
    """Aplica remoções, reordenação, novos uploads e escolha de capa nas fotos de um item.

    Ordem: remove → sobe as novas → ordena tudo por `photo_order` → capa para a frente → grava
    `position`. Chamar `validate_photo_extensions` antes desta função.

    A `position` é SEMPRE regravada no fim. Antes ela só era tocada quando havia capa a
    definir, e uma edição que apenas reordenava (o form React, que não manda `cover_photo_id`)
    era aceita pela API e descartada em silêncio no banco.
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
    new_images = _save_new_photos(item, files)
    ordered, order_is_complete = _resolve_photo_order(
        form.get("photo_order", ""), remaining, new_images
    )
    cover = _resolve_cover(
        form, remaining, new_images, allow_first_new_default=not order_is_complete
    )
    if cover is not None:
        ordered = [cover] + [im for im in ordered if im.id != cover.id]
    for position, img in enumerate(ordered):
        img.position = position


# Vocabulário do editor rich-text do admin + do acervo importado do WooCommerce
# (`importer._clean_description` mantém <b>/<span>; browsers emitem <b>/<i> ou <strong>/<em>).
_DESCRIPTION_TAGS = {"b", "strong", "i", "em", "p", "br", "span", "div"}


def _sanitize_description(raw: str | None) -> str | None:
    """Sanitiza o HTML da descrição antes de persistir.

    Obrigatório: o valor é renderizado com `dangerouslySetInnerHTML` na vitrine pública
    (apps/public/ProductDetailPage.tsx) e com `|safe` no Jinja legado — sem isto, um script
    colado na descrição viraria XSS armazenado. Atributos são todos removidos (nenhum é
    necessário para negrito/itálico/parágrafo).

    Markup sem texto vira `None`: apagar tudo no contentEditable deixa `<br>`/`<div><br></div>`
    para trás, e persistir isso faria a vitrine renderizar um bloco vazio com margens.
    """
    clean = nh3.clean((raw or "").strip(), tags=_DESCRIPTION_TAGS, attributes={})
    text_only = nh3.clean(clean, tags=set(), attributes={})
    if not text_only.strip():
        return None
    return clean.strip() or None


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
        short_description_html=_sanitize_description(description),
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
    item.short_description_html = _sanitize_description(description)
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


def set_item_figurino(item: CatalogItem, sheet: FigurinoSheet | None) -> CatalogItem:
    """Define (ou remove) a ficha de figurino de um item AVULSO do catálogo (fase 1).

    Item avulso é a página de um personagem que se contrata sozinho — Coringa, Arlequina,
    Abóbora Maldita. Antes desta função ele não tinha onde guardar o figurino, e a saída era
    criar um "elenco" de um personagem só dentro dele mesmo (ver a migration
    ``c8f4d92e17ab``); agora a ficha mora no próprio item.

    Um item COM elenco é um tema, e num tema a ficha pertence a cada personagem — o pacote
    inteiro não veste um figurino só. Por isso a operação é recusada nesse caso, com a
    instrução do que fazer (a mesma regra guarda a criação de elenco, do outro lado).
    """
    if sheet is not None and item.characters:
        raise CatalogValidationError(
            "figurino_sheet_id",
            f'"{item.name}" é um tema com {len(item.characters)} personagem(ns) no elenco. '
            "Num tema a ficha pertence a cada personagem — vincule a ficha ao personagem, "
            "não ao tema.",
        )

    item.figurino_sheet_id = sheet.id if sheet else None
    audit(
        "edit",
        "CatalogItem",
        item.id,
        item.name,
        f'Ficha de figurino {"vinculada: " + sheet.character_name if sheet else "removida"}',
    )
    db.session.commit()
    return item


def flatten_to_avulso(item: CatalogItem) -> CatalogItem:
    """Transforma um tema de UM personagem só em item avulso, herdando a ficha dele.

    É a versão manual do que a migration ``c8f4d92e17ab`` fez automaticamente nos 12 casos em
    que o nome do personagem era idêntico ao do item. Os casos de nome apenas parecido
    ("Wandinha Addams" contendo "Wandinha", "Aracnídeo" contendo "Aranha") ficaram de fora de
    propósito: podem ser um tema legítimo, e a decisão é de quem organiza o catálogo — este é
    o botão que ela usa.

    A foto do personagem NÃO é copiada para o item: a página do item já tem a galeria própria,
    e era justamente a duplicação dessa foto no "Elenco Individual" que motivou a mudança.
    """
    if len(item.characters) != 1:
        raise CatalogValidationError(
            "item_id",
            f'"{item.name}" tem {len(item.characters)} personagens no elenco. '
            "Só um tema com exatamente um personagem vira item avulso.",
        )

    character = item.characters[0]
    if character.own_item_id:
        raise CatalogValidationError(
            "item_id",
            f'"{character.name}" tem página própria — desfaça a página própria antes.',
        )
    from app.models import VirtualCampaign

    if VirtualCampaign.query.filter_by(catalog_character_id=character.id).first():
        raise CatalogValidationError(
            "item_id",
            f'"{character.name}" tem campanha da Loja de Interações Virtuais e não pode ser '
            "removido do elenco.",
        )

    item.figurino_sheet_id = character.figurino_sheet_id
    nome_personagem = character.name
    db.session.delete(character)
    audit(
        "edit",
        "CatalogItem",
        item.id,
        item.name,
        f'Virou item avulso: personagem "{nome_personagem}" removido e ficha herdada pelo item',
    )
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
