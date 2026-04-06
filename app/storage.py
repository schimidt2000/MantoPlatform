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
import os
import uuid as _uuid
from typing import BinaryIO

from flask import current_app


def save_file(file_obj: BinaryIO, subfolder: str, filename: str | None = None) -> str:
    """Salva um arquivo e retorna a URL acessível.

    Args:
        file_obj:  Objeto de arquivo do Flask (werkzeug.FileStorage).
        subfolder: Pasta dentro do bucket/uploads (ex: "talent_photos").
        filename:  Nome do arquivo. Se None, gera UUID automaticamente.

    Returns:
        URL completa para acessar o arquivo.
    """
    ext = os.path.splitext(file_obj.filename)[1].lower() if file_obj.filename else ""
    if not filename:
        filename = f"{_uuid.uuid4().hex}{ext}"

    if current_app.config.get("USE_S3"):
        return _save_to_object_storage(file_obj, subfolder, filename)
    return _save_local(file_obj, subfolder, filename)


def delete_file(url_or_path: str | None) -> None:
    """Deleta um arquivo do object storage ou do disco local."""
    if not url_or_path:
        return
    if url_or_path.startswith(("http://", "https://")):
        _delete_from_object_storage(url_or_path)
    else:
        _delete_local(url_or_path)


# ── Local ────────────────────────────────────────────────────────────────────

def _save_local(file_obj: BinaryIO, subfolder: str, filename: str) -> str:
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file_obj.seek(0)
    file_obj.save(os.path.join(upload_dir, filename))
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
    except Exception:
        pass


def _guess_content_type(filename: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp",
        ".gif": "image/gif",  ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }.get(os.path.splitext(filename)[1].lower(), "application/octet-stream")
