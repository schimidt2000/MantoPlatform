"""Endpoints de LEITURA do Catálogo Público em React (feature 161, US1 da migração 144→US5).

Reaproveita literalmente as mesmas queries do blueprint Jinja `app/catalogo/routes.py` — só
troca `render_template` por `jsonify`. Público (sem `@login_required`/RBAC), mesma
acessibilidade do blueprint `catalogo_bp` hoje. As rotas Jinja `/catalogo/*` continuam no ar em
paralelo (a de detalhe é a fonte da prévia Open Graph em links compartilhados — ver
`specs/161-catalogo-publico-leitura/research.md` §4).
"""

from typing import Any

from flask import jsonify

from app.api import api_bp
from app.api_utils import json_error
from app.models import CatalogCategory, CatalogItem


def _item_summary(item: CatalogItem) -> dict[str, Any]:
    """Forma resumida de um item — usada nas listas (grade, categoria, relacionados)."""
    cover = item.cover_image
    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "cover_image_url": cover.url if cover else None,
        "categories": [c.name for c in item.categories],
    }


def _category_summary(category: CatalogCategory, items_by_category: dict[int, list[CatalogItem]]) -> dict[str, Any]:
    """Forma resumida de uma categoria, com contagem e capa — só chamada para categorias com item ativo."""
    items = items_by_category[category.id]
    cover = items[0].cover_image
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "item_count": len(items),
        "cover_image_url": cover.url if cover else None,
    }


@api_bp.route("/catalogo")
def api_catalogo_list() -> Any:
    """Grade geral do catálogo — itens ativos + categorias com contagem (paridade com `catalogo_bp.index`)."""
    from app.formularios.routes import DEFAULT_WHATSAPP_NUMBER, _whatsapp_target

    items = CatalogItem.query.filter_by(is_active=True).order_by(CatalogItem.name.asc()).all()

    items_by_category: dict[int, list[CatalogItem]] = {}
    for item in items:
        for cat in item.categories:
            items_by_category.setdefault(cat.id, []).append(item)

    categories = sorted(
        (c for c in CatalogCategory.query.all() if items_by_category.get(c.id)),
        key=lambda c: -len(items_by_category[c.id]),
    )

    return jsonify(
        {
            "items": [_item_summary(item) for item in items],
            "total": len(items),
            "categories": [_category_summary(c, items_by_category) for c in categories],
            "whatsapp_number": _whatsapp_target() or DEFAULT_WHATSAPP_NUMBER,
        }
    )


@api_bp.route("/catalogo/categorias")
def api_catalogo_categorias() -> Any:
    """Grade de categorias com item ativo (paridade com `catalogo_bp.categorias`)."""
    items = CatalogItem.query.filter_by(is_active=True).order_by(CatalogItem.name.asc()).all()

    items_by_category: dict[int, list[CatalogItem]] = {}
    for item in items:
        for cat in item.categories:
            items_by_category.setdefault(cat.id, []).append(item)

    categories = [
        c
        for c in CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()
        if items_by_category.get(c.id)
    ]

    return jsonify({"categories": [_category_summary(c, items_by_category) for c in categories]})


@api_bp.route("/catalogo/categoria/<slug>")
def api_catalogo_categoria_detail(slug: str) -> Any:
    """Itens ativos de uma categoria por slug (paridade com `catalogo_bp.categoria_detail`)."""
    category = CatalogCategory.query.filter_by(slug=slug).first()
    items = (
        CatalogItem.query.filter_by(is_active=True)
        .filter(CatalogItem.categories.any(CatalogCategory.id == category.id))
        .order_by(CatalogItem.name.asc())
        .all()
        if category
        else []
    )
    if not category or not items:
        return json_error("Categoria não encontrada", 404)

    return jsonify(
        {
            "category": {"id": category.id, "name": category.name, "slug": category.slug},
            "items": [_item_summary(item) for item in items],
        }
    )


@api_bp.route("/catalogo/<slug>")
def api_catalogo_detail(slug: str) -> Any:
    """Detalhe de um item, com fotos e relacionados (paridade com `catalogo_bp.detail`).

    Não inclui campos de Open Graph — esses só existem na rota Jinja, que segue sendo a fonte
    da prévia de link compartilhado (ver `research.md` §4 desta feature).
    """
    item = CatalogItem.query.filter_by(slug=slug, is_active=True).first()
    if not item:
        return json_error("Personagem não encontrado", 404)

    category_ids = [c.id for c in item.categories]
    related = []
    if category_ids:
        related = (
            CatalogItem.query.filter_by(is_active=True)
            .filter(
                CatalogItem.id != item.id,
                CatalogItem.categories.any(CatalogCategory.id.in_(category_ids)),
            )
            .order_by(CatalogItem.name.asc())
            .limit(6)
            .all()
        )

    return jsonify(
        {
            "id": item.id,
            "name": item.name,
            "slug": item.slug,
            "description_html": item.short_description_html,
            "categories": [{"name": c.name, "slug": c.slug} for c in item.categories],
            "images": [{"url": img.url, "position": img.position} for img in item.images],
            "related": [_item_summary(r) for r in related],
        }
    )
