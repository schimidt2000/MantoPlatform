"""Miniatura Open Graph das páginas públicas do catálogo (prévia de link no WhatsApp).

Por que existe uma imagem separada da foto de capa: o cliente do WhatsApp baixa a `og:image`
inteira só para desenhar um quadradinho de ~300px e desiste em silêncio quando o arquivo é
grande — as fotos do catálogo têm ~220KB em média e chegam a 490KB, exatamente a faixa em que a
prévia começa a sair sem miniatura. Aqui a capa é reencodada com teto de bytes (``_MAX_BYTES``),
em JPEG opaco (PNG com alfa vira fundo branco; a prévia não tem transparência).

Vale tanto para a página de PRODUTO (`/catalogo/<slug>`) quanto para a de TEMA
(`/catalogo/categoria/<slug>`) — a diferença entre as duas é só qual capa entra aqui, decidida
por quem chama (`app/catalogo/routes.py`).

Módulo puro no sentido da constituição do projeto: nada de ``flask.request``/``render_template``
— quem chama passa a raiz de uploads e a URL da capa. Ver `app/catalogo/routes.py:og_image`.
"""

from __future__ import annotations

import glob
import hashlib
import io
import logging
import os
import re
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

#: Teto de bytes do JPEG final. Abaixo disso a prévia do WhatsApp é confiável em Android/iOS.
_MAX_BYTES = 280_000

#: Tentativas em ordem decrescente de custo — a primeira que couber em `_MAX_BYTES` vence.
_ATTEMPTS = ((1200, 82), (1200, 70), (900, 68), (700, 62))

#: Muda quando a receita de encode muda — entra na chave de cache e invalida o disco.
_RECIPE_VERSION = "1"

#: Subpastas de ``UPLOAD_FOLDER``: origem das fotos do catálogo e cache das miniaturas.
MEDIA_SUBFOLDER = "catalog_photos"
CACHE_SUBFOLDER = "catalog_og"

#: O nome do cache é ``{digest}_{largura}x{altura}.jpg``. As dimensões moram no NOME porque
#: `og:image:width`/`og:image:height` são pedidas a cada prévia, e reabrir o JPEG só para medi-lo
#: custaria um decode por acesso.
_CACHE_NAME_RE = re.compile(r"_(\d+)x(\d+)\.jpg$")


class Thumbnail(NamedTuple):
    """Miniatura pronta em disco: caminho do arquivo e dimensões reais do JPEG."""

    path: str
    width: int
    height: int


def cache_digest(source_url: str) -> str:
    """Prefixo do arquivo de cache de uma capa — troca sozinho quando a capa ou a receita muda."""
    return hashlib.md5(f"{_RECIPE_VERSION}|{source_url}".encode()).hexdigest()


def find_cached(source_url: str, cache_folder: str) -> Thumbnail | None:
    """Miniatura já gerada para esta capa, lendo as dimensões do nome do arquivo.

    Args:
        source_url: ``CatalogItemImage.url`` da capa.
        cache_folder: Pasta em disco onde as miniaturas são gravadas.

    Returns:
        A miniatura em cache, ou ``None`` quando ainda não foi gerada.
    """
    for path in glob.glob(os.path.join(cache_folder, f"{cache_digest(source_url)}_*.jpg")):
        match = _CACHE_NAME_RE.search(os.path.basename(path))
        if not match:
            continue
        try:
            if os.path.getsize(path) > 0:
                return Thumbnail(path, int(match.group(1)), int(match.group(2)))
        except OSError as exc:  # arquivo removido entre o glob e o stat — segue para o próximo
            logger.warning("og: cache ilegível %s: %s", path, exc)
    return None


def _read_source(source_url: str, media_folder: str) -> bytes | None:
    """Lê os bytes da capa, seja arquivo local (`/catalogo/midia/...`) ou objeto remoto (S3/R2)."""
    if source_url.startswith(("http://", "https://")):
        import requests

        try:
            resp = requests.get(source_url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            logger.warning("og: falha ao baixar capa remota %s: %s", source_url, exc)
            return None

    filename = os.path.basename(source_url)
    path = os.path.join(media_folder, filename)
    # `basename` + `commonpath` cortam qualquer tentativa de sair da pasta de mídia via `..`.
    if os.path.commonpath([os.path.abspath(media_folder), os.path.abspath(path)]) != os.path.abspath(media_folder):
        return None
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        logger.warning("og: capa local ausente %s: %s", path, exc)
        return None


def _decode_opaque(raw: bytes, source_url: str) -> Any:
    """Abre os bytes como imagem RGB opaca (a prévia não suporta transparência).

    Returns:
        Um ``PIL.Image.Image`` em modo RGB, ou ``None`` se a imagem não puder ser decodificada.
    """
    try:
        from PIL import Image, ImageOps

        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))
            flat.paste(img, mask=img.getchannel("A"))
            return flat
        return img if img.mode == "RGB" else img.convert("RGB")
    except Exception as exc:  # noqa: BLE001 — imagem corrompida não pode derrubar a página
        logger.warning("og: falha ao decodificar capa %s: %s", source_url, exc)
        return None


def build_thumbnail(source_url: str, media_folder: str) -> tuple[bytes, int, int] | None:
    """Gera o JPEG de prévia da capa, ou ``None`` se a imagem não puder ser lida/decodificada.

    Args:
        source_url: ``CatalogItemImage.url`` da capa — caminho local ou URL absoluta (S3/R2).
        media_folder: Pasta em disco das fotos do catálogo (`uploads/catalog_photos`).

    Returns:
        ``(bytes, largura, altura)`` do JPEG dentro do teto de tamanho, ou ``None`` para quem
        chama devolver 404. As dimensões saem daqui porque só este ponto sabe qual das
        tentativas de resize venceu — e elas viram `og:image:width`/`og:image:height`.
    """
    raw = _read_source(source_url, media_folder)
    if not raw:
        return None
    img = _decode_opaque(raw, source_url)
    if img is None:
        return None

    from PIL import Image

    encoded, size = b"", (img.width, img.height)
    for max_px, quality in _ATTEMPTS:
        frame = img.copy()
        if max(frame.width, frame.height) > max_px:
            frame.thumbnail((max_px, max_px), Image.LANCZOS)
        buffer = io.BytesIO()
        frame.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
        encoded, size = buffer.getvalue(), (frame.width, frame.height)
        if len(encoded) <= _MAX_BYTES:
            break

    # Nenhuma tentativa coube: devolve a menor (última) mesmo assim — prévia grande é melhor
    # que prévia nenhuma, e o teto é heurístico.
    return (encoded, size[0], size[1]) if encoded else None


def cached_thumbnail(source_url: str, media_folder: str, cache_folder: str) -> Thumbnail | None:
    """Miniatura em disco, gerando-a na primeira chamada.

    Returns:
        A miniatura pronta para `send_file`, ou ``None`` se a capa não pôde ser lida.
    """
    existing = find_cached(source_url, cache_folder)
    if existing:
        return existing

    built = build_thumbnail(source_url, media_folder)
    if not built:
        return None
    data, width, height = built

    path = os.path.join(cache_folder, f"{cache_digest(source_url)}_{width}x{height}.jpg")
    os.makedirs(cache_folder, exist_ok=True)
    # Escrita atômica: dois requests simultâneos do mesmo link não podem servir arquivo pela metade.
    temp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except OSError as exc:
        logger.warning("og: falha ao gravar cache %s: %s", path, exc)
        try:
            os.remove(temp)
        except OSError:
            pass
        return None
    return Thumbnail(path, width, height)


def resolve_thumbnail(source_url: str | None, uploads_folder: str) -> Thumbnail | None:
    """Miniatura de prévia de uma capa a partir da raiz de uploads do app.

    Concentra aqui a convenção de subpastas (`catalog_photos` / `catalog_og`) para que a rota da
    imagem e a API de prévia não a repitam — e, com o tempo, não divirjam.

    Args:
        source_url: URL da capa, ou ``None`` quando o item/tema não tem foto.
        uploads_folder: `UPLOAD_FOLDER` do app.

    Returns:
        A miniatura, ou ``None`` quando não há capa utilizável.
    """
    if not source_url:
        return None
    return cached_thumbnail(
        source_url,
        media_folder=os.path.join(uploads_folder, MEDIA_SUBFOLDER),
        cache_folder=os.path.join(uploads_folder, CACHE_SUBFOLDER),
    )
