import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Card, Skeleton } from "@manto/ui";
import { useAgenda, type EventoResumo } from "../lib/agenda";

function currentYm(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function shiftYm(ym: string, delta: number): string {
  const [y, m] = ym.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  const label = new Date(y, m - 1, 1).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function dayLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function eventTime(ev: EventoResumo): string {
  if (!ev.start_at) return "";
  const dt = new Date(ev.start_at);
  if (dt.getHours() === 0 && dt.getMinutes() === 0) return "";
  return dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function EventCard({ ev }: { ev: EventoResumo }) {
  return (
    <Card className="flex flex-col gap-1 p-4">
      <div className="flex items-start justify-between gap-3">
        <span className="font-medium text-ink">{ev.title}</span>
        {eventTime(ev) && (
          <span className="shrink-0 text-sm tabular-nums text-muted">{eventTime(ev)}</span>
        )}
      </div>
      {ev.location && <span className="text-sm text-muted">{ev.location}</span>}
      <div className="mt-1 flex flex-wrap gap-1.5">
        <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
          {ev.event_type}
        </span>
        {ev.confirmed && (
          <span className="rounded-md bg-green-soft px-2 py-0.5 text-xs text-green">
            Confirmado
          </span>
        )}
        {ev.is_satellite && (
          <span className="rounded-md bg-blue-soft px-2 py-0.5 text-xs text-blue">Satélite</span>
        )}
        {ev.group_name && (
          <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
            {ev.group_name}
          </span>
        )}
      </div>
    </Card>
  );
}

export function AgendaPage() {
  const reduceMotion = useReducedMotion();
  const [ym, setYm] = useState<string>(currentYm());
  const agenda = useAgenda(ym);

  // Agrupa os eventos por dia de início, em ordem cronológica.
  const groups = useMemo(() => {
    const events = agenda.data?.events ?? [];
    const byDay = new Map<string, EventoResumo[]>();
    for (const ev of events) {
      const key = ev.start_at ? ev.start_at.slice(0, 10) : "sem-data";
      const list = byDay.get(key) ?? [];
      list.push(ev);
      byDay.set(key, list);
    }
    return [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [agenda.data]);

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <header className="mb-5 flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-ink">Agenda</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setYm(shiftYm(ym, -1))}>
            ‹
          </Button>
          <span className="min-w-40 text-center text-sm font-medium text-ink">
            {monthLabel(ym)}
          </span>
          <Button variant="outline" size="sm" onClick={() => setYm(shiftYm(ym, 1))}>
            ›
          </Button>
        </div>
      </header>

      {agenda.isLoading && (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {agenda.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a agenda. Tente novamente.
        </div>
      )}

      {agenda.data && groups.length === 0 && (
        <p className="py-10 text-center text-muted">Nenhum evento neste mês.</p>
      )}

      {agenda.data && groups.length > 0 && (
        <motion.div
          key={ym}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-6"
        >
          {groups.map(([day, events]) => (
            <section key={day} className="space-y-2">
              <h2 className="text-sm font-semibold text-muted">
                {day === "sem-data" ? "Sem data" : dayLabel(day)}
              </h2>
              <div className="space-y-2">
                {events.map((ev) => (
                  <EventCard key={ev.id} ev={ev} />
                ))}
              </div>
            </section>
          ))}
        </motion.div>
      )}
    </div>
  );
}
