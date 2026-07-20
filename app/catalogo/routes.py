"""Catálogo público de personagens/shows (feature 133).

Sem login — página voltada à cliente final, alcançada por link (ex.: WhatsApp). Não
segue o padrão visual do restante do sistema (templates próprios, fora de `base.html`).
Não é indexado por buscadores: herda automaticamente o `X-Robots-Tag: noindex` global já
aplicado a todas as rotas do app (feature 127).
"""

from __future__ import annotations

import os
import re

from flask import Blueprint, current_app, render_template, request, send_from_directory

from app.models import CatalogCategory, CatalogItem

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")

_TAG_RE = re.compile(r"<[^>]+>")


def _plain_text(html: str, max_len: int = 200) -> str:
    """Descrição sem HTML, truncada — usada em og:description."""
    text = _TAG_RE.sub(" ", html or "")
    text = " ".join(text.split())
    return (text[: max_len - 1] + "…") if len(text) > max_len else text


@catalogo_bp.route("/")
def index():
    items = (
        CatalogItem.query.filter_by(is_active=True)
        .order_by(CatalogItem.name.asc())
        .all()
    )

    category_counts: dict[int, int] = {}
    for item in items:
        for cat in item.categories:
            category_counts[cat.id] = category_counts.get(cat.id, 0) + 1

    categories = sorted(
        (c for c in CatalogCategory.query.all() if category_counts.get(c.id)),
        key=lambda c: -category_counts.get(c.id, 0),
    )

    cards = [
        {
            "item": item,
            "cover": item.cover_image,
            "category_names": [c.name for c in item.categories],
            "search_text": " ".join(
                [item.name, *item.tags_list, *[c.name for c in item.categories]]
            ),
        }
        for item in items
    ]

    return render_template(
        "catalogo/index.html",
        cards=cards,
        categories=categories,
        category_counts=category_counts,
        total=len(items),
    )


@catalogo_bp.route("/midia/<path:filename>")
def midia(filename: str):
    """Serve fotos do catálogo — só desta subpasta, nunca a `/uploads` geral (login-only,
    serve documentos/contratos)."""
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "catalog_photos")
    return send_from_directory(folder, filename)


@catalogo_bp.route("/categorias")
def categorias():
    """Grade de categorias do catálogo, cada uma com uma foto representativa (feature 140)."""
    items = CatalogItem.query.filter_by(is_active=True).order_by(CatalogItem.name.asc()).all()

    by_category: dict[int, list[CatalogItem]] = {}
    for item in items:
        for cat in item.categories:
            by_category.setdefault(cat.id, []).append(item)

    cards = [
        {"category": c, "count": len(by_category[c.id]), "cover": by_category[c.id][0].cover_image}
        for c in CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()
        if by_category.get(c.id)
    ]

    return render_template("catalogo/categorias.html", cards=cards)


@catalogo_bp.route("/categoria/<slug>")
def categoria_detail(slug: str):
    """Produtos ativos de uma categoria, com fotos maiores que a grade compacta (feature 140)."""
    category = CatalogCategory.query.filter_by(slug=slug).first()
    items = (
        CatalogItem.query.filter_by(is_active=True)
        .filter(CatalogItem.categories.any(CatalogCategory.id == category.id))
        .order_by(CatalogItem.name.asc())
        .all()
        if category else []
    )
    if not category or not items:
        return render_template("catalogo/invalid.html"), 404

    return render_template("catalogo/categoria_detail.html", category=category, items=items)


@catalogo_bp.route("/lista-desejos")
def lista_desejos():
    """Página da lista de desejos — conteúdo é montado no navegador via localStorage
    (feature 140); o servidor só injeta o WhatsApp comercial de destino."""
    from app.formularios.routes import DEFAULT_WHATSAPP_NUMBER, _whatsapp_target

    return render_template(
        "catalogo/lista_desejos.html",
        whatsapp_number=_whatsapp_target() or DEFAULT_WHATSAPP_NUMBER,
    )


@catalogo_bp.route("/<slug>")
def detail(slug: str):
    item = CatalogItem.query.filter_by(slug=slug, is_active=True).first()
    if not item:
        return render_template("catalogo/invalid.html"), 404

    cover = item.cover_image
    og_image = None
    if cover:
        og_image = cover.url
        if og_image.startswith("/"):
            og_image = request.url_root.rstrip("/") + og_image

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

    return render_template(
        "catalogo/detail.html",
        item=item,
        related=related,
        og_title=item.name,
        og_description=_plain_text(item.short_description_html),
        og_image=og_image,
        og_url=request.url,
    )
