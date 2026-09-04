"""
Camada de abstração para armazenamento de arquivos.

Modos de operação (controlado por variáveis de ambiente):

  USE_S3=false  → salva em instance/uploads/ (desenvolvimento local)
  USE_S3=true   → envia para S3-compatível (AWS S3 ou Cloudflare R2)

Para Cloudflare R2, defina também:
  S3_ENDPOINT_URL  = https://<account_id>.r2.cloudflarestorage.com
  S3_PUBLIC_URL    = https://pub-<id>.r2.dev  (ou domínio customizado)
  S3_BUCKET        = nome-do-bucket
  AWS_ACCESS_KEY_ID     = R2 Access Key ID
  AWS_SECRET_ACCESS_KEY = R2 Secret Access Key
"""
import io
import logging
import os
import shutil
import uuid as _uuid
from typing import BinaryIO

from flask import current_app

from app import imaging

logger = logging.getLogger(__name__)

# As constantes de compressão vivem logo abaixo da allowlist de extensões: `COMPRESS_EXTS` é
# DERIVADO dela, e não uma segunda lista escrita à mão (ver o comentário lá embaixo).
MAX_PX = 1200   # lado máximo em pixels
QUALITY = 85    # qualidade JPEG (0-100)

# ── Allowlist de extensões aceitas em upload ─────────────────────────────────
# Fonte única de "o que pode subir". Todo arquivo enviado por usuário cai em
# `instance/uploads/` e é devolvido por `/uploads/<path>`, que é o MESMO ORIGIN das SPAs:
# um `.html`/`.svg` aceito aqui vira XSS armazenado — o JavaScript dele roda com a sessão de
# quem abrir o link (inclusive superadmin). Por isso a checagem é sempre por EXTENSÃO e nunca
# pelo `Content-Type` do multipart, que é escolhido pelo cliente. As listas são separadas por
# finalidade para não afrouxar um caminho por causa do outro (foto de talento não precisa
# aceitar vídeo; material de ensaio precisa).

#: Imagens exibidas na interface (foto de talento, figurino, observação de evento).
#: `.heic`/`.heif` entram porque é o formato nativo da câmera do iPhone — em campo de upload
#: sem `accept`, o Safari envia o arquivo original, e recusá-lo bloquearia foto legítima de
#: comprovante. Nenhum dos dois é executável pelo browser.
#: `.bmp`/`.tif`/`.avif` entram pelo mesmo motivo: as telas de gasto e de observação anunciam
#: `accept="image/*"`, então recusá-los rejeitaria comprovante legítimo. Nenhum é executável.
ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".bmp", ".tif", ".tiff", ".avif"}
)

#: Extensões que passam por compressão automática. **Derivado**, nunca uma segunda lista: por
#: quatro meses `.heic` esteve na allowlist acima e fora da lista de compressão escrita à mão, de
#: modo que toda foto de iPhone era gravada crua — e o navegador não abre HEIC. Com a derivação,
#: acrescentar um formato ali passa a trazer a compressão junto. GIF fica de fora (pode ser
#: animado, e o Pillow salvaria só o primeiro quadro).
COMPRESS_EXTS: frozenset[str] = ALLOWED_IMAGE_EXTENSIONS - {".gif"}

#: Documentos comprobatórios: foto do papel ou PDF (contrato, comprovante).
ALLOWED_DOCUMENT_EXTENSIONS: frozenset[str] = ALLOWED_IMAGE_EXTENSIONS | {".pdf"}

#: Nota fiscal: documento **mais** `.xml`, que é o formato oficial da NF-e e o que as telas de
#: nota já oferecem (`accept=".pdf,.xml,..."` em event_detail.html e financeiro/dashboard.html).
#: Fica numa lista própria porque `.xml` só é seguro por ser servido como anexo — ele não entra
#: em `INLINE_SAFE_EXTENSIONS`, senão viraria XSS armazenado ao ser navegado direto.
ALLOWED_INVOICE_EXTENSIONS: frozenset[str] = ALLOWED_DOCUMENT_EXTENSIONS | {".xml"}

#: Áudio e vídeo (Revisão de Mídia e materiais de ensaio). Espelha `_MEDIA_EXTS` da Revisão.
ALLOWED_AV_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".mov", ".webm", ".m4v", ".ogv",
    ".mp3", ".wav", ".m4a", ".ogg", ".aac",
})

#: Material de apoio de ensaio: documento, mídia, planilha/roteiro ou pacote compactado.
ALLOWED_MATERIAL_EXTENSIONS: frozenset[str] = (
    ALLOWED_DOCUMENT_EXTENSIONS
    | ALLOWED_AV_EXTENSIONS
    | {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".zip"}
)

#: Extensões que podem ser servidas INLINE sem risco de execução no origin da aplicação.
#: Tudo fora daqui (inclusive `.svg`, que é XML executável quando navegado direto) sai como
#: anexo — ver `is_inline_safe`.
INLINE_SAFE_EXTENSIONS: frozenset[str] = (
    ALLOWED_IMAGE_EXTENSIONS | ALLOWED_AV_EXTENSIONS | {".pdf"}
)


def extension_of(filename: str | None) -> str:
    """Extensão em minúsculas (com ponto) de um nome de arquivo.

    Args:
        filename: Nome ou caminho do arquivo (pode vir vazio/None).

    Returns:
        A extensão normalizada (ex.: ``".pdf"``) ou ``""`` quando não há extensão.
    """
    return os.path.splitext((filename or "").split("?")[0])[1].lower()


def is_allowed_extension(filename: str | None, allowed: frozenset[str]) -> bool:
    """Diz se o arquivo pode ser aceito no upload, comparando contra uma allowlist.

    Args:
        filename: Nome do arquivo enviado pelo cliente.
        allowed: Uma das constantes ``ALLOWED_*_EXTENSIONS`` deste módulo.

    Returns:
        `True` se a extensão está na allowlist.
    """
    return extension_of(filename) in allowed


def formatos_aceitos(allowed: frozenset[str]) -> str:
    """Lista legível de extensões para uma mensagem de erro ("JPG, PNG ou WEBP").

    Existe para a mensagem acompanhar a allowlist sozinha: por muito tempo três telas diziam
    "Use JPG, PNG ou WEBP" com a lista escrita à mão no texto, e continuaram dizendo isso depois
    que a allowlist mudou.
    """
    nomes = sorted({e.lstrip(".").upper() for e in allowed})
    if len(nomes) == 1:
        return nomes[0]
    return ", ".join(nomes[:-1]) + " ou " + nomes[-1]


def is_inline_safe(filename: str | None) -> bool:
    """Diz se o arquivo pode ser servido inline (sem `Content-Disposition: attachment`).

    Args:
        filename: Nome ou caminho do arquivo salvo.

    Returns:
        `True` para imagem, PDF, áudio e vídeo conhecidos; `False` para todo o resto —
        inclusive arquivos legados que já estavam no disco antes da allowlist existir.
    """
    return extension_of(filename) in INLINE_SAFE_EXTENSIONS


class ImagemNaoConvertida(Exception):
    """A imagem precisava ser convertida para ser exibível e a conversão falhou.

    Só nasce para as extensões de `imaging.EXTS_QUE_EXIGEM_CONVERSAO` (HEIC de iPhone, TIFF, AVIF,
    BMP): guardar o original desses formatos é guardar um arquivo que nenhum navegador abre — a
    foto "some" da tela sem erro nenhum, e só reaparece num inventário meses depois. Para JPEG e
    PNG a falha continua silenciosa de propósito: lá a compressão é otimização e o original já é
    exibível.
    """


def comprimir_bytes(
    dados: bytes,
    ext: str,
    *,
    manter_formato: bool = False,
    pular_se_pequena: int = 0,
) -> tuple[bytes, str] | None:
    """Reduz uma imagem para `MAX_PX`/`QUALITY` e devolve `(bytes, extensão)`.

    Args:
        dados: Bytes da imagem original.
        ext: Extensão do arquivo de origem (com ponto, minúscula).
        manter_formato: Preserva a extensão de entrada em vez de converter para `.jpg`. É o que o
            `flask compress-images` precisa: lá a URL já está gravada no banco, e mudar a extensão
            quebraria toda referência existente.
        pular_se_pequena: Se maior que zero, devolve ``None`` quando a imagem já cabe em `MAX_PX`
            **e** pesa menos que este número de bytes — reprocessar não ganharia nada.

    Returns:
        `(bytes, extensão)`, ou ``None`` quando não há nada a fazer (extensão fora de
        `COMPRESS_EXTS`, imagem já pequena, ou falha de decodificação).

    Raises:
        ImagemNaoConvertida: A extensão exige conversão e a imagem não pôde ser decodificada.
    """
    if ext not in COMPRESS_EXTS:
        return None

    img = imaging.abrir(dados)
    if img is None:
        if ext in imaging.EXTS_QUE_EXIGEM_CONVERSAO:
            raise ImagemNaoConvertida(ext)
        logger.warning("compressão de imagem falhou; mantendo original (%s)", ext)
        return None

    try:
        precisa_reduzir = max(img.width, img.height) > MAX_PX
        if not precisa_reduzir and pular_se_pequena and len(dados) < pular_se_pequena:
            return None
        if precisa_reduzir:
            from PIL import Image

            img.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)

        out = io.BytesIO()
        # PNG com transparência REAL continua PNG: virar JPEG pintaria o fundo de branco.
        if imaging.tem_transparencia_real(img):
            img.save(out, format="PNG", optimize=True)
            return out.getvalue(), ".png"

        if manter_formato and ext in (".png", ".webp"):
            formato = "PNG" if ext == ".png" else "WEBP"
            img.save(out, format=formato, optimize=True, quality=QUALITY)
            return out.getvalue(), ext

        imaging.para_rgb(img).save(out, format="JPEG", quality=QUALITY, optimize=True)
        return out.getvalue(), ext if manter_formato and ext in (".jpg", ".jpeg") else ".jpg"
    except Exception as exc:  # noqa: BLE001
        if ext in imaging.EXTS_QUE_EXIGEM_CONVERSAO:
            raise ImagemNaoConvertida(ext) from exc
        logger.warning("compressão de imagem falhou; salvando original: %s", exc)
        return None


def _compress_image(file_obj: BinaryIO, ext: str) -> tuple[io.BytesIO, str] | None:
    """Redimensiona e comprime um upload. Retorna `(BytesIO, extensão)` ou `None`.

    Raises:
        ImagemNaoConvertida: formato que o navegador não abre e que não pôde ser convertido.
    """
    file_obj.seek(0)
    resultado = comprimir_bytes(file_obj.read(), ext)
    file_obj.seek(0)
    if resultado is None:
        return None
    dados, nova_ext = resultado
    return io.BytesIO(dados), nova_ext


def caminho_local(url_publica: str | None) -> str | None:
    """URL pública de um arquivo servido pelo Flask -> caminho absoluto em disco.

    Inverso de `save_file`. Cobre as duas formas que o banco guarda: `/uploads/<sub>/<arq>` e a
    reescrita pública do catálogo (`/catalogo/midia/<arq>`, que mora em `catalog_photos/`).

    Returns:
        O caminho absoluto, ou ``None`` para URL externa (legado do Drive), vazia, ou quando o
        armazenamento é S3 — em nenhum desses casos existe arquivo local para apontar.
    """
    if not url_publica or url_publica.startswith(("http://", "https://")):
        return None
    if current_app.config.get("USE_S3"):
        return None
    rel = url_publica.lstrip("/")
    # A capa de campanha é servida pela mesma rota pública do catálogo, mas mora em outra pasta.
    if rel.startswith("catalogo/midia/campanhas/"):
        rel = "virtual_covers/" + rel.rsplit("/", 1)[-1]
    elif rel.startswith("catalogo/midia/"):
        rel = "catalog_photos/" + rel[len("catalogo/midia/"):]
    elif rel.startswith("uploads/"):
        rel = rel[len("uploads/"):]
    return os.path.join(current_app.config["UPLOAD_FOLDER"], rel)


def save_bytes(dados: bytes, subfolder: str, ext: str) -> str:
    """Grava bytes já prontos sob um nome novo e devolve a URL pública.

    Existe para quem já tem a imagem em memória e **precisa de um caminho novo**: girar a foto de
    um figurino regravando por cima deixaria a variante em cache (chaveada pela URL) e o cache do
    navegador (`immutable`, um ano) presos na orientação antiga.
    """
    return save_file(io.BytesIO(dados), subfolder, f"{_uuid.uuid4().hex}{ext}")


def save_file(file_obj: BinaryIO, subfolder: str, filename: str | None = None) -> str:
    """Salva um arquivo (com compressão automática para imagens) e retorna a URL acessível.

    Args:
        file_obj:  Objeto de arquivo do Flask (werkzeug.FileStorage).
        subfolder: Pasta dentro do bucket/uploads (ex: "talent_photos").
        filename:  Nome do arquivo. Se None, gera UUID automaticamente.

    Returns:
        URL completa para acessar o arquivo.
    """
    raw_name = getattr(file_obj, "filename", None) or ""
    ext = os.path.splitext(raw_name)[1].lower()

    compressed = _compress_image(file_obj, ext)
    if compressed is not None:
        actual, new_ext = compressed
        if filename:
            filename = os.path.splitext(filename)[0] + new_ext
        else:
            filename = f"{_uuid.uuid4().hex}{new_ext}"
    else:
        actual = file_obj
        actual.seek(0)
        if not filename:
            filename = f"{_uuid.uuid4().hex}{ext}"

    if current_app.config.get("USE_S3"):
        return _save_to_object_storage(actual, subfolder, filename)
    return _save_local(actual, subfolder, filename)


def delete_file(url_or_path: str | None) -> None:
    """Deleta um arquivo do object storage ou do disco local."""
    if not url_or_path:
        return
    if url_or_path.startswith(("http://", "https://")):
        _delete_from_object_storage(url_or_path)
    else:
        _delete_local(url_or_path)


def copy_file(url_or_path: str, subfolder: str) -> str | None:
    """Copia um arquivo já salvo para `subfolder`, devolvendo a nova URL.

    Usado quando dois registros precisam da MESMA imagem (ex.: foto da galeria do catálogo
    adotada como foto de personagem): referenciar a mesma URL quebraria no delete — os
    fluxos de remoção chamam `delete_file` sem saber que a URL é compartilhada, e em S3 o
    objeto sumiria para o outro registro. A cópia mantém todos os deletes existentes válidos.

    Sem re-compressão: a origem já passou por `save_file` no upload original.

    Returns:
        A nova URL (`/uploads/<subfolder>/<uuid>.<ext>` local, ou URL absoluta em S3), ou
        `None` quando a origem não pôde ser resolvida/copiada.
    """
    if not url_or_path:
        return None
    ext = os.path.splitext(url_or_path.split("?")[0])[1].lower() or ".jpg"
    new_name = f"{_uuid.uuid4().hex}{ext}"

    if url_or_path.startswith(("http://", "https://")):
        return _copy_in_object_storage(url_or_path, subfolder, new_name)

    # Local: resolve o arquivo físico. URLs `/catalogo/midia/<arq>` são reescrita pública de
    # `catalog_photos` (app/catalogo/importer.py:_rewrite_public_url); `/uploads/<sub>/<arq>`
    # mapeia direto para UPLOAD_FOLDER.
    rel = url_or_path.lstrip("/")
    if rel.startswith("catalogo/midia/"):
        rel = "catalog_photos/" + rel[len("catalogo/midia/"):]
    elif rel.startswith("uploads/"):
        rel = rel[len("uploads/"):]
    source = os.path.join(current_app.config["UPLOAD_FOLDER"], rel)
    if not os.path.exists(source):
        logger.warning("copy_file: origem não encontrada: %s", url_or_path)
        return None

    dest_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copyfile(source, os.path.join(dest_dir, new_name))
    return f"/uploads/{subfolder}/{new_name}"


def _copy_in_object_storage(url: str, subfolder: str, new_name: str) -> str | None:
    """`copy_object` dentro do bucket — mesmo parsing de key do `_delete_from_object_storage`."""
    cfg = current_app.config
    bucket = cfg["S3_BUCKET"]
    public_url = cfg.get("S3_PUBLIC_URL", "").rstrip("/")
    endpoint = cfg.get("S3_ENDPOINT_URL", "")
    region = cfg.get("S3_REGION", "us-east-1")

    prefixes = [p for p in [public_url, f"{endpoint}/{bucket}",
                            f"https://{bucket}.s3.{region}.amazonaws.com"] if p]
    key = None
    for prefix in prefixes:
        if url.startswith(prefix + "/"):
            key = url[len(prefix) + 1:]
            break
    if not key:
        logger.warning("copy_file: URL fora do bucket configurado: %s", url)
        return None

    new_key = f"{subfolder}/{new_name}"
    try:
        _get_s3_client().copy_object(
            Bucket=bucket, Key=new_key, CopySource={"Bucket": bucket, "Key": key}
        )
    except Exception as exc:  # noqa: BLE001 — falha de cópia não pode derrubar o request
        logger.warning("copy_file: falha ao copiar objeto S3 %s: %s", key, exc)
        return None

    if public_url:
        return f"{public_url}/{new_key}"
    if endpoint:
        return f"{endpoint}/{bucket}/{new_key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{new_key}"


# ── Local ────────────────────────────────────────────────────────────────────

def _save_local(file_obj: BinaryIO, subfolder: str, filename: str) -> str:
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file_obj.seek(0)
    with open(os.path.join(upload_dir, filename), "wb") as f:
        shutil.copyfileobj(file_obj, f)
    return f"/uploads/{subfolder}/{filename}"


def _delete_local(url_path: str) -> None:
    rel = url_path.lstrip("/")
    if rel.startswith("uploads/"):
        rel = rel[len("uploads/"):]
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], rel)
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
    except OSError:
        pass


# ── Object Storage (AWS S3 ou Cloudflare R2) ─────────────────────────────────

def _get_s3_client():
    """Cria cliente boto3 configurado para S3 ou R2."""
    import boto3

    cfg = current_app.config
    kwargs = dict(
        region_name=cfg.get("S3_REGION", "auto"),
        aws_access_key_id=cfg.get("AWS_ACCESS_KEY"),
        aws_secret_access_key=cfg.get("AWS_SECRET_KEY"),
    )
    endpoint = cfg.get("S3_ENDPOINT_URL", "")
    if endpoint:
        kwargs["endpoint_url"] = endpoint

    return boto3.client("s3", **kwargs)


def _save_to_object_storage(file_obj: BinaryIO, subfolder: str, filename: str) -> str:
    cfg = current_app.config
    bucket     = cfg["S3_BUCKET"]
    key        = f"{subfolder}/{filename}"
    public_url = cfg.get("S3_PUBLIC_URL", "").rstrip("/")
    endpoint   = cfg.get("S3_ENDPOINT_URL", "")
    region     = cfg.get("S3_REGION", "us-east-1")

    extra_args = {"ContentType": _guess_content_type(filename)}
    # ACL public-read só existe no AWS S3; R2 usa acesso público pelo bucket
    if not endpoint:
        extra_args["ACL"] = "public-read"

    s3 = _get_s3_client()
    file_obj.seek(0)
    s3.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)

    # Monta URL pública
    if public_url:
        return f"{public_url}/{key}"
    if endpoint:
        return f"{endpoint}/{bucket}/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _delete_from_object_storage(url: str) -> None:
    cfg        = current_app.config
    bucket     = cfg["S3_BUCKET"]
    public_url = cfg.get("S3_PUBLIC_URL", "").rstrip("/")
    endpoint   = cfg.get("S3_ENDPOINT_URL", "")
    region     = cfg.get("S3_REGION", "us-east-1")

    # Deduz o key a partir da URL pública
    prefixes = [p for p in [public_url, f"{endpoint}/{bucket}",
                             f"https://{bucket}.s3.{region}.amazonaws.com"] if p]
    key = None
    for prefix in prefixes:
        if url.startswith(prefix + "/"):
            key = url[len(prefix) + 1:]
            break

    if not key:
        return

    try:
        _get_s3_client().delete_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 — objeto órfão no S3 não pode travar o fluxo
        logger.warning("falha ao remover objeto S3 %s: %s", key, exc)


def _guess_content_type(filename: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp",
        ".gif": "image/gif",  ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }.get(os.path.splitext(filename)[1].lower(), "application/octet-stream")
