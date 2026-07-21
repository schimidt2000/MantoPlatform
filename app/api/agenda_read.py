"""Serialização de leitura da Agenda/Eventos (feature 145, US1).

Fonte única do formato JSON de leitura consumido pela SPA React. Nesta fatia cobre apenas o
RESUMO do evento (agenda); o detalhe do evento (com RBAC financeiro) entra no Incremento B.
Reaproveita os parsers e a query de mês da view Jinja (Princípio I) — não duplica lógica.
"""

from typing import Any

from app.models import CalendarEvent


def serialize_event_summary(event: CalendarEvent) -> dict[str, Any]:
    """Resumo de um evento para a lista/calendário da agenda (data-model.md: EventoResumo).

    Sem nenhum dado financeiro — a agenda não expõe valores.
    """
    # Import tardio: parsers vivem no blueprint calendar (evita import circular no boot).
    from app.calendar.routes import parse_characters, parse_event_type

    return {
        "id": event.id,
        "title": event.title,
        "event_type": parse_event_type(event.title),
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "location": event.location or None,
        "characters": parse_characters(event.title),
        "is_satellite": event.is_satellite,
        "group_name": event.group_name or None,
        "confirmed": event.confirmed_at is not None,
    }


def build_agenda_month(year: int, month: int) -> dict[str, Any]:
    """Monta a resposta da agenda de um mês: eventos + índice por dia (para o calendário).

    Usa a mesma query da view (`_query_month_events`), então o conjunto de eventos é idêntico
    ao que o sistema atual mostra. `by_day` espalha eventos de vários dias por todos os dias
    que eles cobrem dentro do mês (como o calendário Jinja).
    """
    from app.calendar.routes import _query_month_events

    events = _query_month_events(year, month)
    summaries = [serialize_event_summary(e) for e in events]

    by_day: dict[str, list[int]] = {}
    for event in events:
        if not event.start_at:
            continue
        start_day = event.start_at.date()
        end_day = event.end_at.date() if event.end_at else start_day
        cursor = start_day
        while cursor <= end_day:
            if cursor.year == year and cursor.month == month:
                by_day.setdefault(cursor.isoformat(), []).append(event.id)
            cursor = cursor.fromordinal(cursor.toordinal() + 1)

    return {"ym": f"{year:04d}-{month:02d}", "events": summaries, "by_day": by_day}
