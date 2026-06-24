"""Comandos Flask CLI para operações de manutenção."""
import io
import os
import re

import click

# Campos de mídia do Talent e a subpasta de destino no volume (feature 087).
_TALENT_MEDIA_FIELDS = {
    "photo_face_path": "talent_photos",
    "photo_full_path": "talent_photos",
    "doc_photo_path": "talent_docs",
    "cnh_file_path": "talent_docs",
}

# Extensão por Content-Type retornado no download.
_CT_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/pjpeg": ".jpg",
    "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
    "application/pdf": ".pdf",
}


def _is_drive_url(value: str | None) -> bool:
    """True se o valor é um link hospedado no Google Drive (foto lh3 ou documento drive.google)."""
    if not value or not value.startswith(("http://", "https://")):
        return False
    return "googleusercontent.com" in value or "drive.google.com" in value


def _drive_file_id(url: str) -> str | None:
    """Extrai o file_id de um link do Google Drive em qualquer formato conhecido.

    Suporta ``lh3.googleusercontent.com/d/<id>``, ``drive.google.com/open?id=<id>``,
    ``.../file/d/<id>/view`` e ``?id=<id>``.
    """
    for pat in (r"/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def register_commands(app):
    @app.cli.command("compress-images")
    def compress_images():
        """Comprime todas as imagens existentes no servidor mantendo os mesmos URLs."""
        import click
        from PIL import Image, ImageOps

        from app.models import FigurinoSheet, Talent, User

        USE_S3 = app.config.get("USE_S3", False)
        MAX_PX = 1200
        QUALITY = 85
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

        def _compress_bytes(data: bytes, ext: str) -> bytes | None:
            """Retorna bytes comprimidos ou None se não precisar/falhar."""
            if ext not in IMAGE_EXTS:
                return None
            try:
                img = Image.open(io.BytesIO(data))
                img = ImageOps.exif_transpose(img)

                needs_resize = max(img.width, img.height) > MAX_PX
                if not needs_resize and len(data) < 150 * 1024:
                    return None  # já está pequena o suficiente

                if needs_resize:
                    img.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)

                # PNG com transparência real → mantém PNG
                if img.mode == "RGBA":
                    alpha = img.getchannel("A")
                    if alpha.getextrema()[0] < 255:
                        out = io.BytesIO()
                        img.save(out, format="PNG", optimize=True)
                        return out.getvalue()

                if img.mode != "RGB":
                    img = img.convert("RGB")

                out = io.BytesIO()
                # Mantém formato original para não mudar extensão/URL
                fmt = "PNG" if ext == ".png" else "JPEG"
                if fmt == "JPEG":
                    img.save(out, format="JPEG", quality=QUALITY, optimize=True)
                else:
                    img.save(out, format="PNG", optimize=True)
                return out.getvalue()
            except Exception:
                return None

        def _compress_local(url: str) -> tuple[int, int] | None:
            """Comprime arquivo local. Retorna (bytes_antes, bytes_depois) ou None."""
            if not url or url.startswith(("http://", "https://")):
                return None
            ext = os.path.splitext(url)[1].lower()
            if ext not in IMAGE_EXTS:
                return None

            # /uploads/talent_photos/abc.jpg → instance/uploads/talent_photos/abc.jpg
            rel = url.lstrip("/")
            local_path = os.path.abspath(os.path.join("instance", rel))

            if not os.path.exists(local_path):
                return None

            with open(local_path, "rb") as f:
                original = f.read()

            compressed = _compress_bytes(original, ext)
            if compressed is None:
                return None

            with open(local_path, "wb") as f:
                f.write(compressed)

            return len(original), len(compressed)

        def _compress_s3(url: str) -> tuple[int, int] | None:
            """Comprime arquivo no S3/R2. Retorna (bytes_antes, bytes_depois) ou None."""
            if not url or not url.startswith(("http://", "https://")):
                return None
            # Pula URLs externas que não são do nosso storage
            public_url = app.config.get("S3_PUBLIC_URL", "").rstrip("/")
            endpoint   = app.config.get("S3_ENDPOINT_URL", "").rstrip("/")
            bucket     = app.config.get("S3_BUCKET", "")
            if not any(url.startswith(p) for p in [public_url, f"{endpoint}/{bucket}"] if p):
                return None

            ext = os.path.splitext(url)[1].lower()
            if ext not in IMAGE_EXTS:
                return None

            # Deduz a key do S3
            key = None
            for prefix in [public_url, f"{endpoint}/{bucket}"]:
                if prefix and url.startswith(prefix + "/"):
                    key = url[len(prefix) + 1:]
                    break
            if not key:
                return None

            try:
                import boto3
                s3 = boto3.client(
                    "s3",
                    region_name=app.config.get("S3_REGION", "auto"),
                    aws_access_key_id=app.config.get("AWS_ACCESS_KEY"),
                    aws_secret_access_key=app.config.get("AWS_SECRET_KEY"),
                    endpoint_url=app.config.get("S3_ENDPOINT_URL") or None,
                )
                buf = io.BytesIO()
                s3.download_fileobj(bucket, key, buf)
                original = buf.getvalue()

                compressed = _compress_bytes(original, ext)
                if compressed is None:
                    return None

                content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
                s3.put_object(Bucket=bucket, Key=key, Body=compressed, ContentType=content_type)
                return len(original), len(compressed)
            except Exception as e:
                click.echo(f"    Erro S3: {e}", err=True)
                return None

        compress_fn = _compress_s3 if USE_S3 else _compress_local

        # Coleta todas as imagens (campo, url)
        jobs = []
        for t in Talent.query.all():
            for url in [t.photo_face_path, t.photo_full_path, t.doc_photo_path]:
                if url:
                    jobs.append(url)
        for f in FigurinoSheet.query.all():
            url = f.photo_url
            if url and not url.startswith("https://lh3.google"):  # pula thumbnails do Drive
                jobs.append(url)
        for u in User.query.all():
            if u.profile_photo:
                jobs.append(u.profile_photo)

        # Remove duplicatas mantendo ordem
        seen = set()
        jobs = [j for j in jobs if not (j in seen or seen.add(j))]

        if not jobs:
            click.echo("Nenhuma imagem encontrada.")
            return

        total_before = 0
        total_after = 0
        compressed_count = 0
        skipped_count = 0
        error_count = 0

        click.echo(f"\n{'-'*60}")
        click.echo(f"  Comprimindo {len(jobs)} imagens  (max {MAX_PX}px, JPEG q{QUALITY})")
        click.echo(f"{'-'*60}")

        for i, url in enumerate(jobs, 1):
            label = url[-45:] if len(url) > 45 else url
            result = compress_fn(url)
            if result is None:
                skipped_count += 1
                click.echo(f"  [{i:>3}/{len(jobs)}] SKIP    {label}")
            else:
                before, after = result
                total_before += before
                total_after += after
                saved_pct = 100 - after * 100 // before if before else 0
                compressed_count += 1
                click.echo(
                    f"  [{i:>3}/{len(jobs)}] OK      {label}"
                    f"   {before/1024:.0f}KB -> {after/1024:.0f}KB  (-{saved_pct}%)"
                )

        click.echo(f"\n{'-'*60}")
        click.echo(f"  Comprimidas : {compressed_count}")
        click.echo(f"  Puladas     : {skipped_count}  (pequenas ou externas)")
        if total_before:
            saved_mb = (total_before - total_after) / 1024 / 1024
            click.echo(f"  Economia    : {total_before/1024/1024:.1f}MB -> {total_after/1024/1024:.1f}MB  ({saved_mb:.1f}MB liberados)")
        click.echo(f"{'-'*60}\n")

    @app.cli.command("migrate-drive-to-volume")
    @click.option("--dry-run", is_flag=True, help="Apenas conta o que seria migrado, sem baixar nem alterar.")
    @click.option("--limit", type=int, default=0, help="Migra no máximo N arquivos (0 = todos).")
    def migrate_drive_to_volume(dry_run, limit):
        """Baixa fotos/documentos de talentos do Google Drive e salva no volume (feature 087).

        Atualiza o link de cada campo de mídia para o armazenamento próprio. Idempotente (pula o que já
        está em /uploads/) e resiliente (falha em um item não derruba o processo).
        """
        import requests
        from werkzeug.datastructures import FileStorage

        from app import db
        from app.models import Talent
        from app.storage import save_file

        creds_path = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))
        # Estado da conta de serviço: None=não testada, True=tem acesso, False=sem acesso (pula daí pra frente)
        sa_state = {"svc": None, "ok": None}

        def _public_download(file_id: str, url: str) -> tuple[bytes, str] | None:
            """Tenta baixar pelo link público (lh3 para imagens; uc para arquivos compartilhados)."""
            for link in (
                f"https://lh3.googleusercontent.com/d/{file_id}=s0",
                f"https://drive.google.com/uc?export=download&id={file_id}",
            ):
                try:
                    resp = requests.get(link, timeout=30, allow_redirects=True)
                except requests.RequestException:
                    continue
                if resp.status_code != 200 or not resp.content:
                    continue
                ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if ct.startswith("text/html"):
                    continue  # página de erro/login/preview, não é o arquivo
                ext = _CT_EXT.get(ct) or (
                    os.path.splitext(url.split("?")[0])[1].lower()
                    if os.path.splitext(url.split("?")[0])[1].lower() in (".jpg", ".jpeg", ".png", ".webp", ".pdf")
                    else ".jpg"
                )
                return resp.content, ext
            return None

        def _sa_download(file_id: str) -> tuple[bytes, str] | None:
            """Baixa via API do Drive com a conta de serviço (funciona para qualquer tipo, se houver acesso)."""
            if sa_state["ok"] is False:
                return None
            try:
                if sa_state["svc"] is None:
                    from app.figurino.drive_service import get_drive_service
                    sa_state["svc"] = get_drive_service(creds_path)
                from googleapiclient.http import MediaIoBaseDownload
                svc = sa_state["svc"]
                meta = svc.files().get(fileId=file_id, fields="mimeType").execute()
                buf = io.BytesIO()
                dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=file_id))
                done = False
                while not done:
                    _, done = dl.next_chunk()
                sa_state["ok"] = True
                mime = (meta.get("mimeType") or "").lower()
                ext = _CT_EXT.get(mime) or (".pdf" if mime == "application/pdf" else ".jpg")
                return buf.getvalue(), ext
            except Exception:
                # Primeira falha (sem credenciais ou sem acesso) desliga a SA p/ o resto da execução.
                if sa_state["ok"] is None:
                    sa_state["ok"] = False
                return None

        def _download_drive(url: str) -> tuple[bytes, str] | None:
            """Baixa o arquivo do Drive: link público primeiro (imagens), conta de serviço como reserva."""
            file_id = _drive_file_id(url)
            if not file_id:
                return None
            return _public_download(file_id, url) or _sa_download(file_id)

        talents = Talent.query.order_by(Talent.id).all()
        # Levanta a fila (talent, campo, subpasta, url)
        jobs = []
        for t in talents:
            for field, subfolder in _TALENT_MEDIA_FIELDS.items():
                url = getattr(t, field)
                if _is_drive_url(url):
                    jobs.append((t, field, subfolder, url))

        click.echo(f"\n{'-'*60}")
        click.echo(f"  Migração Google Drive -> volume   ({'DRY-RUN' if dry_run else 'EXECUTANDO'})")
        click.echo(f"  Arquivos no Drive: {len(jobs)}  (de {len(talents)} talentos)")
        if limit:
            click.echo(f"  Limite desta execução: {limit}")
        click.echo(f"{'-'*60}")

        if dry_run:
            by_sub = {}
            for _, _, subfolder, _ in jobs:
                by_sub[subfolder] = by_sub.get(subfolder, 0) + 1
            for sub, n in sorted(by_sub.items()):
                click.echo(f"  {sub:>14}: {n}")
            click.echo(f"{'-'*60}\n")
            return

        migrated = 0
        errors = 0
        processed = 0
        for t, field, subfolder, url in jobs:
            if limit and processed >= limit:
                break
            processed += 1
            tag = f"#{t.id} {field}"
            try:
                downloaded = _download_drive(url)
                if downloaded is None:
                    errors += 1
                    click.echo(f"  [{processed:>4}] ERRO    {tag}  (download falhou)")
                    continue
                data, ext = downloaded
                fs = FileStorage(stream=io.BytesIO(data), filename=f"migrado{ext}")
                new_url = save_file(fs, subfolder)
                setattr(t, field, new_url)
                db.session.commit()
                migrated += 1
                click.echo(f"  [{processed:>4}] OK      {tag}  -> {new_url}")
            except Exception as e:  # noqa: BLE001 — falha de 1 item não pode derrubar a migração
                db.session.rollback()
                errors += 1
                click.echo(f"  [{processed:>4}] ERRO    {tag}  ({e})", err=True)

        click.echo(f"\n{'-'*60}")
        click.echo(f"  Migrados : {migrated}")
        click.echo(f"  Erros    : {errors}  (links mantidos para nova tentativa)")
        click.echo(f"  Restantes: {max(0, len(jobs) - processed)}")
        click.echo(f"{'-'*60}\n")
