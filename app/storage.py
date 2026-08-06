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

logger = logging.getLogger(__name__)

# Extensões que passam por compressão automática (GIF excluído — pode ser animado)
_COMPRESS_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_PX = 1200   # lado máximo em pixels
_QUALITY = 85    # qualidade JPEG (0-100)

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


def is_inline_safe(filename: str | None) -> bool:
    """Diz se o arquivo pode ser servido inline (sem `Content-Disposition: attachment`).

    Args:
        filename: Nome ou caminho do arquivo salvo.

    Returns:
        `True` para imagem, PDF, áudio e vídeo conhecidos; `False` para todo o resto —
        inclusive arquivos legados que já estavam no disco antes da allowlist existir.
    """
    return extension_of(filename) in INLINE_SAFE_EXTENSIONS


def _compress_image(file_obj: BinaryIO, ext: str) -> tuple[io.BytesIO, str] | None:
    """Redimensiona e comprime imagem. Retorna (BytesIO, extensão) ou None se não for imagem."""
    if ext not in _COMPRESS_EXTS:
        return None

    try:
        from PIL import Image, ImageOps

        file_obj.seek(0)
        img = Image.open(file_obj)

        # Corrige orientação EXIF (fotos de celular chegam rotacionadas)
        img = ImageOps.exif_transpose(img)

        # Redimensiona mantendo proporção
        if max(img.width, img.height) > _MAX_PX:
            img.thumbnail((_MAX_PX, _MAX_PX), Image.LANCZOS)

        # PNG com transparência real → mantém PNG comprimido
        if img.mode == "RGBA":
            alpha = img.getchannel("A")
            if alpha.getextrema()[0] < 255:
                out = io.BytesIO()
                img.save(out, format="PNG", optimize=True)
                out.seek(0)
                return out, ".png"

        # Tudo o mais → JPEG
        if img.mode not in ("RGB",):
            img = img.convert("RGB")

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=_QUALITY, optimize=True)
        out.seek(0)
        return out, ".jpg"

    except Exception as exc:  # noqa: BLE001 — compressão é otimização; original segue válido
        logger.warning("compressão de imagem falhou; salvando original: %s", exc)
        return None


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
