"""Fonte única da sincronização da agenda com o Google Calendar.

Reúne, em um só lugar, a lógica de "sincronizar uma faixa de meses" usada por:
  - a sincronização automática interna (thread de background em ``app/__init__.py``);
  - o script ``sync_worker.py`` (execução manual / backup).

Por mês, a operação é a MESMA do botão "Sincronizar agora" da tela da agenda:
buscar do Google → ``sync_events`` → ``_cleanup_stale_events`` → ``_mark_month_synced``.

Os helpers concretos vivem em ``app/calendar/routes.py``; aqui eles são importados
de forma tardia (dentro das funções) para evitar import circular.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _add_months(d: date, n: int) -> date:
    """Retorna o primeiro dia do mês ``n`` meses após ``d``."""
    month = d.month - 1 + n
    return date(d.year + month // 12, month % 12 + 1, 1)


def run_calendar_sync(lookahead_months: int = 6) -> dict:
    """Sincroniza a agenda com o Google Calendar para uma faixa de meses.

    Deve ser chamada dentro de um contexto de aplicação Flask (``app.app_context()``).

    Sincroniza de hoje até ``lookahead_months`` meses à frente, mais um buffer que
    cobre o evento mais distante já existente no banco. Registra o resultado no
    ``AuditLog`` (visível em /admin/logs).

    Args:
        lookahead_months: Quantos meses à frente sincronizar (padrão 6).

    Returns:
        Dicionário com ``months`` (qtd de meses), ``errors`` (qtd de erros) e
        ``results`` (lista de resumos por mês).
    """
    from app import db
    from app.models import AuditLog, CalendarEvent
    from app.calendar.routes import (
        CALENDAR_ID,
        sync_events,
        _cleanup_stale_events,
        _mark_month_synced,
    )
    from app.calendar.service import fetch_events_for_month

    now = datetime.now()
    current = date(now.year, now.month, 1)
    last = _add_months(current, lookahead_months)

    # Estende o horizonte para cobrir o evento mais distante já no banco (+1 mês de buffer).
    last_event = (
        CalendarEvent.query.filter(CalendarEvent.start_at >= datetime(now.year, now.month, 1))
        .order_by(CalendarEvent.start_at.desc())
        .first()
    )
    if last_event and last_event.start_at:
        last_in_db = _add_months(date(last_event.start_at.year, last_event.start_at.month, 1), 1)
        if last_in_db > last:
            last = last_in_db

    months: list[date] = []
    m = current
    while m <= last:
        months.append(m)
        m = _add_months(m, 1)

    errors = 0
    results: list[str] = []
    for m in months:
        ym = f"{m.year:04d}-{m.month:02d}"
        try:
            items = fetch_events_for_month(CALENDAR_ID, m.year, m.month)
            sync_events(items)
            removed = len(_cleanup_stale_events(items, m.year, m.month))
            _mark_month_synced(ym)
            suffix = f" ({removed} removido(s))" if removed else ""
            results.append(f"{ym}: {len(items)} eventos{suffix}")
        except Exception as exc:  # noqa: BLE001 — um mês com erro não pode abortar os demais
            errors += 1
            results.append(f"{ym}: ERRO — {exc}")

    # feature 126: reprocessa respostas de formulário ainda sem evento vinculado — cobre o
    # caso do evento ter sido criado/importado DEPOIS da resposta já ter chegado.
    linked_count = 0
    try:
        from app.formularios.routes import retry_auto_link_pending
        linked_count = retry_auto_link_pending()
    except Exception:  # noqa: BLE001 — best-effort, não pode derrubar o ciclo de sync
        pass

    status = "ok" if not errors else "erro"
    detail = (
        f"{len(months)} mês(es) sincronizado(s). {errors} erro(s). "
        + (f"{linked_count} resposta(s) de formulário vinculada(s) automaticamente. " if linked_count else "")
        + " | ".join(results[:8])
        + (" [...]" if len(results) > 8 else "")
    )
    try:
        db.session.add(
            AuditLog(
                actor_name="auto-sync",
                actor_role="Sistema",
                entity_type="agenda",
                entity_id=None,
                entity_name=f"cron-{now.strftime('%Y-%m-%d %H:%M')}",
                action=f"sync_{status}",
                detail=detail,
            )
        )
        db.session.commit()
    except Exception:  # noqa: BLE001 — log é best-effort; não pode derrubar o ciclo
        db.session.rollback()

    return {"months": len(months), "errors": errors, "results": results}


def _claim_auto_sync(interval_seconds: int) -> bool:
    """Reivindica o ciclo de sincronização automática de forma atômica.

    Faz um ``UPDATE`` condicional em ``site_settings``: só "ganha" o ciclo se a
    última sincronização automática foi há mais de ``interval_seconds`` (ou nunca).
    Como o ``UPDATE`` é atômico no banco, apenas um processo/worker ganha por ciclo,
    evitando execução concorrente (a coluna ``google_event_id`` é única).

    Args:
        interval_seconds: Intervalo mínimo entre ciclos.

    Returns:
        ``True`` se este processo deve executar o ciclo agora; ``False`` caso outro
        já tenha reivindicado dentro do intervalo.
    """
    from sqlalchemy import text
    from app import db

    now = datetime.utcnow()
    threshold = now - timedelta(seconds=interval_seconds)
    result = db.session.execute(
        text(
            "UPDATE site_settings SET calendar_auto_sync_at = :now "
            "WHERE id = 1 AND (calendar_auto_sync_at IS NULL OR calendar_auto_sync_at < :threshold)"
        ),
        {"now": now, "threshold": threshold},
    )
    db.session.commit()
    return result.rowcount == 1
