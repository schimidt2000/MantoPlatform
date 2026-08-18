"""Endpoints de ESCRITA da gestão de catálogo (feature 169, US6 — Cauda Administrativa).

Reusa, sem duplicar, `app.admin.catalog_ops`. Gate `require_superadmin`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.admin import catalog_character_ops, catalog_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import CatalogCharacter, CatalogItem, CatalogItemImage, FigurinoSheet


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _item_summary(item: CatalogItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "is_active": item.is_active,
        "cover_url": item.cover_image.url if item.cover_image else None,
        "category_names": [c.name for c in item.categories],
    }


def _item_summary_full(item: CatalogItem) -> dict:
    """Resumo COMPLETO do item — o mesmo que a listagem devolve.

    As ações que mudam o tipo do item (ficha própria, virar avulso) precisam responder com
    `kind`/`figurino_sheet_*`, senão a tela recebe de volta um objeto que não descreve o que
    acabou de mudar. Import local: os dois módulos são carregados por `app/api/__init__.py` e
    um import no topo criaria dependência circular na ordem de registro das rotas.
    """
    from app.api.admin_catalogo_read import _item_summary as _full

    return _full(item)


@api_bp.route("/admin/catalogo/categorias", methods=["POST"])
@api_login_required
def api_admin_catalogo_new_category() -> Any:
    """Cria (ou reaproveita) uma categoria do catálogo (feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        category = catalog_ops.create_or_reuse_category(body.get("name", ""))
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"id": category.id, "name": category.name})


@api_bp.route("/admin/catalogo", methods=["POST"])
@api_login_required
def api_admin_catalogo_create() -> Any:
    """Cria um novo produto do catálogo (multipart, feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    category_ids = [int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()]
    try:
        item = catalog_ops.create_product(
            name=request.form.get("name", ""),
            description=request.form.get("description", ""),
            tags_raw=request.form.get("tags", ""),
            category_ids=category_ids,
            form=request.form,
            files=request.files,
            video_url=request.form.get("video_url", ""),
        )
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_item_summary(item)), 201


@api_bp.route("/admin/catalogo/<int:item_id>", methods=["PATCH"])
@api_login_required
def api_admin_catalogo_update(item_id: int) -> Any:
    """Edita um produto existente do catálogo (multipart, feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    category_ids = [int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()]
    try:
        catalog_ops.update_product(
            item,
            name=request.form.get("name", ""),
            description=request.form.get("description", ""),
            tags_raw=request.form.get("tags", ""),
            category_ids=category_ids,
            form=request.form,
            files=request.files,
            video_url=request.form.get("video_url", ""),
        )
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_item_summary(item))


@api_bp.route("/admin/catalogo/<int:item_id>/figurino", methods=["POST"])
@api_login_required
def api_admin_catalogo_item_figurino(item_id: int) -> Any:
    """Vincula/desvincula a ficha de figurino de um item AVULSO (`{"figurino_sheet_id": int|null}`).

    Só para item sem elenco: num tema a ficha pertence a cada personagem (fase 1 da
    reestruturação do catálogo — ver `catalog_ops.set_item_figurino`).
    """
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)

    body = request.get_json(silent=True) or {}
    raw = body.get("figurino_sheet_id")
    sheet = None
    if raw is not None:
        sheet = FigurinoSheet.query.get(raw)
        if sheet is None:
            return json_error("Ficha de figurino não encontrada", 404)
    try:
        catalog_ops.set_item_figurino(item, sheet)
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_item_summary_full(item))


@api_bp.route("/admin/catalogo/<int:item_id>/virar-avulso", methods=["POST"])
@api_login_required
def api_admin_catalogo_item_flatten(item_id: int) -> Any:
    """Transforma um tema de UM personagem só em item avulso, herdando a ficha dele (fase 1)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    try:
        catalog_ops.flatten_to_avulso(item)
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_item_summary_full(item))


@api_bp.route("/admin/catalogo/<int:item_id>/toggle-ativo", methods=["POST"])
@api_login_required
def api_admin_catalogo_toggle_ativo(item_id: int) -> Any:
    """Ativa/inativa um produto do catálogo (feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    catalog_ops.toggle_active(item)
    return jsonify(_item_summary(item))


@api_bp.route("/admin/catalogo/<int:item_id>", methods=["DELETE"])
@api_login_required
def api_admin_catalogo_delete(item_id: int) -> Any:
    """Exclui definitivamente um produto do catálogo, com suas fotos (feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    catalog_ops.delete_product(item)
    return "", 204


def _character_summary(character: CatalogCharacter) -> dict:
    own = character.own_item
    return {
        "id": character.id,
        "name": character.name,
        "slug": character.slug,
        "photo_url": character.photo_url,
        "video_url": character.video_url,
        "figurino_sheet_id": character.figurino_sheet_id,
        "position": character.position,
        "is_active": character.is_active,
        # Página própria (feature 209) — null = personagem só existe no elenco do tema.
        "own_item": (
            {"id": own.id, "name": own.name, "slug": own.slug, "is_active": own.is_active}
            if own
            else None
        ),
    }


@api_bp.route("/admin/catalogo/<int:item_id>/personagens", methods=["POST"])
@api_login_required
def api_admin_catalogo_character_create(item_id: int) -> Any:
    """Cria um Personagem filho de um Tema (feature 185)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    figurino_sheet_id_raw = request.form.get("figurino_sheet_id", "")
    try:
        character = catalog_character_ops.create_character(
            item,
            name=request.form.get("name", ""),
            video_url=request.form.get("video_url", ""),
            figurino_sheet_id=int(figurino_sheet_id_raw) if figurino_sheet_id_raw.isdigit() else None,
            photo_file=request.files.get("photo"),
        )
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character)), 201


@api_bp.route("/admin/catalogo/personagens/<int:character_id>", methods=["PATCH"])
@api_login_required
def api_admin_catalogo_character_update(character_id: int) -> Any:
    """Edita um Personagem existente (feature 185)."""
    denied = _require_superadmin()
    if denied:
        return denied
    character = CatalogCharacter.query.get(character_id)
    if character is None:
        return json_error("Personagem não encontrado", 404)

    figurino_sheet_id = ...  # sentinela "não alterar" — ver catalog_character_ops.update_character
    if "figurino_sheet_id" in request.form:
        raw = request.form.get("figurino_sheet_id", "")
        figurino_sheet_id = int(raw) if raw.isdigit() else None

    try:
        catalog_character_ops.update_character(
            character,
            name=request.form.get("name") if "name" in request.form else None,
            video_url=request.form.get("video_url") if "video_url" in request.form else None,
            figurino_sheet_id=figurino_sheet_id,
            position=int(request.form["position"]) if "position" in request.form else None,
            is_active=(request.form.get("is_active", "").lower() == "true")
            if "is_active" in request.form
            else None,
            photo_file=request.files.get("photo"),
            remove_photo=request.form.get("remove_photo", "").lower() == "true",
        )
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character))


@api_bp.route("/admin/catalogo/<int:item_id>/personagens/reaproveitar", methods=["POST"])
@api_login_required
def api_admin_catalogo_character_reuse(item_id: int) -> Any:
    """Põe no elenco deste tema um personagem que já existe (`{"figurino_sheet_id": int}`).

    A ficha é a identidade do personagem (feature 235) — é ela que diz que o Gatuno da Gabby e o
    Gatuno da Gabby Humanizada são o mesmo.
    """
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Tema não encontrado", 404)
    body = request.get_json(silent=True) or {}
    sheet = FigurinoSheet.query.get(body.get("figurino_sheet_id"))
    if sheet is None:
        return json_error("Ficha de figurino não encontrada", 404)
    try:
        character = catalog_character_ops.reuse_character(item, sheet)
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character)), 201


@api_bp.route("/admin/catalogo/personagens/<int:character_id>/adotar-foto", methods=["POST"])
@api_login_required
def api_admin_catalogo_character_adopt_photo(character_id: int) -> Any:
    """Adota uma foto da galeria do Tema como foto do Personagem (drag-and-drop)."""
    denied = _require_superadmin()
    if denied:
        return denied
    character = CatalogCharacter.query.get(character_id)
    if character is None:
        return json_error("Personagem não encontrado", 404)
    body = request.get_json(silent=True) or {}
    image_id = body.get("image_id")
    image = CatalogItemImage.query.get(image_id) if image_id else None
    if image is None:
        return json_error("Foto da galeria não encontrada", 404)
    try:
        catalog_character_ops.adopt_gallery_photo(character, image)
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character))


@api_bp.route("/admin/catalogo/personagens/<int:character_id>", methods=["DELETE"])
@api_login_required
def api_admin_catalogo_character_delete(character_id: int) -> Any:
    """Exclui definitivamente um Personagem (feature 185)."""
    denied = _require_superadmin()
    if denied:
        return denied
    character = CatalogCharacter.query.get(character_id)
    if character is None:
        return json_error("Personagem não encontrado", 404)
    catalog_character_ops.delete_character(character)
    return "", 204


@api_bp.route("/admin/catalogo/personagens/<int:character_id>/pagina-propria", methods=["POST"])
@api_login_required
def api_admin_catalogo_character_own_page(character_id: int) -> Any:
    """Vincula (`{"item_id": int}`) ou remove (`{"item_id": null}`) a página própria."""
    denied = _require_superadmin()
    if denied:
        return denied
    character = CatalogCharacter.query.get(character_id)
    if character is None:
        return json_error("Personagem não encontrado", 404)
    body = request.get_json(silent=True) or {}
    item_id = body.get("item_id")
    item = None
    if item_id is not None:
        item = CatalogItem.query.get(item_id)
        if item is None:
            return json_error("Item não encontrado", 404)
    try:
        catalog_character_ops.set_own_item(character, item)
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character))


@api_bp.route("/admin/catalogo/personagens/<int:character_id>/pagina-unica", methods=["POST"])
@api_login_required
def api_admin_catalogo_character_toggle_page(character_id: int) -> Any:
    """Checkbox "Página única": liga/desliga o `is_active` do item vinculado."""
    denied = _require_superadmin()
    if denied:
        return denied
    character = CatalogCharacter.query.get(character_id)
    if character is None:
        return json_error("Personagem não encontrado", 404)
    body = request.get_json(silent=True) or {}
    try:
        catalog_character_ops.toggle_own_page(character, bool(body.get("enabled")))
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character))


@api_bp.route("/admin/catalogo/<int:tema_id>/adotar-item", methods=["POST"])
@api_login_required
def api_admin_catalogo_adopt_item(tema_id: int) -> Any:
    """Adota um item existente como personagem deste tema (`{"item_id": int}`) — caso Coelho."""
    denied = _require_superadmin()
    if denied:
        return denied
    tema = CatalogItem.query.get(tema_id)
    if tema is None:
        return json_error("Tema não encontrado", 404)
    body = request.get_json(silent=True) or {}
    item = CatalogItem.query.get(body.get("item_id")) if body.get("item_id") else None
    if item is None:
        return json_error("Item não encontrado", 404)
    try:
        character = catalog_character_ops.adopt_item_as_character(tema, item)
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_character_summary(character)), 201


@api_bp.route("/admin/catalogo/personagens/mover-em-massa", methods=["POST"])
@api_login_required
def api_admin_catalogo_characters_move_bulk() -> Any:
    """Realoca em massa Personagens para um novo Tema pai (feature 186, US4)."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    character_ids = body.get("character_ids") or []
    target_item_id = body.get("target_item_id")

    target_item = CatalogItem.query.get(target_item_id) if target_item_id else None
    if target_item is None or not target_item.is_active:
        return json_error("Tema de destino não encontrado ou inativo", 404)

    try:
        moved = catalog_character_ops.move_characters(character_ids, target_item)
    except catalog_character_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"moved": moved})
