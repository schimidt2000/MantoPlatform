import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Skeleton } from "@manto/ui";
import { useAgendaSearch, type EventoBusca } from "../lib/agenda";
import { todayYmd } from "../lib/agendaDates";
import { AgendaListItem } from "./AgendaListView";

export interface AgendaSearchResultsProps {
  /** Termo já debounced (2+ caracteres) — o hook não dispara abaixo disso. */
  q: string;
}

/** Linha secundária do resultado: `cliente · telefone` (papéis sem vendas recebem null). */
function clientSubtitle(event: EventoBusca): string | undefined {
  const parts = [event.client_name, event.client_phone_display].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : undefined;
}

function ResultGroup({ title, items }: { title: string; items: EventoBusca[] }) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-muted">{title}</h2>
      <ul className="divide-y divide-line rounded-lg border border-line">
        {items.map((event) => (
          <AgendaListItem key={event.id} event={event} subtitle={clientSubtitle(event)} showDate />
        ))}
      </ul>
    </section>
  );
}

/**
 * Resultados do buscador da agenda — substitui as visões Mês/Dia/Lista enquanto há termo.
 *
 * Organização: "Próximos" (de hoje em diante, mais perto primeiro), depois "Anteriores"
 * (mais recente primeiro, como vem do servidor) e "Sem data". Cada linha reusa o visual do
 * feed (`AgendaListItem`) com a cliente na linha secundária.
 */
export function AgendaSearchResults({ q }: AgendaSearchResultsProps) {
  const reduceMotion = useReducedMotion();
  const search = useAgendaSearch(q);

  const groups = useMemo(() => {
    const items = search.data?.items ?? [];
    const today = todayYmd();
    const upcoming = items
      .filter((e) => e.start_at && e.start_at.slice(0, 10) >= today)
      .sort((a, b) => (a.start_at! < b.start_at! ? -1 : 1));
    const past = items.filter((e) => e.start_at && e.start_at.slice(0, 10) < today);
    const semData = items.filter((e) => !e.start_at);
    return { upcoming, past, semData };
  }, [search.data]);

  if (search.isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (search.isError) {
    return (
      <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível buscar. Tente novamente.
      </div>
    );
  }

  const data = search.data;
  if (!data) return null;

  if (data.items.length === 0) {
    return (
      <p className="py-10 text-center text-muted">
        Nenhum evento encontrado para “{q}”.
      </p>
    );
  }

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      className="space-y-6"
    >
      <p className="text-sm text-muted" aria-live="polite">
        {data.total} evento(s) para “{q}”
        {data.total >= data.limit && " — mostrando os primeiros; refine a busca para ver menos resultados"}
      </p>
      <ResultGroup title="Próximos" items={groups.upcoming} />
      <ResultGroup title="Anteriores" items={groups.past} />
      <ResultGroup title="Sem data" items={groups.semData} />
    </motion.div>
  );
}
