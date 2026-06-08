#!/usr/bin/env python3
"""Execução manual / backup da sincronização da agenda com o Google Calendar.

A sincronização automática agora roda DENTRO do app (thread de background, ver
``app/__init__.py`` → ``_start_calendar_sync``). Este script é mantido como
execução manual/backup e reaproveita exatamente a mesma lógica
(``app.calendar.sync.run_calendar_sync``).

Uso:
    python sync_worker.py

(Opcional) ainda pode ser configurado como serviço Cron no Railway, mas não é
mais necessário para o app manter a agenda atualizada.
"""
import sys
import os

from dotenv import load_dotenv
load_dotenv()

# Em desenvolvimento, permite OAuth sem HTTPS
if os.getenv("FLASK_ENV", "development") != "production":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from app import create_app
from app.calendar.sync import run_calendar_sync

app = create_app()

with app.app_context():
    result = run_calendar_sync()
    print(
        f"[sync_worker] {result['months']} mês(es), {result['errors']} erro(s).",
        flush=True,
    )
    for line in result["results"]:
        print(f"  - {line}", flush=True)
    sys.exit(1 if result["errors"] else 0)
