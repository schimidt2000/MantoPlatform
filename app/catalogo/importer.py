"""Importador do catálogo de personagens exportado do WordPress/WooCommerce (feature 133).

Lê o CSV de export de produtos, baixa e comprime as fotos (reaproveitando
``app.storage.save_file``) e cria os itens do catálogo dentro do sistema — para que o
catálogo público não dependa do WordPress continuar no ar.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata
from datetime import datetime

import requests
from werkzeug.datastructures import FileStorage

from app import db
from app.models import CatalogCategory, CatalogItem, CatalogItemImage
from app.storage import save_file

HEAVY_IMAGE_BYTES = 300 * 1024  # acima disso entra no relatório de "imagens pesadas"
DOWNLOAD_TIMEOUT = 30


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", no_accents).strip("-")
    return slug or "item"


def _unique_slug(base: str, wp_product_id: int | None, used: set[str]) -> str:
    """Gera um slug único; em colisão (nomes repetidos de produtos diferentes),
    desambigua com o id do WordPress no sufixo."""
    slug = base
    if slug in used:
        suffix = str(wp_product_id) if wp_product_id else str(len(used) + 1)
        slug = f"{base}-{suffix}"
    n = 2
    while slug in used:
        slug = f"{base}-{suffix}-{n}"
        n += 1
    used.add(slug)
    return slug


def _clean_description(raw: str) -> str:
    """Remove artefatos de escape do export do WooCommerce (``\\n`` literal misturado com
    quebras de linha reais), mantendo o HTML simples (``<b>``, ``<span>``)."""
    if not raw:
        return ""
    cleaned = raw.replace("\\n", "")
    return cleaned.strip()


def _split_list(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def _rewrite_public_url(url: str) -> str:
    """Reescreve URL local (rota autenticada) para a rota pública do catálogo.

    ``save_file`` devolve ``/uploads/<subpasta>/<arquivo>`` em modo local (rota exige
    login) ou uma URL absoluta em modo S3/R2 (já pública) — só o primeiro caso precisa de
    reescrita.
    """
    if url.startswith("/uploads/"):
        filename = url.rsplit("/", 1)[-1]
        return f"/catalogo/midia/{filename}"
    return url


def _get_saved_file_size(url: str) -> int | None:
    """Tamanho do arquivo salvo — leitura direta em disco (modo local) ou HEAD HTTP
    (modo S3/R2, onde a URL já é publicamente alcançável)."""
    from flask import current_app

    if url.startswith(("http://", "https://")):
        try:
            resp = requests.head(url, timeout=10)
            length = resp.headers.get("Content-Length")
            return int(length) if length else None
        except (requests.RequestException, ValueError, TypeError):
            return None

    filename = url.rsplit("/", 1)[-1]
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "catalog_photos", filename)
    try:
        return os.path.getsize(full_path)
    except OSError:
        return None


def run_import(csv_path: str, limit: int = 0, echo=None) -> dict:
    """Importa o catálogo a partir do CSV exportado do WordPress.

    Args:
        csv_path: caminho do CSV exportado (WooCommerce Product CSV Export).
        limit: máximo de linhas a processar (0 = todas).
        echo: callback opcional ``(str) -> None`` para log de progresso.

    Returns:
        Dicionário de contagens da execução.
    """

    def _log(msg: str) -> None:
        if echo:
            echo(msg)

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    used_slugs = {s for (s,) in db.session.query(CatalogItem.slug).all()}
    existing_wp_ids = {
        wp_id for (wp_id,) in db.session.query(CatalogItem.wp_product_id).all() if wp_id
    }
    category_cache: dict[str, CatalogCategory] = {
        c.name: c for c in CatalogCategory.query.all()
    }

    counts = {
        "processed": 0,
        "imported": 0,
        "skipped_unpublished": 0,
        "skipped_no_content": 0,
        "skipped_duplicate": 0,
        "skipped_no_images": 0,
        "images_downloaded": 0,
        "images_failed": 0,
    }
    heavy_images: list[str] = []
    errors: list[str] = []

    processed = 0
    for row in rows:
        if limit and processed >= limit:
            break
        processed += 1
        counts["processed"] += 1

        wp_id_raw = (row.get("ID") or "").strip()
        wp_id = int(wp_id_raw) if wp_id_raw.isdigit() else None
        name = (row.get("Nome") or "").strip()

        if (row.get("Publicado") or "").strip() != "1":
            counts["skipped_unpublished"] += 1
            continue

        if wp_id and wp_id in existing_wp_ids:
            counts["skipped_duplicate"] += 1
            continue

        category_names = _split_list(row.get("Categorias") or "")
        image_urls = _split_list(row.get("Imagens") or "")

        if not name or (not category_names and not image_urls):
            counts["skipped_no_content"] += 1
            continue

        _log(f"  [{processed:>4}] importando: {name}")

        item_images: list[CatalogItemImage] = []
        for position, img_url in enumerate(image_urls):
            try:
                resp = requests.get(img_url, timeout=DOWNLOAD_TIMEOUT)
                resp.raise_for_status()
                original_filename = os.path.basename(img_url.split("?")[0]) or "imagem.jpg"
                fs = FileStorage(
                    stream=io.BytesIO(resp.content), filename=original_filename
                )
                saved_url = save_file(fs, "catalog_photos")
                public_url = _rewrite_public_url(saved_url)
                size = _get_saved_file_size(saved_url)
                if size and size > HEAVY_IMAGE_BYTES:
                    heavy_images.append(f"{name} — {public_url} ({size // 1024}KB)")
                item_images.append(
                    CatalogItemImage(
                        url=public_url, original_url=img_url,
                        position=position, file_size_bytes=size,
                    )
                )
                counts["images_downloaded"] += 1
            except (requests.RequestException, OSError) as exc:
                counts["images_failed"] += 1
                errors.append(f"{name}: falha ao baixar {img_url} ({exc})")
                _log(f"       ERRO imagem: {img_url} ({exc})")

        if not item_images:
            counts["skipped_no_images"] += 1
            _log(f"       descartado — nenhuma imagem baixada com sucesso: {name}")
            continue

        slug = _unique_slug(_slugify(name), wp_id, used_slugs)

        categories = []
        for cat_name in category_names:
            cat = category_cache.get(cat_name)
            if not cat:
                cat = CatalogCategory(name=cat_name, slug=_slugify(cat_name))
                db.session.add(cat)
                db.session.flush()
                category_cache[cat_name] = cat
            categories.append(cat)

        tags = _split_list(row.get("Tags") or "")

        item = CatalogItem(
            wp_product_id=wp_id,
            name=name,
            slug=slug,
            short_description_html=_clean_description(row.get("Descrição curta") or ""),
            tags=json.dumps(tags) if tags else None,
            imported_at=datetime.utcnow(),
        )
        item.categories = categories
        item.images = item_images
        db.session.add(item)
        db.session.commit()
        if wp_id:
            existing_wp_ids.add(wp_id)
        counts["imported"] += 1

    counts["heavy_images"] = heavy_images
    counts["errors"] = errors
    return counts
