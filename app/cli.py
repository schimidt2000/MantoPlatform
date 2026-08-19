"""Comandos Flask CLI para operações de manutenção."""
import io
import logging
import os

import click

logger = logging.getLogger(__name__)


def register_commands(app):
    @app.cli.command("cleanup-review-files")
    def cleanup_review_files():
        """Remove os arquivos de revisão vencidos (mantém registro e comentários) — feature 090."""
        from app.revisao.cleanup import cleanup_expired_review_files
        removed = cleanup_expired_review_files()
        click.echo(f"Arquivos de revisão removidos: {removed}")

    @app.cli.command("import-kommo-clients")
    @click.argument("path", default="kommo_export_leads_2026-06-29.csv")
    def import_kommo_clients(path):
        """Importa a base de clientes do CSV do Kommo (dedup por telefone) — feature 094."""
        from app.clientes.importer import import_kommo_csv
        report = import_kommo_csv(path)
        click.echo(f"Importação do Kommo concluída: {report}")

    @app.cli.command("import-wordpress-catalog")
    @click.argument(
        "path",
        default="Produtos Catalogo/wc-product-export-16-7-2026-1784216390934.csv",
    )
    @click.option("--limit", type=int, default=0, help="Importa no máximo N produtos (0 = todos).")
    def import_wordpress_catalog(path, limit):
        """Importa o catálogo de personagens exportado do WordPress — feature 133."""
        from app.catalogo.importer import run_import
        report = run_import(path, limit=limit, echo=click.echo)
        click.echo(f"\n{'-'*60}")
        click.echo(f"  Processados          : {report['processed']}")
        click.echo(f"  Importados           : {report['imported']}")
        click.echo(f"  Não publicados       : {report['skipped_unpublished']}")
        click.echo(f"  Sem conteúdo         : {report['skipped_no_content']}")
        click.echo(f"  Já importados antes  : {report['skipped_duplicate']}")
        click.echo(f"  Sem nenhuma imagem   : {report['skipped_no_images']}")
        click.echo(f"  Imagens baixadas     : {report['images_downloaded']}")
        click.echo(f"  Imagens com falha    : {report['images_failed']}")
        if report["heavy_images"]:
            click.echo(f"  Imagens ainda pesadas (>300KB): {len(report['heavy_images'])}")
            for line in report["heavy_images"]:
                click.echo(f"    - {line}")
        click.echo(f"{'-'*60}\n")

    @app.cli.command("backfill-form-event-links")
    def backfill_form_event_links():
        """Tenta vincular automaticamente respostas de formulário antigas ainda sem
        evento (feature 126) — rodar uma vez após o deploy da feature."""
        from app.formularios.formularios_ops import retry_auto_link_pending
        linked = retry_auto_link_pending()
        click.echo(f"Respostas vinculadas automaticamente: {linked}")

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
            except Exception as exc:  # noqa: BLE001 — imagem corrompida: mantém original
                logger.warning("[migrate-drive] falha ao comprimir imagem: %s", exc)
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
        from app.drive_migration import TALENT_MEDIA_FIELDS, is_drive_url, run_drive_migration
        from app.models import Talent

        if dry_run:
            by_sub = {}
            for t in Talent.query.all():
                for field, subfolder in TALENT_MEDIA_FIELDS.items():
                    if is_drive_url(getattr(t, field)):
                        by_sub[subfolder] = by_sub.get(subfolder, 0) + 1
            total = sum(by_sub.values())
            click.echo(f"\n{'-'*60}")
            click.echo("  Migração Google Drive -> volume   (DRY-RUN)")
            click.echo(f"  Arquivos no Drive: {total}")
            for sub, n in sorted(by_sub.items()):
                click.echo(f"  {sub:>14}: {n}")
            click.echo(f"{'-'*60}\n")
            return

        result = run_drive_migration(limit=limit, echo=click.echo)
        click.echo(f"\n{'-'*60}")
        click.echo(f"  Migrados : {result['migrated']}")
        click.echo(f"  Erros    : {result['errors']}  (links mantidos para nova tentativa)")
        click.echo(f"  Restantes: {result['remaining']}")
        click.echo(f"{'-'*60}\n")
