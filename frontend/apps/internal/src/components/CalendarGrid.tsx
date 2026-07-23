import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { EventoResumo } from "../lib/agenda";
import { eventCategory } from "../lib/eventCategory";

export interface CalendarGridProps {
  ym: string;
  events: EventoResumo[];
  /** Clique no número do dia ou em área vazia da célula (fora dos eventos) — abre a visão Dia. */
  onDayClick?: (dateKey: string) => void;
}

const WEEKDAY_LABELS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const MAX_VISIBLE_PER_DAY = 3;

interface CalendarCell {
  date: Date;
  key: string;
  inCurrentMonth: boolean;
  isToday: boolean;
  events: EventoResumo[];
}

function toDayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function buildWeeks(ym: string, events: EventoResumo[]): CalendarCell[][] {
  const [year, month] = ym.split("-").map(Number);
  const firstOfMonth = new Date(year, month - 1, 1);
  const lastOfMonth = new Date(year, month, 0);
  const gridStart = new Date(firstOfMonth);
  gridStart.setDate(gridStart.getDate() - gridStart.getDay());
  const gridEnd = new Date(lastOfMonth);
  gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()));

  const eventsByDay = new Map<string, EventoResumo[]>();
  for (const ev of events) {
    if (!ev.start_at) continue;
    const key = ev.start_at.slice(0, 10);
    const list = eventsByDay.get(key) ?? [];
    list.push(ev);
    eventsByDay.set(key, list);
  }

  const todayKey = toDayKey(new Date());
  const cells: CalendarCell[] = [];
  const cursor = new Date(gridStart);
  while (cursor <= gridEnd) {
    const key = toDayKey(cursor);
    cells.push({
      date: new Date(cursor),
      key,
      inCurrentMonth: cursor.getMonth() === month - 1,
      isToday: key === todayKey,
      events: eventsByDay.get(key) ?? [],
    });
    cursor.setDate(cursor.getDate() + 1);
  }

  const weeks: CalendarCell[][] = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
}

function eventTime(ev: EventoResumo): string {
  if (!ev.start_at) return "";
  const dt = new Date(ev.start_at);
  if (dt.getHours() === 0 && dt.getMinutes() === 0) return "";
  return dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function DayCell({ cell, onDayClick }: { cell: CalendarCell; onDayClick?: (dateKey: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? cell.events : cell.events.slice(0, MAX_VISIBLE_PER_DAY);
  const hidden = cell.events.length - visible.length;

  return (
    <div
      role={onDayClick ? "button" : undefined}
      tabIndex={onDayClick ? 0 : undefined}
      onClick={() => onDayClick?.(cell.key)}
      onKeyDown={(e) => {
        if (onDayClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onDayClick(cell.key);
        }
      }}
      className={`flex min-h-[92px] flex-col gap-1 border-b border-r border-line p-1.5 sm:min-h-[110px] ${
        cell.inCurrentMonth ? "bg-panel" : "bg-surface-2"
      } ${onDayClick ? "cursor-pointer hover:bg-surface-2" : ""}`}
    >
      <span
        className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
          cell.isToday
            ? "bg-accent text-white"
            : cell.inCurrentMonth
              ? "text-ink"
              : "text-muted"
        }`}
      >
        {cell.date.getDate()}
      </span>
      <div className="flex flex-col gap-1">
        {visible.map((ev) => {
          const cat = eventCategory(ev.event_type);
          return (
            <Link
              key={ev.id}
              to={`/events/${ev.id}`}
              title={ev.title}
              onClick={(e) => e.stopPropagation()}
              className={`truncate rounded px-1.5 py-0.5 text-[11px] font-medium ${cat.bg} ${cat.fg} hover:opacity-80`}
            >
              {eventTime(ev) && <span className="tabular-nums">{eventTime(ev)} </span>}
              {ev.title}
            </Link>
          );
        })}
        {hidden > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(true);
            }}
            className="truncate rounded px-1.5 py-0.5 text-left text-[11px] font-medium text-muted hover:underline"
          >
            +{hidden}
          </button>
        )}
      </div>
    </div>
  );
}

/** Grade mensal de calendário — feature 174 (substitui a listagem agrupada por dia). */
export function CalendarGrid({ ym, events, onDayClick }: CalendarGridProps) {
  const weeks = useMemo(() => buildWeeks(ym, events), [ym, events]);

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px] overflow-hidden rounded-lg border-l border-t border-line">
        <div className="grid grid-cols-7">
          {WEEKDAY_LABELS.map((label) => (
            <div
              key={label}
              className="border-b border-r border-line bg-surface-2 px-1.5 py-1 text-center text-xs font-medium text-muted"
            >
              {label}
            </div>
          ))}
        </div>
        {weeks.map((week) => (
          <div key={week[0].key} className="grid grid-cols-7">
            {week.map((cell) => (
              <DayCell key={cell.key} cell={cell} onDayClick={onDayClick} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
