import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton } from "@manto/ui";
import { useAgenda } from "../lib/agenda";
import { useCurrentUser } from "../lib/useAuth";
import { CalendarGrid } from "../components/CalendarGrid";

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

/** COMERCIAL/SUPERADMIN podem criar evento (`_CAN_CREATE` — paridade com o Jinja). */
function canCreateEvent(user: { roles: string[]; is_superadmin: boolean } | null | undefined) {
  if (!user) return false;
  return user.is_superadmin || user.roles.includes("COMERCIAL");
}

export function AgendaPage() {
  const reduceMotion = useReducedMotion();
  const [ym, setYm] = useState<string>(currentYm());
  const agenda = useAgenda(ym);
  const currentUser = useCurrentUser();

  const events = agenda.data?.events ?? [];
  const semData = events.filter((ev) => !ev.start_at);

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <PageHeader
        title="Agenda"
        className="mb-5"
        actions={
          <>
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
            {canCreateEvent(currentUser.data) && (
              <Button asChild size="sm">
                <Link to="/events/new">Novo evento</Link>
              </Button>
            )}
          </>
        }
      />

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

      {agenda.data && events.length === 0 && (
        <p className="py-10 text-center text-muted">Nenhum evento neste mês.</p>
      )}

      {agenda.data && events.length > 0 && (
        <motion.div
          key={ym}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          <CalendarGrid ym={ym} events={events} />

          {semData.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-muted">Sem data</h2>
              <ul className="space-y-1">
                {semData.map((ev) => (
                  <li key={ev.id}>
                    <Link
                      to={`/events/${ev.id}`}
                      className="text-sm text-ink hover:underline"
                    >
                      {ev.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </motion.div>
      )}
    </div>
  );
}
