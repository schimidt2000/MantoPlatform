import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { useAgendaDia, type EventoResumo } from "../lib/agenda";
import { computeDayLayout } from "../lib/agendaLayout";
import { eventCategory } from "../lib/eventCategory";

export interface DayTimelineViewProps {
  /** "YYYY-MM-DD" */
  date: string;
}

const HOUR_ROW_PX = 56;
const HOURS = Array.from({ length: 24 }, (_, h) => h);

function eventTimeRange(ev: EventoResumo): string {
  if (!ev.start_at) return "";
  const start = new Date(ev.start_at).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  if (!ev.end_at) return start;
  const end = new Date(ev.end_at).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${start}–${end}`;
}

/** Linha do tempo 00:00–23:00 de um dia, com sobreposição de horários lado a lado (US3). */
export function DayTimelineView({ date }: DayTimelineViewProps) {
  const agendaDia = useAgendaDia(date);
  const events = agendaDia.data?.events ?? [];
  const semHorario = useMemo(() => events.filter((ev) => !ev.start_at), [events]);
  const blocks = useMemo(() => computeDayLayout(events), [events]);

  if (agendaDia.isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (agendaDia.isError) {
    return (
      <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível carregar os eventos do dia. Tente novamente.
      </div>
    );
  }

  if (events.length === 0) {
    return <p className="py-10 text-center text-muted">Nenhum evento neste dia.</p>;
  }

  return (
    <div className="space-y-3">
      {semHorario.length > 0 && (
        <section className="space-y-1.5">
          <h2 className="text-sm font-semibold text-muted">Sem horário</h2>
          <ul className="space-y-1">
            {semHorario.map((ev) => {
              const cat = eventCategory(ev.event_type);
              return (
                <li key={ev.id}>
                  <Link
                    to={`/events/${ev.id}`}
                    className={`inline-flex items-center gap-2 truncate rounded px-2 py-1 text-sm font-medium ${cat.bg} ${cat.fg} hover:opacity-80`}
                  >
                    <span>{cat.label}</span>
                    <span>{ev.title}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="flex overflow-x-auto rounded-lg border border-line">
        <div className="w-12 shrink-0 sm:w-14">
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="border-b border-line px-1 text-right text-[11px] text-muted"
              style={{ height: HOUR_ROW_PX }}
            >
              {String(hour).padStart(2, "0")}:00
            </div>
          ))}
        </div>
        <div
          className="relative min-w-[220px] flex-1"
          style={{ height: HOURS.length * HOUR_ROW_PX }}
        >
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="absolute inset-x-0 border-b border-line"
              style={{ top: hour * HOUR_ROW_PX }}
            />
          ))}
          {blocks.map(({ event, topPct, heightPct, column, columnCount }) => {
            const cat = eventCategory(event.event_type);
            return (
              <Link
                key={event.id}
                to={`/events/${event.id}`}
                title={event.title}
                className={`absolute overflow-hidden rounded px-1.5 py-1 text-[11px] leading-tight shadow-sm ${cat.bg} ${cat.fg} hover:opacity-90`}
                style={{
                  top: `${topPct}%`,
                  height: `${heightPct}%`,
                  left: `${(column / columnCount) * 100}%`,
                  width: `${100 / columnCount}%`,
                }}
              >
                <span className="block font-semibold">{cat.label}</span>
                <span className="block truncate">{event.title}</span>
                <span className="block tabular-nums">{eventTimeRange(event)}</span>
                {event.location && <span className="block truncate">{event.location}</span>}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
