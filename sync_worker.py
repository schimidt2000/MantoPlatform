#!/usr/bin/env python3
"""Cron job: sincroniza o Google Calendar com o banco de dados.

Configurar no Railway como novo serviço tipo Cron:
  Comando : python sync_worker.py
  Schedule: */10 * * * *   (a cada 10 minutos)

Lógica:
  - Descobre o mês mais distante com evento no banco (a partir de hoje)
  - Sincroniza todos os meses de hoje até esse mês + 2 meses de buffer
    (o buffer garante que novos eventos adicionados ao Google sejam capturados)
"""
import sys
import os
from datetime import datetime, date

from dotenv import load_dotenv
load_dotenv()

# Em desenvolvimento, permite OAuth sem HTTPS
if os.getenv("FLASK_ENV", "development") != "production":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from app import create_app

app = create_app()

with app.app_context():
    from app.models import CalendarEvent
    from app.calendar.routes import sync_events, CALENDAR_ID, _mark_month_synced
    from app.calendar.service import fetch_events_for_month
    from app import db

    now = datetime.now()
    current = date(now.year, now.month, 1)

    # Evento mais distante no banco a partir deste mês
    last_event = (
        CalendarEvent.query
        .filter(CalendarEvent.start_at >= datetime(now.year, now.month, 1))
        .order_by(CalendarEvent.start_at.desc())
        .first()
    )

    if last_event and last_event.start_at:
        last = date(last_event.start_at.year, last_event.start_at.month, 1)
    else:
        last = current

    # +2 meses de buffer para capturar eventos recém-adicionados além do último conhecido
    for _ in range(2):
        last = date(last.year + (last.month // 12), last.month % 12 + 1, 1)

    # Constrói lista de meses a sincronizar
    months: list[date] = []
    m = current
    while m <= last:
        months.append(m)
        m = date(m.year + (m.month // 12), m.month % 12 + 1, 1)

    print(
        f"[sync_worker] {now.strftime('%Y-%m-%d %H:%M')} "
        f"— sincronizando {len(months)} mês(es): "
        f"{months[0].strftime('%Y-%m')} → {months[-1].strftime('%Y-%m')}",
        flush=True,
    )

    errors = 0
    for m in months:
        ym = f"{m.year:04d}-{m.month:02d}"
        try:
            items = fetch_events_for_month(CALENDAR_ID, m.year, m.month)
            sync_events(items)
            _mark_month_synced(ym)
            print(f"  ✓ {ym} — {len(items)} evento(s)", flush=True)
        except Exception as e:
            errors += 1
            print(f"  ✗ {ym} — {e}", file=sys.stderr, flush=True)

    print(f"[sync_worker] Concluído. {errors} erro(s).", flush=True)
    sys.exit(1 if errors else 0)
