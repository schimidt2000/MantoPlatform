import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { CalendarDays, MessageSquareDashed, Search, Star, Trash2, TrendingUp } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  PageHeader,
  Skeleton,
  StarRating,
  formatRelativeDay,
  formatShortDate,
} from "@manto/ui";
import {
  useClientFeedback,
  useDeleteClientFeedback,
  type ClientFeedbackItem,
  type FeedbackPeriod,
} from "../lib/clientes";

const PERIOD_LABELS: Record<FeedbackPeriod, string> = {
  "30d": "Últimos 30 dias",
  "90d": "Últimos 90 dias",
  "365d": "Últimos 365 dias",
  custom: "Personalizado",
  all: "Todo o período",
};

/**
 * Faixas de nota do filtro. `3 ou menos` não cabe no parâmetro `score` do servidor (que só
 * aceita nota exata), então o recorte por nota é feito no cliente sobre a lista já carregada
 * — mesmo lugar onde a busca textual e a ordenação acontecem.
 */
const SCORE_BANDS = {
  all: { label: "Todas as notas", match: () => true },
  "5": { label: "5 estrelas", match: (s: number) => s === 5 },
  "4": { label: "4 estrelas", match: (s: number) => s === 4 },
  low: { label: "3 ou menos (atenção)", match: (s: number) => s <= 3 },
} as const;

type ScoreBand = keyof typeof SCORE_BANDS;

const SORT_OPTIONS = {
  recent: "Mais recentes",
  best: "Maior nota",
  worst: "Menor nota",
} as const;

type SortOrder = keyof typeof SORT_OPTIONS;

const SELECT_CLASS =
  "h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-ring";

/** Minúsculas e sem acento — busca textual tolerante, como o `strip_accents_lower` do backend. */
function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/** Texto pesquisável de uma avaliação: nome da cliente + título do evento. */
function searchHaystack(item: ClientFeedbackItem): string {
  return normalize(`${item.client?.full_name ?? ""} ${item.event?.title ?? ""}`);
}

function scoreTone(score: number): "green" | "gold" | "red" {
  if (score >= 5) return "green";
  if (score >= 4) return "gold";
  return "red";
}

function KpiCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string;
  hint?: ReactNode;
  icon: ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">{value}</p>
          {hint && <div className="mt-1.5 flex items-center gap-1.5 text-xs text-muted">{hint}</div>}
        </div>
        <span className="rounded-md bg-accent-soft p-2 text-accent" aria-hidden="true">
          {icon}
        </span>
      </CardContent>
    </Card>
  );
}

/** Card de uma avaliação: nota em estrelas, cliente, evento (com link) e comentário. */
function FeedbackCard({ item, canDelete }: { item: ClientFeedbackItem; canDelete: boolean }) {
  // Exclusão manual (SUPERADMIN) com confirmação inline em duas etapas — padrão
  // FormulariosAdminPage; o servidor valida o papel de novo no DELETE.
  const deleteFeedback = useDeleteClientFeedback();
  const [confirming, setConfirming] = useState(false);
  return (
    <Card className="flex h-full flex-col">
      <CardContent className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <StarRating value={item.score} />
            <Badge tone={scoreTone(item.score)}>{item.score}/5</Badge>
          </div>
          <span className="flex shrink-0 items-center gap-1">
            <span className="text-xs text-muted" title={formatShortDate(item.submitted_at)}>
              {formatRelativeDay(item.submitted_at) || formatShortDate(item.submitted_at)}
            </span>
            {canDelete && !confirming && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-1.5 text-muted hover:text-red"
                aria-label="Excluir avaliação"
                onClick={() => setConfirming(true)}
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            )}
          </span>
        </div>

        {confirming && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-red bg-red-soft p-2 text-sm">
            <span className="text-red">Excluir esta avaliação? A ação não pode ser desfeita.</span>
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              loading={deleteFeedback.isPending}
              onClick={() =>
                deleteFeedback.mutate(item.id, { onSettled: () => setConfirming(false) })
              }
            >
              Excluir
            </Button>
          </div>
        )}

        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">
            {item.client?.full_name || "Cliente não identificada"}
          </p>
          {item.event ? (
            <Link
              to={`/events/${item.event.id}`}
              className="mt-0.5 flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              <CalendarDays className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {/* `min-w-0`: sem isso o item flex não encolhe abaixo do texto e o `truncate` não corta. */}
              <span className="min-w-0 truncate">{item.event.title}</span>
              <span className="shrink-0 text-muted">· {formatShortDate(item.event.event_date)}</span>
            </Link>
          ) : (
            <p className="mt-0.5 text-sm text-muted">Evento removido</p>
          )}
        </div>

        {item.comment ? (
          <blockquote className="border-l-2 border-line pl-3 text-sm leading-relaxed text-ink">
            {item.comment}
          </blockquote>
        ) : (
          <p className="text-sm italic text-muted">Sem comentário escrito.</p>
        )}

        {item.tags.length > 0 && (
          <div className="mt-auto flex flex-wrap gap-1 pt-1">
            {item.tags.map((tag) => (
              <Badge key={tag} tone="neutral">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-line bg-panel px-6 py-14 text-center">
      <MessageSquareDashed className="h-10 w-10 text-line" aria-hidden="true" />
      <p className="mt-3 font-semibold text-ink">Nenhuma avaliação encontrada</p>
      <p className="mt-1 max-w-sm text-sm text-muted">
        {filtered
          ? "Nenhuma avaliação corresponde aos filtros aplicados. Tente ampliar o período ou limpar a busca."
          : "Assim que as clientes responderem o link de avaliação enviado após o evento, os feedbacks aparecem aqui."}
      </p>
    </div>
  );
}

export function ClientFeedbackPage() {
  const [period, setPeriod] = useState<FeedbackPeriod>("all");
  const [tag, setTag] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [band, setBand] = useState<ScoreBand>("all");
  const [sort, setSort] = useState<SortOrder>("recent");
  const reduceMotion = useReducedMotion();

  const query = useClientFeedback({ period, tag });
  const data = query.data;

  const visible = useMemo(() => {
    const items = data?.feedbacks ?? [];
    const term = normalize(search.trim());
    const matchBand = SCORE_BANDS[band].match;
    const filtered = items.filter(
      (item) => matchBand(item.score) && (!term || searchHaystack(item).includes(term)),
    );
    const byDate = (item: ClientFeedbackItem) =>
      item.submitted_at ? new Date(item.submitted_at).getTime() : 0;
    return [...filtered].sort((a, b) => {
      if (sort === "best" && a.score !== b.score) return b.score - a.score;
      if (sort === "worst" && a.score !== b.score) return a.score - b.score;
      return byDate(b) - byDate(a);
    });
  }, [data?.feedbacks, search, band, sort]);

  const hasFilters = period !== "all" || Boolean(tag) || band !== "all" || search.trim() !== "";

  function clearFilters() {
    setPeriod("all");
    setTag(undefined);
    setBand("all");
    setSearch("");
    setSort("recent");
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>

      <PageHeader
        title="Satisfação das clientes"
        subtitle="Avaliações enviadas pelas clientes após cada evento"
        className="mb-0"
      />

      {query.isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </div>
          <Skeleton className="h-12 w-full" />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-44 w-full" />
            <Skeleton className="h-44 w-full" />
            <Skeleton className="h-44 w-full" />
          </div>
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as avaliações.{" "}
          <button type="button" className="font-semibold underline" onClick={() => query.refetch()}>
            Tentar novamente
          </button>
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <KpiCard
              label="Nota média geral"
              value={`${data.kpis.media_geral.toFixed(1)} / 5.0`}
              hint={<StarRating value={data.kpis.media_geral} size="sm" />}
              icon={<Star className="h-5 w-5" />}
            />
            <KpiCard
              label="Total de avaliações"
              value={String(data.kpis.total_avaliacoes)}
              hint={<span>{data.clients_rated} clientes avaliadas</span>}
              icon={<MessageSquareDashed className="h-5 w-5" />}
            />
            <KpiCard
              label="Índice de excelência"
              value={`${data.kpis.percentual_5_estrelas.toFixed(1)}%`}
              hint={<span>{data.dist["5"] ?? 0} avaliações com 5 estrelas</span>}
              icon={<TrendingUp className="h-5 w-5" />}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Distribuição por nota</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {[5, 4, 3, 2, 1].map((s) => {
                const count = data.dist[String(s)] ?? 0;
                const pct = data.dist_max > 0 ? (count / data.dist_max) * 100 : 0;
                return (
                  <div key={s} className="flex items-center gap-2 text-sm">
                    <span className="w-16 shrink-0 text-muted">{s} estrela(s)</span>
                    <div className="h-2 flex-1 rounded-full bg-surface-2">
                      <div className="h-2 rounded-full bg-accent" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-6 shrink-0 text-right tabular-nums text-ink">{count}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-0 flex-1 sm:max-w-xs">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                aria-hidden="true"
              />
              <Input
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por cliente ou evento…"
                aria-label="Buscar por cliente ou evento"
              />
            </div>
            <select
              className={SELECT_CLASS}
              value={band}
              onChange={(e) => setBand(e.target.value as ScoreBand)}
              aria-label="Filtrar por nota"
            >
              {(Object.entries(SCORE_BANDS) as [ScoreBand, { label: string }][]).map(
                ([value, { label }]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ),
              )}
            </select>
            <select
              className={SELECT_CLASS}
              value={sort}
              onChange={(e) => setSort(e.target.value as SortOrder)}
              aria-label="Ordenar avaliações"
            >
              {(Object.entries(SORT_OPTIONS) as [SortOrder, string][]).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <select
              className={SELECT_CLASS}
              value={period}
              onChange={(e) => setPeriod(e.target.value as FeedbackPeriod)}
              aria-label="Período"
            >
              {(Object.entries(PERIOD_LABELS) as [FeedbackPeriod, string][]).map(
                ([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ),
              )}
            </select>
            {data.all_tags.length > 0 && (
              <select
                className={SELECT_CLASS}
                value={tag ?? ""}
                onChange={(e) => setTag(e.target.value || undefined)}
                aria-label="Tag"
              >
                <option value="">Todas as tags</option>
                {data.all_tags.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            )}
            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Limpar filtros
              </Button>
            )}
          </div>

          <p className="text-sm text-muted" aria-live="polite">
            {visible.length === data.feedbacks.length
              ? `${visible.length} avaliação(ões)`
              : `${visible.length} de ${data.feedbacks.length} avaliação(ões)`}
            {query.isFetching && " · atualizando…"}
          </p>

          {/*
            Transição no bloco inteiro, com `key` no recorte atual — e não uma animação de saída
            por card. Animar a saída item a item deixaria o card removido no DOM até a animação
            terminar, e a lista exibida discordaria do contador enquanto isso.
          */}
          <motion.div
            key={`${search}|${band}|${sort}|${period}|${tag ?? ""}`}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            {visible.length === 0 ? (
              <EmptyState filtered={hasFilters} />
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {visible.map((item) => (
                  <FeedbackCard key={item.id} item={item} canDelete={Boolean(data?.can_delete)} />
                ))}
              </div>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
