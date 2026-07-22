"""Endpoints de LEITURA da gestão de catálogo (feature 169, US6 — Cauda Administrativa).

Reusa, sem duplicar, `app.admin.catalog_ops`. Gate `require_superadmin` reimplementado.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import CatalogCategory, CatalogItem


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


@api_bp.route("/admin/catalogo")
@api_login_required
def api_admin_catalogo_list() -> Any:
    """Lista/filtra produtos do catálogo (feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    q = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria", "").strip()
    status = request.args.get("status", "todos").strip()

    query = CatalogItem.query
    if q:
        query = query.filter(CatalogItem.name.ilike(f"%{q}%"))
    if categoria_id.isdigit():
        query = query.filter(CatalogItem.categories.any(CatalogCategory.id == int(categoria_id)))
    if status == "ativo":
        query = query.filter_by(is_active=True)
    elif status == "inativo":
        query = query.filter_by(is_active=False)

    items = query.order_by(CatalogItem.name.asc()).all()
    categories = CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()
    return jsonify(
        {
            "items": [_item_summary(i) for i in items],
            "categories": [{"id": c.id, "name": c.name} for c in categories],
        }
    )


@api_bp.route("/admin/catalogo/<int:item_id>")
@api_login_required
def api_admin_catalogo_detail(item_id: int) -> Any:
    """Detalhe de um produto do catálogo, para o formulário de edição (feature 169)."""
    denied = _require_superadmin()
    if denied:
        return denied
    item = CatalogItem.query.get(item_id)
    if item is None:
        return json_error("Produto não encontrado", 404)
    return jsonify(
        {
            "id": item.id,
            "name": item.name,
            "description": item.short_description_html or "",
            "tags": item.tags_list,
            "is_active": item.is_active,
            "category_ids": [c.id for c in item.categories],
            "images": [
                {"id": img.id, "url": img.url, "position": img.position} for img in item.images
            ],
        }
    )
