import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton } from "@manto/ui";
import { useAgenda } from "../lib/agenda";
import { useCurrentUser } from "../lib/useAuth";
import { CalendarGrid } from "../components/CalendarGrid";
import { AgendaToolbar } from "../components/AgendaToolbar";
import { DayTimelineView } from "../components/DayTimelineView";
import { AgendaListView } from "../components/AgendaListView";
import { AgendaSearchResults } from "../components/AgendaSearchResults";
import {
  type AgendaViewMode,
  shiftDay,
  shiftMonth,
  todayYmd,
  ymOf,
} from "../lib/agendaDates";

/** Espera de digitação antes de refletir a busca na URL (e disparar a query). */
const SEARCH_DEBOUNCE_MS = 300;

/** COMERCIAL/SUPERADMIN podem criar evento (`_CAN_CREATE` — paridade com o Jinja). */
function canCreateEvent(
  user: { roles: string[]; is_superadmin: boolean } | null | undefined,
) {
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
  const q = searchParams.get("q") ?? "";

  // Campo controlado localmente + debounce para a URL: digitar não pode disparar uma query
  // por tecla, e limpar o campo remove `q` da URL — a página volta à visão anterior
  // (view/date continuam nos params). O timeout captura `searchInput` fresco por render —
  // sem o bug de stale-closure já registrado no projeto.
  const [searchInput, setSearchInput] = useState(q);
  // Último `q` que ESTE componente empurrou para a URL — distingue mudança própria (debounce)
  // de mudança externa (clique em "Agenda" na sidebar, botão voltar). Sem isso, sair do modo
  // busca pela sidebar não funcionava: `q` virava "" mas o debounce reescrevia o termo antigo.
  const lastPushedQRef = useRef(q);
  useEffect(() => {
    if (searchInput === q) return;
    const timer = setTimeout(() => {
      const params = new URLSearchParams(searchParams);
      if (searchInput.trim()) {
        params.set("q", searchInput);
      } else {
        params.delete("q");
      }
      lastPushedQRef.current = searchInput.trim() ? searchInput : "";
      setSearchParams(params, { replace: true });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput, q, searchParams, setSearchParams]);

  // Sincronização URL → campo, SÓ para mudanças externas (a própria digitação não pode ser
  // clobberada quando o debounce de um termo intermediário aterrissa).
  useEffect(() => {
    if (q !== lastPushedQRef.current) {
      lastPushedQRef.current = q;
      setSearchInput(q);
    }
  }, [q]);

  const searching = q.trim().length >= 2;

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
            onDateChange={(date) => updateParams({ date })}
            searchValue={searchInput}
            onSearchChange={setSearchInput}
          />
        }
      />

      <motion.div
        // Key constante durante a busca: incluir o `q` remontava a árvore a cada termo
        // debounced e anulava o keepPreviousData (flash de skeleton por refinamento).
        key={searching ? "search" : `${view}-${view === "day" ? refDate : ym}`}
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        {searching ? (
          <AgendaSearchResults q={q.trim()} />
        ) : (
          <>
            {view === "day" && <DayTimelineView date={refDate} />}

            {view !== "day" && agenda.isLoading && (
              <div className="space-y-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            )}

            {view !== "day" && agenda.isError && (
              <div
                className="rounded-md bg-red-soft px-4 py-3 text-sm text-red"
                role="alert"
              >
                Não foi possível carregar a agenda. Tente novamente.
              </div>
            )}

            {view === "month" && agenda.data && events.length === 0 && (
              <p className="py-10 text-center text-muted">
                Nenhum evento neste mês.
              </p>
            )}

            {view === "month" && agenda.data && events.length > 0 && (
              <div className="space-y-4">
                <CalendarGrid
                  ym={ym}
                  events={events}
                  onDayClick={(dateKey) =>
                    updateParams({ view: "day", date: dateKey })
                  }
                />

                {semData.length > 0 && (
                  <section className="space-y-2">
                    <h2 className="text-sm font-semibold text-muted">
                      Sem data
                    </h2>
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
              </div>
            )}

            {view === "list" && agenda.data && (
              <AgendaListView events={events} />
            )}
          </>
        )}
      </motion.div>
    </div>
  );
}
