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

        from app import db
        from app.models import (
            CatalogCharacter,
            CatalogItemImage,
            FigurinoSheet,
            Talent,
            User,
        )
        from app.storage import COMPRESS_EXTS, MAX_PX, QUALITY, caminho_local, comprimir_bytes

        # Sem cópia das constantes: `MAX_PX`/`QUALITY`/`COMPRESS_EXTS` e a tradução URL→disco
        # vivem em `app/storage.py`, junto do upload. Enquanto eram duas listas, mudar uma e
        # esquecer a outra fazia o comando e o upload discordarem em silêncio.

        USE_S3 = app.config.get("USE_S3", False)
        IMAGE_EXTS = COMPRESS_EXTS

        def _compress_bytes(data: bytes, ext: str) -> bytes | None:
            """Bytes comprimidos, ou None quando não precisa (ou não deu).

            Duas regras que só existem aqui e por isso são parâmetros, não default: **manter o
            formato** (a URL já está no banco; mudar a extensão quebraria toda referência) e
            **pular quem já é pequena** (reprocessar 150 KB não ganha nada e custa um decode).
            """
            try:
                resultado = comprimir_bytes(
                    data, ext, manter_formato=True, pular_se_pequena=150 * 1024
                )
            except Exception as exc:  # noqa: BLE001 — imagem ilegível: mantém o original
                logger.warning("compress-images: falha ao comprimir: %s", exc)
                return None
            return None if resultado is None else resultado[0]

        def _caminho_local(url: str) -> str | None:
            """Traduz a URL pública no caminho em disco (ver `storage.caminho_local`).

            O comentário histórico continua valendo: `/catalogo/midia/<arquivo>` é a rota pública
            (existe para NÃO exigir login), mas o arquivo mora em `uploads/catalog_photos/`. Sem
            essa tradução o comando resolvia para `instance/catalogo/midia/...`, que não existe, e
            PULAVA a vitrine inteira em silêncio.
            """
            caminho = caminho_local(url)
            return None if caminho is None else os.path.abspath(caminho)

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
    @click.option(
        "--familia",
        type=click.Choice(["catalogo", "talento", "figurino", "todas"]),
        default="todas",
        help="aquece so uma familia (o deploy ja compete com o app por CPU nos 3 workers)",
    )
    @click.option("--largura", type=int, default=None, help="aquece so esta largura")
    @click.option("--falhas", type=int, default=100, help="quantas falhas imprimir")
    def warm_thumbnails(familia: str, largura: int | None, falhas: int):
        """Pré-aquece as variantes de miniatura (features 270 e 292).

        Sob demanda é auto-curável (foto nova nasce com variante na primeira visita), mas a
        primeira geração roda numa thread do gunicorn — e o incidente da 263 foi exatamente
        requisição presa segurando thread. Rode depois do deploy, e depois do
        `compress-images --execute`: decodificar um original de 4 MB por variante é lento à toa.
        Idempotente: o que já está em cache conta como existente e não é reescrito.

        O que aquece = o que as telas pedem. **Catálogo**: todas as fotos a 128 (tira de
        miniaturas), capas e personagens a 320/480/640 (cards). **Talento**: foto de rosto a 128
        (o avatar da produção e dos comboboxes — a largura que faltava, e o motivo de
        `talent_thumbs/128` estar vazia em produção) e a 320/480/640 (grade do Banco).
        **Figurino**: foto da ficha nas quatro larguras (feature 292). URL absoluta (legado do
        Drive) não tem variante e é contada à parte.

        `--familia` existe porque a rodada completa passou de ~2.500 para ~4.500 decodificações:
        depois de um deploy dá para aquecer só o que mudou, sem competir com o app pela CPU.
        """
        import time

        from app.catalogo.og_ops import resolve_variante, variante_em_cache
        from app.models import (
            CatalogCharacter,
            CatalogItem,
            CatalogItemImage,
            FigurinoSheet,
            Talent,
        )

        uploads = app.config["UPLOAD_FOLDER"]
        larguras_card = (320, 480, 640)
        trabalhos: list[tuple[str, int]] = []

        def quer(nome: str) -> bool:
            return familia in (nome, "todas")

        if quer("catalogo"):
            for img in CatalogItemImage.query.order_by(CatalogItemImage.id).all():
                trabalhos.append((img.url, 128))
            for item in CatalogItem.query.order_by(CatalogItem.id).all():
                capa = item.cover_image
                if capa:
                    trabalhos += [(capa.url, w) for w in larguras_card]
            for ch in CatalogCharacter.query.filter(CatalogCharacter.photo_url.isnot(None)).all():
                trabalhos += [(ch.photo_url, w) for w in larguras_card]
        if quer("talento"):
            for talento in Talent.query.filter(Talent.photo_face_path.isnot(None)).all():
                trabalhos += [(talento.photo_face_path, w) for w in (128, *larguras_card)]
        if quer("figurino"):
            # `photo_url` (property) e nao `photo_filename`: ela normaliza o legado de nome nu
            # para `/uploads/figurino_photos/<x>`, que e a forma que tem variante.
            for ficha in FigurinoSheet.query.order_by(FigurinoSheet.id).all():
                if ficha.photo_url:
                    trabalhos += [(ficha.photo_url, w) for w in (128, *larguras_card)]

        if largura is not None:
            trabalhos = [t for t in trabalhos if t[1] == largura]
        unicos = list(dict.fromkeys(trabalhos))

        gerados = existentes = sem_variante = falhou = 0
        por_familia: dict[str, list[int]] = {}
        inicio = time.monotonic()
        for url, w in unicos:
            if "figurino_photos" in url:
                rotulo = "figurino"
            elif "talent_photos" in url:
                rotulo = "talento"
            else:
                rotulo = "catalogo"
            contadores = por_familia.setdefault(rotulo, [0, 0])
            if variante_em_cache(url, w, uploads):
                existentes += 1
                continue
            if url.startswith(("http://", "https://")):
                sem_variante += 1
                continue
            if resolve_variante(url, w, uploads):
                gerados += 1
                contadores[0] += 1
            else:
                falhou += 1
                contadores[1] += 1
                if falhou <= falhas:
                    click.echo(f"  FALHA {w}px {url}")
                elif falhou == falhas + 1:
                    click.echo("  ... (demais falhas omitidas; o total sai no resumo)")
        for nome, (ok, ruim) in sorted(por_familia.items()):
            click.echo(f"  {nome:>9}: {ok} geradas, {ruim} falhas")
        click.echo(
            f"warm-thumbnails: {gerados} geradas, {existentes} já existiam, "
            f"{sem_variante} sem variante (URL externa), {falhou} falhas — "
            f"{len(unicos)} pedidos em {time.monotonic() - inicio:.0f}s"
        )

    @app.cli.command("midia-orfa")
    @click.option(
        "--familia",
        type=click.Choice(
            ["talento", "figurino", "catalogo", "personagem", "portfolio",
             "acervo3d", "usuario", "todas"]
        ),
        default="todas",
    )
    @click.option("--csv", "como_csv", is_flag=True, help="uma linha por problema, para relatório")
    @click.option(
        "--rapido", is_flag=True, help="não abre os arquivos (só confere se existem)"
    )
    def midia_orfa(familia: str, como_csv: bool, rapido: bool):
        """Diz, arquivo por arquivo, POR QUE uma foto não aparece na tela.

        A migração Railway → Render (28/08/2026) trouxe o banco e não trouxe o volume de uploads.
        **Nenhum campo ficou NULL** — a linha continua apontando para `/uploads/...` e o Flask
        responde 404 — então qualquer consulta escrita com ``IS NULL`` subconta o estrago. O
        critério certo é cruzar o caminho gravado com o disco, que é o que este comando faz.

        Roda igual em qualquer ambiente, e é essa a graça: no `manto_local` acusa quase tudo
        (o disco de dev tem uma fração dos arquivos) e no Shell do Render dá o número real. É a
        resposta para "isto está consertado em todos os ambientes?".

        Somente leitura. No Shell do Render use `MANTO_SEM_THREADS=1` na frente.
        """
        from app.talents.midia_ops import MOTIVO_OK, inventario, resumo

        achados = inventario(familia=familia, conferir_conteudo=not rapido)
        problemas = [a for a in achados if a.problema]

        if como_csv:
            click.echo("familia;id;nome;coluna;url;motivo")
            for a in problemas:
                nome = (a.nome or "").replace(";", ",")
                click.echo(f"{a.familia};{a.registro_id};{nome};{a.coluna};{a.url};{a.motivo}")
            return

        click.echo("")
        click.echo(f"{'-' * 72}")
        click.echo("  Inventário de mídia — banco cruzado com o disco")
        click.echo(f"{'-' * 72}")
        for nome_familia, motivos in sorted(resumo(achados).items()):
            total = sum(motivos.values())
            ok = motivos.get(MOTIVO_OK, 0)
            click.echo(f"  {nome_familia:>11}: {total:>5} referências, {ok:>5} íntegras")
            for motivo, quantos in sorted(motivos.items()):
                if motivo != MOTIVO_OK:
                    click.echo(f"  {'':>11}  {quantos:>5}  {motivo}")
        click.echo(f"{'-' * 72}")
        click.echo(f"  Total com problema: {len(problemas)}")
        click.echo("  Use --csv para a lista completa (colável no relatório).")
        click.echo(f"{'-' * 72}")
        click.echo("")
        for a in problemas[:40]:
            click.echo(f"  {a.familia:>11} #{a.registro_id:<5} {a.motivo:<32} {a.nome[:34]}")
        if len(problemas) > 40:
            click.echo(f"  ... e mais {len(problemas) - 40} (use --csv)")
        click.echo("")

    @app.cli.command("fix-heic")
    @click.option("--execute", is_flag=True, help="converte de verdade (padrão: só lista)")
    def fix_heic(execute: bool):
        """Converte para JPEG o que está em disco num formato que o navegador não abre.

        O `compress-images` **não** resolve isto: ele mantém o formato e a extensão de propósito
        (a URL já está gravada no banco), então reescrever um `.heic` produz um JPEG dentro de um
        arquivo `.heic` — e o `send_from_directory` continua declarando `image/heic` pelo nome.
        Aqui o arquivo vira `<uuid>.jpg`, **a coluna é atualizada**, o original sai do disco e as
        variantes antigas são invalidadas.

        Pega três casos, todos medidos na produção em 03/09/2026:

        - **PDF com nome de foto** (28 arquivos, quase todos documento de talento): o Flask declara
          `image/jpeg` pelo nome e o navegador não abre nem oferece download. Aqui só a **extensão**
          muda, para `.pdf` — rasterizar um documento seria perder o documento.
        - **Formato ilegível escondido numa extensão de imagem** (5 HEIC de iPhone gravados como
          `.jpg`): o Pillow abre, o Chrome não. Vira JPEG de verdade.
        - **Extensão que o navegador não abre** (`.heic`, `.tiff`…), gravada antes de o servidor
          saber converter.

        **Dry-run por padrão**, imprimindo o mapa `antigo → novo`: é a única reversão possível
        depois do `--execute`, então leia linha a linha antes.
        """
        from app import db, imaging
        from app.catalogo.og_ops import invalidar_variantes
        from app.storage import (
            MAX_PX,
            QUALITY,
            caminho_local,
            delete_file,
            save_bytes,
        )
        from app.talents.midia_ops import (
            MOTIVO_FORMATO_OCULTO,
            MOTIVO_ILEGIVEL,
            MOTIVO_NAO_E_IMAGEM,
            inventario,
        )

        uploads = app.config["UPLOAD_FOLDER"]
        alvos = [
            a for a in inventario()
            if a.motivo in (MOTIVO_ILEGIVEL, MOTIVO_NAO_E_IMAGEM, MOTIVO_FORMATO_OCULTO)
        ]
        if not alvos:
            click.echo("fix-heic: nada a converter — todo arquivo em disco é exibível.")
            return

        modelos = {
            "talento": "Talent",
            "figurino": "FigurinoSheet",
            "catalogo": "CatalogItemImage",
            "personagem": "CatalogCharacter",
            "portfolio": "TalentMedia",
            "acervo3d": "Acervo3DItem",
            "usuario": "User",
        }
        import app.models as m

        convertidos = falhas = 0
        for a in alvos:
            caminho = caminho_local(a.url)
            if caminho is None or not os.path.exists(caminho):
                continue
            with open(caminho, "rb") as handle:
                dados = handle.read()

            # Um PDF gravado com nome de foto não deve virar JPEG: rasterizar um documento é
            # perder o documento. O conserto é a EXTENSÃO — com `.pdf`, o `send_from_directory`
            # declara `application/pdf` e o navegador abre no visualizador.
            e_pdf = dados.startswith(b"%PDF")
            img = None if e_pdf else imaging.abrir(dados)
            if not e_pdf and img is None:
                click.echo(f"  ILEGÍVEL  {a.familia} #{a.registro_id} {a.url}")
                falhas += 1
                continue

            nova_ext = ".pdf" if e_pdf else ".jpg"
            if not execute:
                click.echo(
                    f"  {a.url}  ->  <uuid>{nova_ext}   ({a.familia} #{a.registro_id}"
                    f"{' — é PDF, só troca a extensão' if e_pdf else ''})"
                )
                convertidos += 1
                continue

            if e_pdf:
                conteudo = dados
            else:
                from PIL import Image

                frame = imaging.para_rgb(img)
                if max(frame.width, frame.height) > MAX_PX:
                    frame.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)
                buffer = io.BytesIO()
                frame.save(buffer, format="JPEG", quality=QUALITY, optimize=True)
                conteudo = buffer.getvalue()

            subpasta = a.url.strip("/").split("/")[1] if a.url.startswith("/uploads/") else (
                "catalog_photos"
            )
            nova = save_bytes(conteudo, subpasta, nova_ext)
            # A coluna do catálogo guarda a URL pública `/catalogo/midia/<arq>`, não `/uploads/`.
            if a.url.startswith("/catalogo/midia/"):
                nova = "/catalogo/midia/" + nova.rsplit("/", 1)[-1]
            registro = getattr(m, modelos[a.familia]).query.get(a.registro_id)
            coluna = "photo_filename" if a.coluna == "photo_url" and a.familia == "figurino" else a.coluna
            setattr(registro, coluna, nova)
            db.session.commit()
            delete_file(a.url)
            invalidar_variantes(a.url, uploads)
            click.echo(f"  {a.url}  ->  {nova}")
            convertidos += 1

        click.echo("")
        click.echo(f"  Convertidos: {convertidos}   Ilegíveis (sem conserto): {falhas}")
        if not execute:
            click.echo("  DRY-RUN — nada foi escrito. Repita com --execute para aplicar.")
        click.echo("")

    @app.cli.command("campanha-fotos")
    @click.option("--enviar", is_flag=True, help="envia de verdade (padrão: só mostra)")
    @click.option("--limite", type=int, default=None, help="manda só para os N primeiros")
    @click.option("--pausa", type=float, default=3.0, help="segundos entre um envio e o próximo")
    @click.option(
        "--id",
        "ids",
        type=int,
        multiple=True,
        help="restringe a estes talentos (repetível) — para reenviar a uma pessoa só",
    )
    def campanha_fotos(enviar: bool, limite: int | None, pausa: float, ids: tuple[int, ...]):
        """Pede aos talentos que reenviem pelo portal os arquivos perdidos na migração (293).

        **Dry-run por padrão**: lista quem receberia, o que falta de cada um, quem é pulado e por
        quê, e imprime um e-mail renderizado por inteiro para conferência. Só com `--enviar` sai
        mensagem.

        Três cuidados que a campanha de 28/08/2026 não teve e que explicam o resultado dela:

        1. **Link que dura.** O token vai com `CAMPANHA_RESET_TTL` (7 dias) em vez da hora do
           autoatendimento — quem abre o e-mail à tarde não recebe "link inválido" — e já leva
           para a tela de fotos (`?destino=`).
        2. **Dedup que sobrevive a redeploy.** Cada envio grava uma linha no `AuditLog`; rodar de
           novo não reenvia. Antes o controle era um `.txt` na máquina de uma pessoa só.
        3. **Sem queimar o remetente.** Uma conexão SMTP para o lote todo, `--pausa` entre as
           mensagens e `--limite` para mandar uma primeira onda pequena. A reputação do
           joao@ carrega convite de evento, redefinição de senha e nota fiscal.

        Quem tem devolução permanente registrada não recebe e-mail — sai numa lista de WhatsApp
        com o link `wa.me` pronto, porque para essas pessoas o e-mail já provou que não chega.

        No Shell do Render, use `MANTO_SEM_THREADS=1` na frente.
        """
        import time

        from app import db
        from app.email_service import mail, send_foto_pendente_email
        from app.models import AuditLog, EmailBounce, Talent
        from app.talent_portal.portal_account_ops import (
            CAMPANHA_RESET_TTL,
            emitir_token_de_reset,
        )
        from app.talent_portal.portal_links import FOTOS_PATH, portal_reset_url
        from app.talents.midia_ops import faltas_do_talento
        from app.utils import audit

        ACAO = "campanha_fotos_292"
        validade_dias = CAMPANHA_RESET_TTL.days

        consulta = Talent.query.filter_by(status="active")
        if ids:
            # `--id` existe para o caso concreto de reenviar a uma pessoa só depois que o casting
            # corrigiu o e-mail dela — e é o que permite verificar o comando sem tocar em quem
            # não faz parte do teste.
            consulta = consulta.filter(Talent.id.in_(ids))
        ativos = consulta.order_by(Talent.full_name).all()
        pendentes = [(t, faltas_do_talento(t)) for t in ativos]
        pendentes = [(t, f) for t, f in pendentes if f]

        emails = [(t.email_contact or "").strip().lower() for t, _ in pendentes]
        mortos = {
            b.email.lower()
            for b in EmailBounce.query.filter(
                EmailBounce.is_permanent.is_(True),
                EmailBounce.resolved_at.is_(None),
                db.func.lower(EmailBounce.email).in_([e for e in emails if e]),
            ).all()
        }
        ja_recebeu = {
            linha.entity_id
            for linha in AuditLog.query.filter_by(entity_type="Talent", action=ACAO).all()
        }

        vao_receber, sem_email, com_bounce, repetidos = [], [], [], []
        for talento, faltas in pendentes:
            endereco = (talento.email_contact or "").strip()
            if not endereco:
                sem_email.append((talento, faltas))
            elif endereco.lower() in mortos:
                com_bounce.append((talento, faltas))
            elif talento.id in ja_recebeu:
                repetidos.append((talento, faltas))
            else:
                vao_receber.append((talento, faltas))

        if limite is not None:
            vao_receber = vao_receber[:limite]

        def bloco(titulo: str, itens: list, extra=None) -> None:
            click.echo("")
            click.echo(f"  {titulo} ({len(itens)})")
            click.echo(f"  {'-' * 70}")
            for talento, faltas in itens:
                senha = "tem senha" if talento.password_hash else "SEM SENHA"
                click.echo(f"  #{talento.id:<5} {(talento.full_name or '')[:34]:<34} {senha}")
                click.echo(f"        {talento.email_contact or '(sem e-mail)'}")
                click.echo(f"        falta: {', '.join(faltas)}")
                if extra:
                    click.echo(f"        {extra(talento)}")

        bloco("VÃO RECEBER", vao_receber)
        bloco(
            "PULADOS — devolução permanente, MANDAR POR WHATSAPP",
            com_bounce,
            lambda t: f"WhatsApp: https://wa.me/{t.whatsapp_number or '(sem telefone)'}",
        )
        bloco("PULADOS — já receberam nesta campanha", repetidos)
        bloco("PULADOS — sem e-mail no cadastro", sem_email)

        sem_termo = [t for t, _ in vao_receber if not t.terms_accepted_at]
        if sem_termo:
            click.echo("")
            click.echo(
                f"  Aviso: {len(sem_termo)} de {len(vao_receber)} ainda não aceitaram os termos. "
                "O portal vai pedir o aceite ANTES de mostrar a tela de fotos."
            )

        if not enviar:
            if vao_receber:
                talento, faltas = vao_receber[0]
                token = emitir_token_de_reset(talento, CAMPANHA_RESET_TTL)
                db.session.rollback()  # dry-run não grava token nenhum
                url = portal_reset_url(token, FOTOS_PATH)
                click.echo("")
                click.echo(f"  {'=' * 70}")
                click.echo(f"  EXEMPLO — o que {talento.full_name} receberia:")
                click.echo(f"  {'=' * 70}")
                click.echo("  Assunto: 📸 Faltam arquivos no seu cadastro da Manto")
                click.echo(f"  Para:    {talento.email_contact}")
                click.echo(f"  Falta:   {', '.join(faltas)}")
                click.echo(f"  Botão:   {url}")
                click.echo(f"  Validade do link: {validade_dias} dias")
            click.echo("")
            click.echo("  DRY-RUN — nenhum e-mail saiu. Repita com --enviar para disparar.")
            click.echo("")
            return

        enviados = falhou = 0
        # Uma conexão SMTP para o lote inteiro: `_send` abre uma por mensagem, e 40 conexões
        # seguidas ao Gmail em poucos segundos é padrão de burst.
        with mail.connect():
            for indice, (talento, faltas) in enumerate(vao_receber):
                try:
                    token = emitir_token_de_reset(talento, CAMPANHA_RESET_TTL)
                    db.session.commit()
                    ok = send_foto_pendente_email(
                        talento,
                        faltas=faltas,
                        acao_url=portal_reset_url(token, FOTOS_PATH),
                        validade_dias=validade_dias,
                    )
                except Exception as exc:  # noqa: BLE001 — uma falha não pode parar a fila
                    db.session.rollback()
                    click.echo(f"  ERRO   #{talento.id} {talento.full_name}: {exc}")
                    falhou += 1
                    continue

                if ok:
                    # Marca DEPOIS do envio dar certo: e-mail que não saiu não gasta a vez
                    # (mesmo cuidado de `invite_reminders`).
                    audit(
                        action=ACAO,
                        entity_type="Talent",
                        entity_id=talento.id,
                        entity_name=talento.full_name,
                        detail=f"Reenvio pedido: {', '.join(faltas)}",
                    )
                    db.session.commit()
                    enviados += 1
                    click.echo(f"  enviado  #{talento.id} {talento.email_contact}")
                else:
                    falhou += 1
                    click.echo(f"  NAO SAIU #{talento.id} {talento.email_contact}")
                if pausa and indice < len(vao_receber) - 1:
                    time.sleep(pausa)

        click.echo("")
        click.echo(f"  Enviados: {enviados}   Falhas: {falhou}")
        click.echo(f"  Para mandar à mão (WhatsApp): {len(com_bounce)}")
        click.echo("")

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
