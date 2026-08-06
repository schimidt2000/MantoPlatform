"""Catálogo público de personagens/shows (feature 133).

Sem login — página voltada à cliente final, alcançada por link (ex.: WhatsApp). Não
segue o padrão visual do restante do sistema (templates próprios, fora de `base.html`).
Não é indexado por buscadores: herda automaticamente o `X-Robots-Tag: noindex` global já
aplicado a todas as rotas do app (feature 127).
"""

from __future__ import annotations

import os
import re

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)

from app.catalogo.og_ops import resolve_thumbnail
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


def _send_og_thumbnail(cover_url: str | None):
    """Resposta da miniatura reencodada de uma capa, ou 404 quando não há capa utilizável."""
    thumb = resolve_thumbnail(cover_url, current_app.config["UPLOAD_FOLDER"])
    if not thumb:
        return "", 404

    response = send_file(thumb.path, mimetype="image/jpeg", max_age=86400)
    # O nome do arquivo em cache já carrega o hash da capa: conteúdo novo = URL de origem nova.
    response.headers["Cache-Control"] = "public, max-age=86400"
    # O `after_request` global carimba `noindex, nofollow, noarchive` em TUDO (feature 127), e o
    # crawler de prévia do WhatsApp (facebookexternalhit) pode recusar renderizar o card nessas
    # condições. Aqui sobrescrevemos: a imagem segue fora do índice, mas com a prévia liberada.
    response.headers["X-Robots-Tag"] = "noindex, max-image-preview:large"
    return response


@catalogo_bp.route("/og/<slug>.jpg")
def og_image(slug: str):
    """Miniatura da capa de um PRODUTO para a prévia de link compartilhado (WhatsApp e afins).

    A `og:image` das páginas da vitrine aponta para cá, e não para a foto original: o cliente do
    WhatsApp baixa a imagem inteira só para desenhar um quadrado pequeno e desiste sem prévia
    quando o arquivo é grande demais (ver `app/catalogo/og_ops.py`). Rota pública, como toda a
    superfície do catálogo — o `frontend/server.js` repassa `/catalogo/og/*` ao Flask antes de
    montar a SPA pública, mesmo arranjo de `/catalogo/midia/*`.
    """
    item = CatalogItem.query.filter_by(slug=slug, is_active=True).first()
    cover = item.cover_image if item else None
    return _send_og_thumbnail(cover.url if cover else None)


@catalogo_bp.route("/og/categoria/<slug>.jpg")
def og_image_categoria(slug: str):
    """Miniatura de um TEMA (categoria) do catálogo, pela mesma redução de bytes do produto.

    `CatalogCategory` não tem imagem própria no banco, então a capa do tema é a do PRIMEIRO item
    ativo dele — exatamente a regra que a vitrine já usa para desenhar o card da seção
    (`_category_summary` em `app/api/catalogo_read.py`). Assim a miniatura do link compartilhado
    é a mesma foto que a pessoa viu na grade antes de copiar o endereço.

    Não colide com `og_image`: o conversor padrão de `<slug>` não casa `/`, então
    `/og/categoria/x.jpg` só entra aqui.
    """
    category = CatalogCategory.query.filter_by(slug=slug).first()
    first_item = (
        CatalogItem.query.filter_by(is_active=True)
        .filter(CatalogItem.categories.any(CatalogCategory.id == category.id))
        .order_by(CatalogItem.name.asc())
        .first()
        if category
        else None
    )
    cover = first_item.cover_image if first_item else None
    return _send_og_thumbnail(cover.url if cover else None)


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

    # Prévia sempre pela miniatura de `/catalogo/og/<slug>.jpg`, nunca pela foto original:
    # arquivo grande faz o WhatsApp entregar o link sem imagem nenhuma (ver `og_ops.py`).
    og_image = (
        request.url_root.rstrip("/") + url_for("catalogo.og_image", slug=item.slug)
        if item.cover_image
        else None
    )

    primary_category = item.categories[0] if item.categories else None

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
        primary_category=primary_category,
        og_title=item.name,
        og_description=_plain_text(item.short_description_html),
        og_image=og_image,
        og_url=request.url,
    )
