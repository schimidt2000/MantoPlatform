"""Arquivos públicos do catálogo: fotos e miniaturas de prévia de link.

A vitrine de personagens é React (`frontend/apps/public`, montada em `/catalogo/*` pelo
`frontend/server.js`). As páginas Jinja que existiam aqui — grade, temas, lista de desejos e
detalhe do produto — saíram na fase 3 da remoção do Jinja; estavam **sombreadas** desde a feature
186, quando a SPA passou a ocupar esse endereço, e a prévia de link que elas geravam foi para o
`server.js`, que injeta as meta tags no `index.html` do bundle.

O que sobra são rotas de ARQUIVO, e elas ficam: `/catalogo/midia/*` e `/catalogo/og/*` estão entre
os prefixos que a porta pública repassa ao Flask, casados **antes** do mount da SPA justamente para
que a imagem não seja engolida pelo `index.html`.
"""

from __future__ import annotations

import os

from flask import Blueprint, current_app, send_file, send_from_directory

from app.catalogo.og_ops import LARGURAS_PERMITIDAS, resolve_thumbnail, resolve_variante
from app.models import CatalogCategory, CatalogItem

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")


@catalogo_bp.route("/midia/campanhas/<path:filename>")
def midia_campanha(filename: str):
    """Capa das campanhas da Loja de Interações Virtuais — rota **pública** (feature 224b).

    A capa precisa abrir para quem nunca logou: quem vê a landing é a família comprando. Salva
    em `virtual_covers`, ela caía na rota geral `/uploads/*`, que é `login_required` — o visitante
    era redirecionado para a tela de login do staff e a landing ficava sem imagem.

    Mora sob `/catalogo/midia/` de propósito: esse prefixo já é repassado ao Flask pelo
    `frontend/server.js` e proxiado pelos vite configs dos três apps. Um prefixo novo exigiria
    mexer nos três — o gap de proxy por app que já mordeu antes (feature 182). A pasta em disco
    continua separada, então nada se mistura com as fotos do catálogo.

    Declarada ANTES da rota genérica: `<path:filename>` engoliria `campanhas/arquivo.jpg`.
    """
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "virtual_covers")
    # Mesmo cache longo da rota irmã: a capa também nasce com nome UUID (`save_file` em
    # `app/api/virtuais_write.py:62`), então trocar a capa muda a URL.
    resposta = send_from_directory(folder, filename, max_age=_CACHE_MIDIA_SEGUNDOS)
    resposta.headers["Cache-Control"] = f"public, max-age={_CACHE_MIDIA_SEGUNDOS}, immutable"
    return resposta


#: Um ano. Seguro porque o NOME é o conteúdo: `storage.save_file` grava cada foto com um UUID
#: novo (`catalog_character_ops.py:89,149` chamam sem `filename`), então trocar a foto de um
#: personagem produz uma URL diferente — nunca o mesmo endereço com bytes diferentes.
_CACHE_MIDIA_SEGUNDOS = 31_536_000


@catalogo_bp.route("/midia/t/<int:largura>/<filename>")
def midia_variante(largura: int, filename: str):
    """Variante de ``largura`` px de uma foto do catálogo (feature 270), gerada sob demanda.

    Variante no CAMINHO, não em query string: há CDN na frente (o `cf-cache-status` aparece nas
    respostas) e cache de CDN com query string é território de configuração — caminho é
    inequívoco, e cada variante é uma URL própria, então o `immutable` da 268 continua valendo
    sem ressalva. A largura vem de uma allowlist fechada (`LARGURAS_PERMITIDAS`); fora dela é
    404 e nada é gravado. `<filename>` (sem `path:`) já recusa barra, e `og_ops` corta `..`.

    Declarada ANTES de `midia`: `<path:filename>` engoliria `t/128/arquivo.jpg`.
    """
    if largura not in LARGURAS_PERMITIDAS:
        return "", 404
    thumb = resolve_variante(
        f"/catalogo/midia/{filename}", largura, current_app.config["UPLOAD_FOLDER"]
    )
    if not thumb:
        return "", 404
    resposta = send_file(thumb.path, mimetype="image/jpeg", max_age=_CACHE_MIDIA_SEGUNDOS)
    # Mesmo `immutable` da foto original: o nome de origem é UUID, então foto nova = URL nova.
    resposta.headers["Cache-Control"] = f"public, max-age={_CACHE_MIDIA_SEGUNDOS}, immutable"
    return resposta


@catalogo_bp.route("/midia/<path:filename>")
def midia(filename: str):
    """Serve fotos do catálogo — só desta subpasta, nunca a `/uploads` geral (login-only,
    serve documentos/contratos).

    `max_age` explícito (feature 268): sem ele o Flask responde `Cache-Control: no-cache`, que
    obriga o navegador a **revalidar cada imagem em toda visita**. Com as ~460 fotos da vitrine
    isso são ~460 idas ao servidor por página, mesmo com tudo já em cache — e é metade da
    lentidão que a cliente sente. A outra metade é o peso dos arquivos (ver
    `scripts/comprimir_imagens.py`).
    """
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "catalog_photos")
    resposta = send_from_directory(folder, filename, max_age=_CACHE_MIDIA_SEGUNDOS)
    # `immutable` dispensa até a revalidação condicional: o navegador nem pergunta.
    resposta.headers["Cache-Control"] = f"public, max-age={_CACHE_MIDIA_SEGUNDOS}, immutable"
    return resposta


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
