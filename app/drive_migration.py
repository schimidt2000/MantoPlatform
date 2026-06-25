"""Migração de fotos/documentos de talentos do Google Drive para o volume (feature 087).

Usado por dois pontos de entrada:
- CLI: ``flask migrate-drive-to-volume`` (em ``app/cli.py``).
- Web: botão do admin (rota em ``app/admin/routes.py``) que dispara em segundo plano.

O download tenta primeiro o link público (lh3 para imagens; ``uc?export=download`` para arquivos
compartilhados) e, como reserva, a API do Drive com a conta de serviço — que funciona para qualquer
tipo (inclusive PDF) quando a pasta das respostas do Form é compartilhada com o e-mail da conta de
serviço.
"""
import io
import json
import os
import re
import threading
from datetime import datetime

# Campos de mídia do Talent e a subpasta de destino no volume.
TALENT_MEDIA_FIELDS = {
    "photo_face_path": "talent_photos",
    "photo_full_path": "talent_photos",
    "doc_photo_path": "talent_docs",
    "cnh_file_path": "talent_docs",
}

# Extensão por Content-Type / mimeType retornado no download.
_CT_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/pjpeg": ".jpg",
    "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
    "application/pdf": ".pdf",
}

# Status compartilhado da migração (app roda em instância única). Lido pela página de progresso.
migration_status = {
    "running": False, "done": False, "total": 0, "processed": 0,
    "migrated": 0, "errors": 0, "started_at": None, "finished_at": None,
}
_status_lock = threading.Lock()


def is_drive_url(value: str | None) -> bool:
    """True se o valor é um link hospedado no Google Drive (foto lh3 ou documento drive.google)."""
    if not value or not value.startswith(("http://", "https://")):
        return False
    return "googleusercontent.com" in value or "drive.google.com" in value


def drive_file_id(url: str) -> str | None:
    """Extrai o file_id de um link do Google Drive em qualquer formato conhecido."""
    for pat in (r"/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _get_drive_service():
    """Cria o serviço do Drive (conta de serviço), aceitando credencial por env ou arquivo."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    env_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if env_json:
        info = json.loads(env_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    else:
        path = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))
        creds = service_account.Credentials.from_service_account_file(path, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _download(url: str, sa_state: dict) -> tuple[bytes, str] | None:
    """Baixa o arquivo: link público primeiro (imagens), conta de serviço como reserva."""
    import requests

    file_id = drive_file_id(url)
    if not file_id:
        return None

    # 1) Público (lh3 para imagens; uc para arquivos compartilhados publicamente)
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
        guess = os.path.splitext(url.split("?")[0])[1].lower()
        ext = _CT_EXT.get(ct) or (guess if guess in (".jpg", ".jpeg", ".png", ".webp", ".pdf") else ".jpg")
        return resp.content, ext

    # 2) Conta de serviço (qualquer tipo, se houver acesso). Desliga após a 1ª falha de acesso.
    if sa_state.get("ok") is False:
        return None
    try:
        if sa_state.get("svc") is None:
            sa_state["svc"] = _get_drive_service()
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
        if sa_state.get("ok") is None:
            sa_state["ok"] = False
        return None


def run_drive_migration(limit: int = 0, echo=None) -> dict:
    """Migra os arquivos de Drive dos talentos para o volume; atualiza ``migration_status``.

    Args:
        limit: Máximo de arquivos a processar (0 = todos).
        echo: Callback opcional ``(str) -> None`` para log de progresso (usado pela CLI).

    Returns:
        Dicionário de contagens da execução.
    """
    from werkzeug.datastructures import FileStorage

    from app import db
    from app.models import Talent
    from app.storage import save_file

    def _log(msg: str) -> None:
        if echo:
            echo(msg)

    talents = Talent.query.order_by(Talent.id).all()
    jobs = []
    for t in talents:
        for field, subfolder in TALENT_MEDIA_FIELDS.items():
            if is_drive_url(getattr(t, field)):
                jobs.append((t.id, field, subfolder, getattr(t, field)))

    with _status_lock:
        migration_status.update(
            running=True, done=False, total=len(jobs), processed=0,
            migrated=0, errors=0, started_at=datetime.utcnow(), finished_at=None,
        )

    sa_state: dict = {"svc": None, "ok": None}
    migrated = errors = processed = 0
    try:
        for talent_id, field, subfolder, url in jobs:
            if limit and processed >= limit:
                break
            processed += 1
            t = Talent.query.get(talent_id)
            if not t or not is_drive_url(getattr(t, field)):
                continue  # já migrado por outra execução
            try:
                downloaded = _download(url, sa_state)
                if downloaded is None:
                    errors += 1
                    _log(f"  [{processed:>4}] ERRO    #{talent_id} {field}  (download falhou)")
                else:
                    data, ext = downloaded
                    fs = FileStorage(stream=io.BytesIO(data), filename=f"migrado{ext}")
                    new_url = save_file(fs, subfolder)
                    setattr(t, field, new_url)
                    db.session.commit()
                    migrated += 1
                    _log(f"  [{processed:>4}] OK      #{talent_id} {field}  -> {new_url}")
            except Exception as e:  # noqa: BLE001 — falha de 1 item não derruba a migração
                db.session.rollback()
                errors += 1
                _log(f"  [{processed:>4}] ERRO    #{talent_id} {field}  ({e})")
            with _status_lock:
                migration_status.update(processed=processed, migrated=migrated, errors=errors)
    finally:
        with _status_lock:
            migration_status.update(
                running=False, done=True, processed=processed,
                migrated=migrated, errors=errors, finished_at=datetime.utcnow(),
            )

    return {"total": len(jobs), "processed": processed, "migrated": migrated,
            "errors": errors, "remaining": max(0, len(jobs) - processed)}


def start_background_migration(app) -> bool:
    """Dispara a migração em segundo plano (não bloqueia). Retorna False se já estiver rodando."""
    with _status_lock:
        if migration_status["running"]:
            return False
        migration_status["running"] = True  # marca cedo p/ evitar corrida de duplo clique

    def _run():
        with app.app_context():
            try:
                run_drive_migration()
            except Exception:
                with _status_lock:
                    migration_status.update(running=False, done=True, finished_at=datetime.utcnow())

    threading.Thread(target=_run, daemon=True).start()
    return True
