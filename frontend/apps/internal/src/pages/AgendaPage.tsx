import { Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton } from "@manto/ui";
import { useAgenda } from "../lib/agenda";
import { useCurrentUser } from "../lib/useAuth";
import { CalendarGrid } from "../components/CalendarGrid";
import { AgendaToolbar } from "../components/AgendaToolbar";
import { DayTimelineView } from "../components/DayTimelineView";
import { AgendaListView } from "../components/AgendaListView";
import { type AgendaViewMode, shiftDay, shiftMonth, todayYmd, ymOf } from "../lib/agendaDates";

/** COMERCIAL/SUPERADMIN podem criar evento (`_CAN_CREATE` — paridade com o Jinja). */
function canCreateEvent(user: { roles: string[]; is_superadmin: boolean } | null | undefined) {
  if (!user) return false;
  return user.is_superadmin || user.roles.includes("COMERCIAL");
}

export function AgendaPage() {
  const reduceMotion = useReducedMotion();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentUser = useCurrentUser();

  const view = (searchParams.get("view") as AgendaViewMode | null) ?? "month";
  const refDate = searchParams.get("date") ?? todayYmd();
  const ym = ymOf(refDate);

  const agenda = useAgenda(ym);
  const events = agenda.data?.events ?? [];
  const semData = events.filter((ev) => !ev.start_at);

  function updateParams(next: { view?: AgendaViewMode; date?: string }) {
    const params = new URLSearchParams(searchParams);
    if (next.view) params.set("view", next.view);
    if (next.date) params.set("date", next.date);
    setSearchParams(params, { replace: true });
  }

  function handleNavigate(delta: -1 | 1) {
    if (view === "day") {
      updateParams({ date: shiftDay(refDate, delta) });
    } else {
      updateParams({ date: `${shiftMonth(ym, delta)}-01` });
    }
  }

  return (
    <div className="w-full p-4 sm:p-6">
      <PageHeader
        title="Agenda"
        actions={
          canCreateEvent(currentUser.data) ? (
            <Button asChild size="sm">
              <Link to="/events/new">Novo evento</Link>
            </Button>
          ) : undefined
        }
        filters={
          <AgendaToolbar
            view={view}
            refDate={refDate}
            onViewChange={(next) => updateParams({ view: next })}
            onNavigate={handleNavigate}
            onToday={() => updateParams({ date: todayYmd() })}
          />
        }
      />

      <motion.div
        key={`${view}-${view === "day" ? refDate : ym}`}
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        {view === "day" && <DayTimelineView date={refDate} />}

        {view !== "day" && agenda.isLoading && (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        )}

        {view !== "day" && agenda.isError && (
          <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
            Não foi possível carregar a agenda. Tente novamente.
          </div>
        )}

        {view === "month" && agenda.data && events.length === 0 && (
          <p className="py-10 text-center text-muted">Nenhum evento neste mês.</p>
        )}

        {view === "month" && agenda.data && events.length > 0 && (
          <div className="space-y-4">
            <CalendarGrid
              ym={ym}
              events={events}
              onDayClick={(dateKey) => updateParams({ view: "day", date: dateKey })}
            />

            {semData.length > 0 && (
              <section className="space-y-2">
                <h2 className="text-sm font-semibold text-muted">Sem data</h2>
                <ul className="space-y-1">
                  {semData.map((ev) => (
                    <li key={ev.id}>
                      <Link to={`/events/${ev.id}`} className="text-sm text-ink hover:underline">
                        {ev.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}

        {view === "list" && agenda.data && <AgendaListView events={events} />}
      </motion.div>
    </div>
  );
}
