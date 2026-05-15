"""Comandos Flask CLI para operações de manutenção."""
import io
import os


def register_commands(app):
    @app.cli.command("compress-images")
    def compress_images():
        """Comprime todas as imagens existentes no servidor mantendo os mesmos URLs."""
        import click
        from PIL import Image, ImageOps
        from app.models import Talent, FigurinoSheet, User
        from app import db

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
            except Exception as e:
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
