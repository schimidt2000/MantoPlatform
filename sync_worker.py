#!/usr/bin/env python3
"""Cron job: sincroniza o Google Calendar com o banco de dados.

Configurar no Railway como novo serviço tipo Cron:
  Comando : python sync_worker.py
  Schedule: */10 * * * *   (a cada 10 minutos)

Lógica:
  - Descobre o mês mais distante com evento no banco (a partir de hoje)
  - Sincroniza todos os meses de hoje até esse mês + 2 meses de buffer
    (o buffer garante que novos eventos adicionados ao Google sejam capturados)
  - Registra o resultado no AuditLog (visível em /admin/logs)
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
    from app.models import CalendarEvent, AuditLog
    from app.calendar.routes import sync_events, CALENDAR_ID, _mark_month_synced, _cleanup_stale_events
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
    month_results = []
    for m in months:
        ym = f"{m.year:04d}-{m.month:02d}"
        try:
            items = fetch_events_for_month(CALENDAR_ID, m.year, m.month)
            sync_events(items)
            removed = _cleanup_stale_events(items, m.year, m.month)
            _mark_month_synced(ym)
            suffix = f" ({removed} removido(s))" if removed else ""
            print(f"  ✓ {ym} — {len(items)} evento(s){suffix}", flush=True)
            month_results.append(f"{ym}: {len(items)} eventos{suffix}")
        except Exception as e:
            errors += 1
            print(f"  ✗ {ym} — {e}", file=sys.stderr, flush=True)
            month_results.append(f"{ym}: ERRO — {e}")

    # Registra resultado no AuditLog para visibilidade em /admin/logs
    status = "ok" if not errors else "erro"
    detail = (
        f"{len(months)} mês(es) sincronizado(s). {errors} erro(s). "
        + " | ".join(month_results[:8])  # limita para não poluir o log
        + (" [...]" if len(month_results) > 8 else "")
    )
    try:
        db.session.add(AuditLog(
            actor_name="sync_worker",
            actor_role="Sistema",
            entity_type="agenda",
            entity_id=None,
            entity_name=f"cron-{now.strftime('%Y-%m-%d %H:%M')}",
            action=f"sync_{status}",
            detail=detail,
        ))
        db.session.commit()
    except Exception as log_exc:
        print(f"  [warn] Não foi possível registrar no AuditLog: {log_exc}", file=sys.stderr, flush=True)

    print(f"[sync_worker] Concluído. {errors} erro(s).", flush=True)
    sys.exit(1 if errors else 0)
