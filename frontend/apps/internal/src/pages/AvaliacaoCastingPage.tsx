import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, Input, PageHeader, Skeleton, StarRating } from "@manto/ui";
import {
  useRatingsOverview,
  useToggleAnonymousMode,
  type RatingComment,
  type RatingsPeriod,
} from "../lib/ratings";

const PERIOD_OPTIONS: { value: RatingsPeriod; label: string }[] = [
  { value: "all", label: "Tudo" },
  { value: "7d", label: "Última semana" },
  { value: "30d", label: "30 dias" },
  { value: "90d", label: "3 meses" },
  { value: "365d", label: "12 meses" },
  { value: "custom", label: "Personalizado" },
];

const DATE_MODE_OPTIONS: { value: "evento" | "avaliacao"; label: string }[] = [
  { value: "evento", label: "Data do evento" },
  { value: "avaliacao", label: "Data da avaliação" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

// Os antigos `StarsInt`/`StarsAvg` desta tela viraram o `StarRating` de `@manto/ui` na feature
// 197 — mesma exibição de nota inteira e de média fracionária, agora compartilhada com o
// dashboard de satisfação das clientes (Princípio I).

function catChip(c: RatingComment): string {
  return c.subject_name ? `${c.cat_label} — ${c.subject_name}` : c.cat_label;
}

function FadeIn({ children, keyId }: { children: ReactNode; keyId: string }) {
  const reduceMotion = useReducedMotion();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={keyId}
        initial={reduceMotion ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduceMotion ? undefined : { opacity: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

function CommentRow({ item, showEventLink, onFocusEvent }: {
  item: RatingComment;
  showEventLink: boolean;
  onFocusEvent: (id: string) => void;
}) {
  return (
    <div className="space-y-1 border-b border-line py-3 last:border-0">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <StarRating value={item.score} size="sm" />
        <span className="rounded-full bg-surface-2 px-2 py-0.5 font-medium text-ink">
          {catChip(item)}
        </span>
        <span className="font-medium text-ink">{item.author}</span>
        {item.author_funcao && <span className="text-muted">· {item.author_funcao}</span>}
        {showEventLink && (
          <button
            type="button"
            onClick={() => onFocusEvent(String(item.event_id))}
            className="text-muted underline-offset-2 hover:text-ink hover:underline"
          >
            · {item.event_title}
          </button>
        )}
        <span className="ml-auto text-muted">{formatDate(item.submitted_at)}</span>
      </div>
      <p className="text-sm text-ink">{item.comment || "Sem comentário."}</p>
    </div>
  );
}

export function AvaliacaoCastingPage() {
  const [period, setPeriod] = useState<RatingsPeriod>("all");
  const [customFromDraft, setCustomFromDraft] = useState("");
  const [customToDraft, setCustomToDraft] = useState("");
  const [appliedCustomRange, setAppliedCustomRange] = useState<{ from: string; to: string } | null>(null);
  const [dateMode, setDateMode] = useState<"evento" | "avaliacao">("evento");
  const [cat, setCat] = useState("");
  const [eventId, setEventId] = useState("");

  const query = useRatingsOverview({
    event_id: eventId || undefined,
    cat: cat || undefined,
    period,
    from: period === "custom" ? appliedCustomRange?.from : undefined,
    to: period === "custom" ? appliedCustomRange?.to : undefined,
    date_mode: dateMode,
  });
  const toggleAnon = useToggleAnonymousMode();

  const data = query.data;
  const hasEventFocus = Boolean(eventId);

  function selectPeriod(value: RatingsPeriod) {
    setPeriod(value);
    setEventId("");
    if (value !== "custom") {
      setCustomFromDraft("");
      setCustomToDraft("");
      setAppliedCustomRange(null);
    }
  }

  function applyCustomRange() {
    if (!customFromDraft && !customToDraft) return;
    setAppliedCustomRange({ from: customFromDraft, to: customToDraft });
  }

  function focusEvent(id: string) {
    setEventId(id);
  }

  function clearFilters() {
    setPeriod("all");
    setCat("");
    setEventId("");
    setDateMode("evento");
    setCustomFromDraft("");
    setCustomToDraft("");
    setAppliedCustomRange(null);
  }

  return (
    <div className="w-full space-y-4 px-6 py-6 sm:px-8">
      <PageHeader
        title="Resumo das Avaliações"
        subtitle="Panorama das avaliações dos eventos — filtre por período, categoria ou evento"
        className="mb-0"
      />

      {data?.is_superadmin && (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-3 p-4">
            <div className="min-w-[240px] flex-1">
              <p className="text-sm font-semibold text-ink">
                Privacidade das avaliações:{" "}
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    data.fully_anonymous ? "bg-surface-2 text-muted" : "bg-blue-soft text-blue"
                  }`}
                >
                  {data.fully_anonymous ? "Anônimo total (ativo)" : "Você vê a autoria"}
                </span>
              </p>
              <p className="mt-1 text-xs text-muted">
                {data.fully_anonymous
                  ? "A autoria está oculta para todos, inclusive para você. Desative para voltar a ver quem avaliou."
                  : "Os comentários são anônimos para os demais usuários; só você (super admin) vê a autoria. Ative o modo anônimo total para ocultar a autoria até para você."}
              </p>
            </div>
            <Button
              size="sm"
              variant={data.fully_anonymous ? "outline" : "default"}
              loading={toggleAnon.isPending}
              onClick={() => {
                const next = !data.fully_anonymous;
                const msg = next
                  ? "Ativar o modo anônimo total? Nem o super admin verá quem fez cada avaliação."
                  : "Desativar o modo anônimo total? A autoria volta a aparecer para o super admin.";
                if (window.confirm(msg)) toggleAnon.mutate(next);
              }}
            >
              {data.fully_anonymous ? "Desativar modo anônimo total" : "Ativar modo anônimo total"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 p-4">
          {!hasEventFocus && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-20 text-xs text-muted">Período:</span>
              {PERIOD_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  size="sm"
                  variant={period === opt.value ? "default" : "outline"}
                  onClick={() => selectPeriod(opt.value)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          )}

          {!hasEventFocus && period === "custom" && (
            <div className="flex flex-wrap items-center gap-2 pl-[88px]">
              <Input
                type="date"
                value={customFromDraft}
                onChange={(e) => setCustomFromDraft(e.target.value)}
                className="h-9 w-40"
              />
              <span className="text-sm text-muted">até</span>
              <Input
                type="date"
                value={customToDraft}
                onChange={(e) => setCustomToDraft(e.target.value)}
                className="h-9 w-40"
              />
              <Button
                size="sm"
                variant="outline"
                disabled={!customFromDraft && !customToDraft}
                onClick={applyCustomRange}
              >
                Aplicar
              </Button>
            </div>
          )}

          {!hasEventFocus && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-20 text-xs text-muted">Filtrar por:</span>
              {DATE_MODE_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  size="sm"
                  variant={dateMode === opt.value ? "default" : "outline"}
                  onClick={() => setDateMode(opt.value)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <span className="w-20 text-xs text-muted">Categoria:</span>
            <Button size="sm" variant={cat === "" ? "default" : "outline"} onClick={() => setCat("")}>
              Todas
            </Button>
            {data?.categories.map((c) => (
              <Button
                key={c.key}
                size="sm"
                variant={cat === c.key ? "default" : "outline"}
                onClick={() => setCat(c.key)}
              >
                {c.label}
              </Button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="w-20 text-xs text-muted">Evento:</span>
            <select
              className="h-10 max-w-md flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
            >
              <option value="">Geral (todos os eventos do recorte)</option>
              {data?.event_groups.map((g) => (
                <optgroup key={g.label} label={g.label}>
                  {g.events.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.start_at ? new Date(ev.start_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "—"} — {ev.title}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            {data?.selected_event && (
              <Button size="sm" variant="outline" asChild>
                <Link to={`/events/${data.selected_event.id}`}>Abrir evento</Link>
              </Button>
            )}
            {data?.has_filters && (
              <Button size="sm" variant="ghost" className="ml-auto" onClick={clearFilters}>
                ✕ Limpar filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {query.isLoading && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as avaliações.
        </div>
      )}

      {data && data.total === 0 && (
        <Card>
          <CardContent className="space-y-3 p-10 text-center text-muted">
            <p className="text-4xl">📋</p>
            <p>
              Nenhuma avaliação
              {data.recorte_label && (
                <>
                  {" "}
                  de <strong className="text-ink">{data.recorte_label}</strong>
                </>
              )}
              {data.selected_event && " neste evento"} encontrada.
            </p>
            {data.has_filters && (
              <Button size="sm" variant="outline" onClick={clearFilters}>
                Limpar filtros
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {data && data.total > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted">
                  Nota média{data.recorte_label ? ` — ${data.recorte_label}` : data.selected_event ? " do evento" : " geral"}
                </p>
                <p className="mt-1 flex items-center gap-2 text-2xl font-semibold text-ink">
                  {data.avg_overall.toFixed(1)}
                  <StarRating value={data.avg_overall} size="lg" />
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted">{cat ? `Avaliações de ${data.cat_label}` : "Total de avaliações"}</p>
                <p className="mt-1 text-2xl font-semibold text-ink">{data.total}</p>
              </CardContent>
            </Card>
            {!data.selected_event && (
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs text-muted">Eventos avaliados</p>
                  <p className="mt-1 text-2xl font-semibold text-ink">{data.events_rated}</p>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <AnimatePresence>
              {data.trend.length >= 2 && !data.selected_event && (
                <FadeIn keyId="trend">
                  <Card>
                    <CardContent className="p-4">
                      <p className="mb-3 text-sm font-semibold text-ink">
                        Tendência mensal <span className="font-normal text-muted">(média por mês do evento)</span>
                      </p>
                      <div className="flex h-32 items-end gap-3 overflow-x-auto pb-1">
                        {data.trend.map((t) => (
                          <div
                            key={t.label}
                            className="flex min-w-[44px] flex-col items-center gap-1"
                            title={`${t.label}: média ${t.avg.toFixed(1)} (${t.count} avaliações)`}
                          >
                            <span className="text-xs font-semibold text-ink">{t.avg.toFixed(1)}</span>
                            <div
                              className="w-6 min-h-[3px] rounded-t-md bg-accent"
                              style={{ height: `${Math.round((t.avg / 5) * 80)}px` }}
                            />
                            <span className="whitespace-nowrap text-[11px] text-muted">{t.label}</span>
                            <span className="text-[10px] text-muted">({t.count})</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </FadeIn>
              )}
            </AnimatePresence>

            <Card>
              <CardContent className="p-4">
                <p className="mb-3 text-sm font-semibold text-ink">
                  Distribuição das notas{cat && ` — ${data.cat_label}`}
                </p>
                {[5, 4, 3, 2, 1].map((s) => {
                  const count = data.dist[String(s)] ?? 0;
                  const pct = data.dist_max ? (count / data.dist_max) * 100 : 0;
                  return (
                    <div key={s} className="mb-2 flex items-center gap-2">
                      <span className="w-12 whitespace-nowrap text-xs text-gold">{s} ★</span>
                      <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                        <div className="h-full rounded-full bg-gold" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="w-8 text-right text-xs font-semibold text-ink">{count}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <AnimatePresence>
              {!cat && data.by_category.length > 0 && (
                <FadeIn keyId="by-category">
                  <Card>
                    <CardContent className="p-4">
                      <p className="mb-3 text-sm font-semibold text-ink">Média por categoria</p>
                      {data.by_category.map((c) => (
                        <div key={c.key} className="mb-3">
                          <div className="mb-1 flex items-center justify-between text-sm">
                            <button
                              type="button"
                              onClick={() => setCat(c.key)}
                              className="font-semibold text-ink hover:underline"
                              title={`Filtrar por ${c.label}`}
                            >
                              {c.label}
                            </button>
                            <span className="text-muted">
                              <StarRating value={c.avg} /> {c.avg.toFixed(1)}{" "}
                              <span className="text-xs">({c.count})</span>
                            </span>
                          </div>
                          <div className="h-2.5 overflow-hidden rounded-full bg-surface-2">
                            <div
                              className="h-full rounded-full bg-accent"
                              style={{ width: `${(c.avg / 5) * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                </FadeIn>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {!data.selected_event && (data.best_events.length > 0 || data.worst_events.length > 0) && (
                <FadeIn keyId="ranking">
                  <Card>
                    <CardContent className="p-4">
                      <p className="mb-2 text-sm font-semibold text-ink">🏆 Melhores eventos</p>
                      {data.best_events.map((e) => (
                        <button
                          key={e.id}
                          type="button"
                          onClick={() => focusEvent(String(e.id))}
                          className="flex w-full items-center gap-2 border-b border-line py-1.5 text-left text-sm last:border-0 hover:bg-surface-2"
                        >
                          <span className="min-w-0 flex-1 truncate">
                            <span className="text-xs text-muted">{formatDate(e.start_at)}</span> {e.title}
                          </span>
                          <span className="whitespace-nowrap">
                            <StarRating value={e.avg} /> <strong>{e.avg.toFixed(1)}</strong>{" "}
                            <span className="text-xs text-muted">({e.count})</span>
                          </span>
                        </button>
                      ))}
                      {data.worst_events.length > 0 && (
                        <>
                          <p className="mb-2 mt-4 text-sm font-semibold text-ink">📉 Pontos a melhorar</p>
                          {data.worst_events.map((e) => (
                            <button
                              key={e.id}
                              type="button"
                              onClick={() => focusEvent(String(e.id))}
                              className="flex w-full items-center gap-2 border-b border-line py-1.5 text-left text-sm last:border-0 hover:bg-surface-2"
                            >
                              <span className="min-w-0 flex-1 truncate">
                                <span className="text-xs text-muted">{formatDate(e.start_at)}</span> {e.title}
                              </span>
                              <span className="whitespace-nowrap">
                                <StarRating value={e.avg} /> <strong>{e.avg.toFixed(1)}</strong>{" "}
                                <span className="text-xs text-muted">({e.count})</span>
                              </span>
                            </button>
                          ))}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </FadeIn>
              )}
            </AnimatePresence>
          </div>

          <Card className={data.attention.length > 0 ? "border-l-4 border-l-red" : "border-l-4 border-l-green"}>
            <CardContent className="p-4">
              <p className="mb-3 text-sm font-semibold text-ink">
                ⚠️ Pontos de atenção <span className="font-normal text-muted">(notas 1-2 do recorte)</span>
              </p>
              {data.attention.length > 0 ? (
                data.attention.map((a, i) => (
                  <div key={i} className="border-b border-line py-2.5 last:border-0">
                    <div className="mb-0.5 flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-bold text-red">{a.score} ★</span>
                      <span className="rounded-full bg-surface-2 px-2 py-0.5 font-medium text-ink">
                        {catChip(a)}
                      </span>
                      <span className="font-semibold text-ink">{a.author}</span>
                      {a.author_funcao && <span className="text-muted">· {a.author_funcao}</span>}
                      {!data.selected_event && a.event_id && (
                        <button
                          type="button"
                          onClick={() => focusEvent(String(a.event_id))}
                          className="text-muted underline-offset-2 hover:text-ink hover:underline"
                        >
                          · {a.event_title}
                        </button>
                      )}
                      <span className="ml-auto text-muted">{formatDate(a.submitted_at)}</span>
                    </div>
                    <div className="text-sm text-ink">{a.comment || <span className="text-muted">Sem comentário.</span>}</div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted">✅ Nenhuma nota baixa no recorte.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <p className="mb-2 text-sm font-semibold text-ink">
                Comentários {!data.selected_event && <span className="font-normal text-muted">(mais recentes)</span>}
              </p>
              {data.comments.length === 0 ? (
                <p className="text-sm text-muted">Nenhum comentário no recorte.</p>
              ) : (
                data.comments.map((c, i) => (
                  <CommentRow
                    key={i}
                    item={c}
                    showEventLink={!data.selected_event}
                    onFocusEvent={focusEvent}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
