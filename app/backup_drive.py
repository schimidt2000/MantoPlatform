"""Backup automático para o Google Drive (feature 264, pós-suspensão do Railway).

Nasceu do incidente de 28/08/2026: a conta do Railway foi suspensa e descobriu-se que os
arquivos do volume NUNCA tiveram cópia externa — só o banco tinha (dump noturno na máquina do
dono). Este módulo faz, de dentro do próprio processo web (mesmo padrão das threads `_start_*`):

- **2x/dia**: `pg_dump -Fc` do banco -> Drive (`manto_db_<data>_<hora>.dump`), retenção 14.
- **1x/dia**: tar.gz das pastas de mídia de `instance/` -> Drive (`manto_media_<data>.tar.gz`),
  retenção 2 (os arquivos pertencem à conta de serviço, que tem 15 GB — retenção curta é o que
  cabe; o dump local diário da máquina do dono continua como segunda cópia do banco).

Autenticação: conta de serviço (a mesma do Sheets/Drive de figurinos) com escopo `drive`,
enviando para uma pasta do Drive DO DONO compartilhada com ela como Editor. O id da pasta vem do
env `BACKUP_DRIVE_FOLDER_ID` ou do arquivo `instance/backup_drive_folder.txt` (gravável por SSH,
sem redeploy). Sem id configurado o backup fica desligado e loga isso uma única vez — o deploy é
seguro antes de a pasta existir.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import subprocess
import tarfile

logger = logging.getLogger(__name__)

#: Subpastas de `instance/` que entram no pacote de mídia. `credentials` vai junto de propósito:
#: é o que permite reerguer o backup do zero num desastre total.
_MEDIA_SUBDIRS = ("uploads", "nfc_media", "virtual_videos", "credentials")
_KEEP_DB = 14      # 7 dias x 2 por dia
_KEEP_MEDIA = 2    # ~6,5 GB no regime atual — o que cabe nos 15 GB da conta de serviço
_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _tmp_no_disco(app, sufixo: str) -> str:
    """Caminho temporário NO DISCO PERSISTENTE — nunca em /tmp.

    No Render o /tmp é tmpfs (mora na RAM): escrever o tar de ~3 GB lá estourou os 2 GB do
    container e o kernel matou o serviço inteiro (exit 137, incidente de 28/08/2026 à noite).
    Fica na raiz de `instance/`, FORA das subpastas empacotadas — o tar só adiciona
    `_MEDIA_SUBDIRS`, então o temporário nunca entra no próprio pacote.
    """
    return os.path.join(app.instance_path, f".backup_tmp{sufixo}")


def _folder_id(app) -> str:
    env = (os.getenv("BACKUP_DRIVE_FOLDER_ID") or "").strip()
    if env:
        return env
    path = os.path.join(app.instance_path, "backup_drive_folder.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    return ""


def _drive_service(app):
    """Serviço do Drive pela conta de serviço; tolera o env JSON quebrado (multi-linha)."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    env_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or ""
    creds = None
    if env_json.strip():
        try:
            info = json.loads(env_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
        except ValueError:
            # .env com o JSON colado em várias linhas — o mesmo defeito que quebrava o
            # talent-sync. Cai para o arquivo em vez de morrer.
            logger.warning("[backup] GOOGLE_SHEETS_CREDENTIALS invalido; usando arquivo")
    if creds is None:
        path = os.path.join(app.instance_path, "credentials", "sheets_service_account.json")
        creds = service_account.Credentials.from_service_account_file(path, scopes=_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _upload(service, folder_id: str, local_path: str, name: str, mime: str) -> None:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(local_path, mimetype=mime, resumable=True,
                            chunksize=10 * 1024 * 1024)
    service.files().create(
        body={"name": name, "parents": [folder_id]},
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()


def _prune(service, folder_id: str, prefix: str, keep: int) -> int:
    """Apaga (permanentemente) os mais antigos além de ``keep``.

    Os nomes carregam a data — ordenar por nome desc é ordenar por idade.
    """
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name contains '{prefix}' and trashed=false",
        fields="files(id, name)", orderBy="name desc", pageSize=100,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    velhos = resp.get("files", [])[keep:]
    for f in velhos:
        service.files().delete(fileId=f["id"], supportsAllDrives=True).execute()
    return len(velhos)


def run_db_backup(app) -> str:
    """``pg_dump -Fc`` do banco direto para o Drive. Retorna o nome do arquivo enviado."""
    folder = _folder_id(app)
    if not folder:
        raise RuntimeError("BACKUP_DRIVE_FOLDER_ID nao configurado")
    db_url = app.config["SQLALCHEMY_DATABASE_URI"].replace(
        "postgresql+psycopg://", "postgresql://", 1)
    stamp = _dt.datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    nome = f"manto_db_{stamp}.dump"
    caminho = _tmp_no_disco(app, ".dump")
    try:
        subprocess.run(["pg_dump", db_url, "-Fc", "-f", caminho],
                       check=True, capture_output=True, timeout=600)
        service = _drive_service(app)
        _upload(service, folder, caminho, nome, "application/octet-stream")
        removidos = _prune(service, folder, "manto_db_", _KEEP_DB)
        tam = os.path.getsize(caminho) / 1e6
        logger.info("[backup] db OK: %s (%.1f MB), %d antigos removidos", nome, tam, removidos)
        return nome
    finally:
        try:
            os.unlink(caminho)
        except OSError:
            pass


def run_media_backup(app) -> str:
    """Empacota as pastas de mídia de ``instance/`` num tar.gz e envia ao Drive."""
    folder = _folder_id(app)
    if not folder:
        raise RuntimeError("BACKUP_DRIVE_FOLDER_ID nao configurado")
    stamp = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    nome = f"manto_media_{stamp}.tar.gz"
    caminho = _tmp_no_disco(app, ".tar.gz")
    try:
        with tarfile.open(caminho, "w|gz") as tar:
            for sub in _MEDIA_SUBDIRS:
                p = os.path.join(app.instance_path, sub)
                if os.path.isdir(p):
                    tar.add(p, arcname=sub)
        service = _drive_service(app)
        _upload(service, folder, caminho, nome, "application/gzip")
        removidos = _prune(service, folder, "manto_media_", _KEEP_MEDIA)
        tam = os.path.getsize(caminho) / 1e9
        logger.info("[backup] midia OK: %s (%.2f GB), %d antigos removidos", nome, tam, removidos)
        return nome
    finally:
        try:
            os.unlink(caminho)
        except OSError:
            pass


def start_backup_thread(app) -> None:
    """Thread daemon: banco às 05h/17h UTC (02h/14h SP), mídia às 06h UTC (03h SP).

    Mesmo contrato das outras threads ``_start_*`` de ``create_app``: ``except Exception`` nunca
    deixa a thread morrer; sobe uma cópia POR WORKER do gunicorn — o conjunto ``feitos`` evita
    duplicar no mesmo processo, e execuções repetidas entre workers só custam um upload extra
    inofensivo (nomes iguais não colidem no Drive; a retenção limpa o excesso).
    """
    import threading
    import time

    if not _folder_id(app):
        app.logger.info(
            "[backup] desligado: pasta do Drive nao configurada "
            "(env BACKUP_DRIVE_FOLDER_ID ou instance/backup_drive_folder.txt)")
        return

    def _loop() -> None:
        feitos: set[str] = set()
        while True:
            try:
                agora = _dt.datetime.utcnow()
                slots: list[tuple[str, str]] = []
                if agora.hour in (5, 17):
                    slots.append(("db", f"db-{agora.date()}-{agora.hour}"))
                if agora.hour == 6:
                    slots.append(("media", f"media-{agora.date()}"))
                for tipo, chave in slots:
                    if chave in feitos:
                        continue
                    with app.app_context():
                        if tipo == "db":
                            run_db_backup(app)
                        else:
                            run_media_backup(app)
                    feitos.add(chave)
                if len(feitos) > 100:
                    feitos.clear()
            except Exception as exc:  # noqa: BLE001 — nunca deixar a thread morrer
                app.logger.warning("[backup] erro: %s", exc)
            time.sleep(300)

    threading.Thread(target=_loop, daemon=True, name="backup-drive").start()
    app.logger.info("[backup] thread iniciada (db 05h/17h UTC, midia 06h UTC)")
