"""Comandos Flask CLI para operações de manutenção."""
import io
import logging
import os
import shutil

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
    @click.option("--execute", is_flag=True, help="grava de verdade (padrão: só mede)")
    @click.option("--sem-backup", is_flag=True, help="não guarda o original (só no modo local)")
    def compress_images(execute: bool, sem_backup: bool):
        """Comprime as imagens já gravadas, mantendo os mesmos URLs.

        Aplica retroativamente a MESMA regra dos uploads (`storage.save_file`: 1200px, JPEG q85)
        em quem entrou por fora dela. O caso que motivou a extensão (feature 268): a recuperação
        pós-Railway gravou as fotos do catálogo com `open(destino,"wb").write(r.content)`
        (`recuperacao/baixar_catalogo_wp.py:34`) — bytes crus do WordPress, sem passar por
        `save_file`. Medido em produção em 01/09/2026: mediana de 627 KB e picos de 4,3 MB contra
        as ~200 KB de quem passou pela regra.

        **Dry-run por padrão.** Sem `--execute` só mede e relata.
        """
        import click
        from PIL import Image, ImageOps

        from app import db
        from app.models import (
            CatalogCharacter,
            CatalogItemImage,
            FigurinoSheet,
            Talent,
            User,
        )

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

        def _caminho_local(url: str) -> str | None:
            """Traduz a URL pública no caminho em disco.

            A regra geral é `instance/<url>` — `/uploads/talent_photos/x.jpg` mora em
            `instance/uploads/talent_photos/x.jpg`. As fotos do catálogo são a exceção: a URL
            pública é `/catalogo/midia/<arquivo>` (rota que existe para NÃO exigir login), mas o
            arquivo mora em `uploads/catalog_photos/`. Sem esta tradução o comando resolvia para
            `instance/catalogo/midia/...`, que não existe, e PULAVA a vitrine inteira em silêncio
            — o motivo de o comando existir desde sempre e nunca ter tocado o catálogo.
            """
            if not url:
                return None
            base = app.config.get("UPLOAD_FOLDER") or os.path.join("instance", "uploads")
            if url.startswith("/catalogo/midia/campanhas/"):
                return os.path.abspath(
                    os.path.join(base, "virtual_covers", url.rsplit("/", 1)[-1])
                )
            if url.startswith("/catalogo/midia/"):
                return os.path.abspath(
                    os.path.join(base, "catalog_photos", url.rsplit("/", 1)[-1])
                )
            return os.path.abspath(os.path.join("instance", url.lstrip("/")))

        def _compress_local(url: str) -> tuple[int, int] | None:
            """Comprime arquivo local. Retorna (bytes_antes, bytes_depois) ou None."""
            if not url or url.startswith(("http://", "https://")):
                return None
            ext = os.path.splitext(url)[1].lower()
            if ext not in IMAGE_EXTS:
                return None

            local_path = _caminho_local(url)
            if local_path is None or not os.path.exists(local_path):
                return None

            with open(local_path, "rb") as f:
                original = f.read()

            compressed = _compress_bytes(original, ext)
            if compressed is None:
                return None

            if execute:
                if not sem_backup:
                    backup = os.path.join(os.path.dirname(local_path), ".originais")
                    os.makedirs(backup, exist_ok=True)
                    destino = os.path.join(backup, os.path.basename(local_path))
                    if not os.path.exists(destino):  # não sobrescreve backup de rodada anterior
                        shutil.copy2(local_path, destino)
                # Arquivo temporário + replace: um Ctrl-C no meio não deixa imagem truncada
                # servindo na vitrine.
                temporario = local_path + ".tmp"
                with open(temporario, "wb") as f:
                    f.write(compressed)
                os.replace(temporario, local_path)

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
                if execute:
                    s3.put_object(
                        Bucket=bucket, Key=key, Body=compressed, ContentType=content_type
                    )
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

        # Catálogo (feature 268) — a superfície PÚBLICA, e a única que ficou de fora da regra de
        # compressão por causa da recuperação da 264. `tamanho_por_url` existe porque
        # `CatalogItemImage.file_size_bytes` guarda o tamanho de quando a foto passou pelo
        # importador: depois do re-download cru ela ficou mentindo, e precisa ser reescrita.
        tamanho_por_url: dict[str, list] = {}
        for img in CatalogItemImage.query.all():
            if img.url:
                jobs.append(img.url)
                tamanho_por_url.setdefault(img.url, []).append(img)
        for personagem in CatalogCharacter.query.all():
            if personagem.photo_url:
                jobs.append(personagem.photo_url)

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
                # A coluna volta a dizer a verdade sobre o arquivo em disco.
                for img in tamanho_por_url.get(url, []):
                    img.file_size_bytes = after
                click.echo(
                    f"  [{i:>3}/{len(jobs)}] OK      {label}"
                    f"   {before/1024:.0f}KB -> {after/1024:.0f}KB  (-{saved_pct}%)"
                )

        if execute:
            db.session.commit()

        click.echo(f"\n{'-'*60}")
        click.echo(f"  Comprimidas : {compressed_count}")
        click.echo(f"  Puladas     : {skipped_count}  (pequenas ou externas)")
        if total_before:
            saved_mb = (total_before - total_after) / 1024 / 1024
            click.echo(f"  Economia    : {total_before/1024/1024:.1f}MB -> {total_after/1024/1024:.1f}MB  ({saved_mb:.1f}MB liberados)")
        click.echo(f"{'-'*60}")
        if not execute:
            click.echo("  DRY-RUN — nada foi escrito. Repita com --execute para aplicar.")
        elif not USE_S3 and not sem_backup:
            click.echo("  Originais preservados em <pasta>/.originais/")
        click.echo("")

    @app.cli.command("warm-thumbnails")
    def warm_thumbnails():
        """Pré-aquece as variantes de miniatura (feature 270): ninguém paga a primeira geração.

        Sob demanda é auto-curável (foto nova nasce com variante na primeira visita), mas a
        primeira geração roda numa thread do gunicorn — e o incidente da 263 foi exatamente
        requisição presa segurando thread. Rode depois do deploy, e depois do
        `compress-images --execute`: decodificar um original de 4 MB por variante é lento à toa.
        Idempotente: o que já está em cache conta como existente e não é reescrito.

        O que aquece = o que as telas pedem: TODAS as fotos do catálogo a 128 (tira de
        miniaturas), capas de item e fotos de personagem a 320/480/640 (cards da grade), fotos
        de rosto de talento a 320/480/640 (grade do Banco). URL absoluta (legado do Drive) não tem
        variante e é contada à parte.
        """
        import time

        from app.catalogo.og_ops import resolve_variante, variante_em_cache
        from app.models import CatalogCharacter, CatalogItem, CatalogItemImage, Talent

        uploads = app.config["UPLOAD_FOLDER"]
        trabalhos: list[tuple[str, int]] = []
        for img in CatalogItemImage.query.order_by(CatalogItemImage.id).all():
            trabalhos.append((img.url, 128))
        larguras_card = (320, 480, 640)
        for item in CatalogItem.query.order_by(CatalogItem.id).all():
            capa = item.cover_image
            if capa:
                trabalhos += [(capa.url, w) for w in larguras_card]
        for ch in CatalogCharacter.query.filter(CatalogCharacter.photo_url.isnot(None)).all():
            trabalhos += [(ch.photo_url, w) for w in larguras_card]
        for talento in Talent.query.filter(Talent.photo_face_path.isnot(None)).all():
            trabalhos += [(talento.photo_face_path, w) for w in larguras_card]
        unicos = list(dict.fromkeys(trabalhos))

        gerados = existentes = falhas = sem_variante = 0
        inicio = time.monotonic()
        for url, largura in unicos:
            if variante_em_cache(url, largura, uploads):
                existentes += 1
                continue
            if url.startswith(("http://", "https://")):
                sem_variante += 1
                continue
            if resolve_variante(url, largura, uploads):
                gerados += 1
            else:
                falhas += 1
                if falhas <= 20:
                    click.echo(f"  FALHA {largura}px {url}")
                elif falhas == 21:
                    click.echo("  ... (demais falhas omitidas; o total sai no resumo)")
        click.echo(
            f"warm-thumbnails: {gerados} geradas, {existentes} já existiam, "
            f"{sem_variante} sem variante (URL externa), {falhas} falhas — "
            f"{len(unicos)} pedidos em {time.monotonic() - inicio:.0f}s"
        )

    @app.cli.command("notificacoes-limpar")
    @click.option("--execute", is_flag=True, help="apaga de verdade (padrão: só conta)")
    def notificacoes_limpar(execute: bool):
        """Retenção das notificações internas (feature 272), à mão.

        Lida há mais de 30 dias ou não lida há mais de 180 dias sai. A mesma rotina roda sozinha
        no laço diário do review-cleanup; este comando existe para depois de um deploy, num
        incidente, e para o verify_272 testar a regra sem esperar 24 h. Dry-run por padrão.
        """
        from app.notificacoes.notificacoes_ops import contar_antigas, limpar_antigas

        candidatas = contar_antigas()
        if not execute:
            click.echo(f"notificacoes-limpar: {candidatas} notificação(ões) seriam apagadas. "
                       "Repita com --execute para aplicar.")
            return
        apagadas = limpar_antigas()
        click.echo(f"notificacoes-limpar: {apagadas} notificação(ões) apagada(s).")

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
