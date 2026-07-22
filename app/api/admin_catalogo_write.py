"""Endpoints de ESCRITA da gestão de catálogo (feature 169, US6 — Cauda Administrativa).

Reusa, sem duplicar, `app.admin.catalog_ops`. Gate `require_superadmin`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.admin import catalog_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import CatalogItem


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
        )
    except catalog_ops.CatalogValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(_item_summary(item))


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
