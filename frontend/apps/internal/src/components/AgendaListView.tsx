import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Button } from "@manto/ui";
import type { EventoResumo } from "../lib/agenda";
import { eventCategory } from "../lib/eventCategory";
import { dayHeaderLabel } from "../lib/agendaDates";

export interface AgendaListViewProps {
  events: EventoResumo[];
}

function eventTimeLabel(ev: EventoResumo): string {
  if (!ev.start_at) return "";
  const dt = new Date(ev.start_at);
  if (dt.getHours() === 0 && dt.getMinutes() === 0) return "Sem horário definido";
  return dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function AgendaListItem({ event }: { event: EventoResumo }) {
  const cat = eventCategory(event.event_type);
  const time = eventTimeLabel(event);
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2.5">
      {time && (
        <span className="w-24 shrink-0 text-xs tabular-nums text-muted">{time}</span>
      )}
      <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${cat.bg} ${cat.fg}`}>
        {cat.label}
      </span>
      <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{event.title}</span>
      {event.location && (
        <span className="hidden max-w-[200px] truncate text-xs text-muted sm:block">
          {event.location}
        </span>
      )}
      <Button asChild size="sm" variant="outline" className="ml-auto">
        <Link to={`/events/${event.id}`}>Abrir</Link>
      </Button>
    </li>
  );
}

/** Visão em Lista — feed de eventos do período, agrupado por dia (US4). */
export function AgendaListView({ events }: AgendaListViewProps) {
  const withDate = useMemo(() => events.filter((ev) => ev.start_at), [events]);
  const semData = useMemo(() => events.filter((ev) => !ev.start_at), [events]);

  const groups = useMemo(() => {
    const byDay = new Map<string, EventoResumo[]>();
    for (const ev of withDate) {
      const key = (ev.start_at as string).slice(0, 10);
      const list = byDay.get(key) ?? [];
      list.push(ev);
      byDay.set(key, list);
    }
    for (const list of byDay.values()) {
      list.sort((a, b) => (a.start_at! < b.start_at! ? -1 : a.start_at! > b.start_at! ? 1 : 0));
    }
    return [...byDay.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  }, [withDate]);

  if (events.length === 0) {
    return <p className="py-10 text-center text-muted">Nenhum evento neste período.</p>;
  }

  return (
    <div className="space-y-6">
      {groups.map(([day, dayEvents]) => (
        <section key={day} className="space-y-2">
          <h2 className="text-sm font-semibold text-muted">{dayHeaderLabel(day)}</h2>
          <ul className="divide-y divide-line rounded-lg border border-line">
            {dayEvents.map((ev) => (
              <AgendaListItem key={ev.id} event={ev} />
            ))}
          </ul>
        </section>
      ))}

      {semData.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-muted">Sem data</h2>
          <ul className="divide-y divide-line rounded-lg border border-line">
            {semData.map((ev) => (
              <AgendaListItem key={ev.id} event={ev} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
