"""Motor de miniaturas do catálogo: prévia Open Graph e variantes por largura (feature 270).

Nasceu (feature 209) como a imagem separada da foto de capa para a prévia de link no WhatsApp: o
cliente do WhatsApp baixa a `og:image` inteira só para desenhar um quadradinho de ~300px e desiste
em silêncio quando o arquivo é grande. A capa é reencodada com teto de bytes (``_MAX_BYTES``), em
JPEG opaco (PNG com alfa vira fundo branco; a prévia não tem transparência).

A feature 270 **generaliza o mesmo motor** para as variantes que a vitrine e o Banco de Talentos
pedem por caminho (`/catalogo/midia/t/<largura>/<arquivo>`, `/uploads/t/<largura>/talent_photos/
<arquivo>`): mesma cache em disco por digest, mesmas dimensões no nome do arquivo, mesma escrita
atômica. O que varia é a ``Receita`` — a lista de tentativas (largura × qualidade), o teto de
bytes e se o redimensionamento é pelo lado maior (prévia) ou pela largura (variante, porque um
`<img>` de card é limitado pela largura da coluna, não pela altura).

Módulo puro no sentido da constituição do projeto: nada de ``flask.request``/``render_template``
— quem chama passa a raiz de uploads e a URL de origem. Ver `app/catalogo/routes.py` e a rota
`/uploads/t/...` em `app/__init__.py`.
"""

from __future__ import annotations

import glob
import hashlib
import io
import logging
import os
import re
import tempfile
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

#: Teto de bytes do JPEG da prévia. Abaixo disso a prévia do WhatsApp é confiável em Android/iOS.
_MAX_BYTES = 280_000

#: Tentativas da prévia em ordem decrescente de custo — a primeira que couber em `_MAX_BYTES` vence.
_ATTEMPTS = ((1200, 82), (1200, 70), (900, 68), (700, 62))

#: Qualidade JPEG das variantes. Não precisam de escada: a 640px um JPEG q80 fica em ~40-90 KB.
_QUALIDADE_VARIANTE = 80

#: Larguras públicas de variante (feature 270). **Allowlist fechada de propósito**: sem ela,
#: `/t/<qualquer número>/` é um gerador de trabalho arbitrário — um laço de `curl` enche o disco
#: de 10 GB com milhares de tamanhos. 128 = tira de miniaturas (64px em retina); 320 = card da
#: grade em celular pequeno (2 colunas, ≤384px); 480 = card em celular de 390–430px com DPR 2 (o
#: navegador escolhe a MENOR variante ≥ `sizes × dpr`, e 156px × 2 já passa de 320 em quase todo
#: aparelho atual — sem o 480 ele pulava direto para o 640); 640 = card no desktop (~270px em retina).
LARGURAS_PERMITIDAS = (128, 320, 480, 640)

#: Subpastas de ``UPLOAD_FOLDER``: origens e caches. As variantes ficam numa pasta POR LARGURA
#: dentro da pasta de cache — a limpeza de um tamanho aposentado é um `rm -r` só.
MEDIA_SUBFOLDER = "catalog_photos"
CACHE_SUBFOLDER = "catalog_og"
THUMBS_SUBFOLDER = "catalog_thumbs"
TALENT_MEDIA_SUBFOLDER = "talent_photos"
TALENT_THUMBS_SUBFOLDER = "talent_thumbs"

#: Prefixos de URL que têm variante. `assetUrl(path, { largura })` no frontend aplica a MESMA
#: regra (`@manto/api-client`): os dois lados precisam concordar sobre quem tem miniatura.
_PREFIXO_CATALOGO = "/catalogo/midia/"
_PREFIXO_TALENTO = f"/uploads/{TALENT_MEDIA_SUBFOLDER}/"

#: O nome do cache é ``{digest}_{largura}x{altura}.jpg``. As dimensões moram no NOME porque
#: `og:image:width`/`og:image:height` são pedidas a cada prévia, e reabrir o JPEG só para medi-lo
#: custaria um decode por acesso.
_CACHE_NAME_RE = re.compile(r"_(\d+)x(\d+)\.jpg$")


class Thumbnail(NamedTuple):
    """Miniatura pronta em disco: caminho do arquivo e dimensões reais do JPEG."""

    path: str
    width: int
    height: int


class Receita(NamedTuple):
    """Como reencodar: entra na chave de cache, então mudar a receita invalida o disco sozinho.

    Attributes:
        chave: Prefixo do digest. A prévia usa ``"1"`` (o ``_RECIPE_VERSION`` histórico) para não
            invalidar o cache que já existe em produção; as variantes usam ``"t<largura>"``.
        tentativas: Pares ``(tamanho, qualidade)`` em ordem; a primeira que couber em
            ``max_bytes`` vence. Com ``max_bytes=None`` só a primeira roda.
        max_bytes: Teto de bytes, ou ``None`` para não impor teto.
        por_largura: ``True`` redimensiona para que a LARGURA seja ``tamanho`` (card de grade);
            ``False`` limita o LADO MAIOR (prévia de link, que é um quadrado).
    """

    chave: str
    tentativas: tuple[tuple[int, int], ...]
    max_bytes: int | None
    por_largura: bool


#: Receita da prévia Open Graph — inalterada desde a feature 209 (a chave "1" preserva o cache).
RECEITA_OG = Receita("1", _ATTEMPTS, _MAX_BYTES, False)


def receita_variante(largura: int) -> Receita:
    """Receita da variante de uma largura da allowlist.

    Raises:
        ValueError: largura fora de ``LARGURAS_PERMITIDAS`` — quem chama deve ter filtrado antes
            (a rota responde 404); aqui é a última linha de defesa.
    """
    if largura not in LARGURAS_PERMITIDAS:
        raise ValueError(f"largura de variante não permitida: {largura}")
    return Receita(f"t{largura}", ((largura, _QUALIDADE_VARIANTE),), None, True)


def cache_digest(source_url: str, receita: Receita = RECEITA_OG) -> str:
    """Prefixo do arquivo de cache — troca sozinho quando a imagem de origem ou a receita muda."""
    return hashlib.md5(f"{receita.chave}|{source_url}".encode()).hexdigest()


def find_cached(source_url: str, cache_folder: str, receita: Receita = RECEITA_OG) -> Thumbnail | None:
    """Miniatura já gerada para esta origem, lendo as dimensões do nome do arquivo.

    Args:
        source_url: URL de origem (``CatalogItemImage.url``, ``Talent.photo_face_path``...).
        cache_folder: Pasta em disco onde as miniaturas desta receita são gravadas.
        receita: Receita usada na geração — entra no digest.

    Returns:
        A miniatura em cache, ou ``None`` quando ainda não foi gerada.
    """
    padrao = os.path.join(cache_folder, f"{cache_digest(source_url, receita)}_*.jpg")
    for path in glob.glob(padrao):
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
    """Lê os bytes da origem, seja arquivo local (`/catalogo/midia/...`) ou objeto remoto (S3/R2)."""
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
        logger.warning("og: origem local ausente %s: %s", path, exc)
        return None


def _decode_opaque(raw: bytes, source_url: str) -> Any:
    """Abre os bytes como imagem RGB opaca (nem a prévia nem o JPEG suportam transparência).

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
        logger.warning("og: falha ao decodificar %s: %s", source_url, exc)
        return None


def _redimensionar(frame: Any, tamanho: int, por_largura: bool) -> Any:
    """Reduz ``frame`` sem nunca ampliar: pela largura (variante) ou pelo lado maior (prévia)."""
    from PIL import Image

    if por_largura:
        if frame.width > tamanho:
            altura = max(1, round(frame.height * tamanho / frame.width))
            return frame.resize((tamanho, altura), Image.LANCZOS)
        return frame
    if max(frame.width, frame.height) > tamanho:
        frame.thumbnail((tamanho, tamanho), Image.LANCZOS)
    return frame


def build_thumbnail(
    source_url: str, media_folder: str, receita: Receita = RECEITA_OG
) -> tuple[bytes, int, int] | None:
    """Gera o JPEG reencodado da origem, ou ``None`` se a imagem não puder ser lida/decodificada.

    Args:
        source_url: URL de origem — caminho local ou URL absoluta (S3/R2, só na prévia).
        media_folder: Pasta em disco das imagens de origem.
        receita: Tentativas, teto e modo de redimensionamento.

    Returns:
        ``(bytes, largura, altura)`` do JPEG, ou ``None`` para quem chama devolver 404. As
        dimensões saem daqui porque só este ponto sabe qual das tentativas venceu.
    """
    raw = _read_source(source_url, media_folder)
    if not raw:
        return None
    img = _decode_opaque(raw, source_url)
    if img is None:
        return None

    encoded, size = b"", (img.width, img.height)
    for tamanho, qualidade in receita.tentativas:
        frame = _redimensionar(img.copy(), tamanho, receita.por_largura)
        buffer = io.BytesIO()
        frame.save(buffer, format="JPEG", quality=qualidade, optimize=True, progressive=True)
        encoded, size = buffer.getvalue(), (frame.width, frame.height)
        if receita.max_bytes is None or len(encoded) <= receita.max_bytes:
            break

    # Nenhuma tentativa coube: devolve a menor (última) mesmo assim — prévia grande é melhor
    # que prévia nenhuma, e o teto é heurístico.
    return (encoded, size[0], size[1]) if encoded else None


def cached_thumbnail(
    source_url: str, media_folder: str, cache_folder: str, receita: Receita = RECEITA_OG
) -> Thumbnail | None:
    """Miniatura em disco, gerando-a na primeira chamada.

    Returns:
        A miniatura pronta para `send_file`, ou ``None`` se a origem não pôde ser lida.
    """
    existing = find_cached(source_url, cache_folder, receita)
    if existing:
        return existing

    built = build_thumbnail(source_url, media_folder, receita)
    if not built:
        return None
    data, width, height = built

    path = os.path.join(cache_folder, f"{cache_digest(source_url, receita)}_{width}x{height}.jpg")
    os.makedirs(cache_folder, exist_ok=True)
    # Escrita atômica: dois requests simultâneos do mesmo link não podem servir arquivo pela metade.
    # O temporário precisa ser único POR THREAD, não por processo: até a 270 o nome era
    # `{path}.{pid}.tmp`, e as 12 threads de um worker do gunicorn compartilham o PID — oito
    # requisições da mesma variante escreviam o mesmo `.tmp`, e uma delas servia bytes pela
    # metade (o verify_270 reproduziu). `mkstemp` gera um nome novo por chamada, na mesma pasta,
    # então o `os.replace` continua sendo um rename atômico dentro do mesmo sistema de arquivos.
    fd, temp = tempfile.mkstemp(prefix=f"{os.path.basename(path)}.", suffix=".tmp", dir=cache_folder)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except OSError as exc:
        try:
            os.remove(temp)
        except OSError:
            pass
        # Perder a corrida não é falha: se outra thread já publicou o arquivo final (no Windows o
        # `replace` recusa sobrescrever um destino aberto para leitura), serve-se o dela.
        vencedor = find_cached(source_url, cache_folder, receita)
        if vencedor:
            return vencedor
        logger.warning("og: falha ao gravar cache %s: %s", path, exc)
        return None
    return Thumbnail(path, width, height)


def resolve_thumbnail(source_url: str | None, uploads_folder: str) -> Thumbnail | None:
    """Miniatura de prévia de link (Open Graph) de uma capa, a partir da raiz de uploads do app.

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


def pastas_da_variante(source_url: str, uploads_folder: str) -> tuple[str, str] | None:
    """Pasta de origem e pasta-raiz de cache para a URL, ou ``None`` se ela não tem variante.

    Só duas famílias têm miniatura (decisões 6 e 7 da spec): fotos do catálogo e fotos de rosto/
    corpo de talento. URL absoluta (legado do Drive, feature 154) não entra — a variante nunca
    baixa de fora, e o `assetUrl` do frontend também a deixa passar intacta. A foto de documento
    (`talent_docs`) fica de fora de propósito: é identidade civil, e cópias reduzidas espalham PII
    por mais um lugar no disco sem ninguém precisar delas.
    """
    if source_url.startswith(_PREFIXO_CATALOGO):
        resto = source_url[len(_PREFIXO_CATALOGO):]
        if "/" in resto or not resto:
            return None
        return (
            os.path.join(uploads_folder, MEDIA_SUBFOLDER),
            os.path.join(uploads_folder, THUMBS_SUBFOLDER),
        )
    if source_url.startswith(_PREFIXO_TALENTO):
        resto = source_url[len(_PREFIXO_TALENTO):]
        if "/" in resto or not resto:
            return None
        return (
            os.path.join(uploads_folder, TALENT_MEDIA_SUBFOLDER),
            os.path.join(uploads_folder, TALENT_THUMBS_SUBFOLDER),
        )
    return None


def resolve_variante(source_url: str | None, largura: int, uploads_folder: str) -> Thumbnail | None:
    """Variante de ``largura`` px de uma imagem local, gerada sob demanda e cacheada em disco.

    Args:
        source_url: URL pública da imagem (`/catalogo/midia/<arquivo>` ou
            `/uploads/talent_photos/<arquivo>`).
        largura: Uma das ``LARGURAS_PERMITIDAS``.
        uploads_folder: `UPLOAD_FOLDER` do app.

    Returns:
        A miniatura, ou ``None`` quando a largura não é permitida, a URL não tem variante ou o
        arquivo de origem não existe/não decodifica — em todos os casos a rota responde 404 e
        **nada é gravado no cache**.
    """
    if not source_url or largura not in LARGURAS_PERMITIDAS:
        return None
    pastas = pastas_da_variante(source_url, uploads_folder)
    if pastas is None:
        return None
    media_folder, cache_root = pastas
    return cached_thumbnail(
        source_url,
        media_folder=media_folder,
        cache_folder=os.path.join(cache_root, str(largura)),
        receita=receita_variante(largura),
    )


def variante_em_cache(source_url: str, largura: int, uploads_folder: str) -> Thumbnail | None:
    """Só consulta o cache da variante, sem gerar — para o pré-aquecimento contar o que já existe."""
    pastas = pastas_da_variante(source_url, uploads_folder)
    if pastas is None or largura not in LARGURAS_PERMITIDAS:
        return None
    return find_cached(
        source_url, os.path.join(pastas[1], str(largura)), receita_variante(largura)
    )
