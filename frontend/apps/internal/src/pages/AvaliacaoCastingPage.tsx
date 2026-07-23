import { useState } from "react";
import { Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { useRatingsOverview, useToggleAnonymousMode } from "../lib/ratings";

const INPUT = "h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function Stars({ score }: { score: number }) {
  return (
    <span className="tabular-nums text-ink" aria-label={`${score} de 5`}>
      {"★".repeat(score)}
      <span className="text-line">{"★".repeat(5 - score)}</span>
    </span>
  );
}

export function AvaliacaoCastingPage() {
  const [eventId, setEventId] = useState("");
  const [cat, setCat] = useState("");
  const [period, setPeriod] = useState("all");
  const query = useRatingsOverview({ event_id: eventId, cat, period });
  const toggleAnon = useToggleAnonymousMode();

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Avaliação de Casting"
        subtitle="Notas e comentários do elenco por evento"
        className="mb-0"
      />

      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as avaliações.
        </div>
      )}

      {query.data && (
        <>
          <div className="flex flex-wrap gap-2">
            <select className={INPUT} value={eventId} onChange={(e) => setEventId(e.target.value)}>
              <option value="">Todos os eventos</option>
              {query.data.event_groups.map((g) => (
                <optgroup key={g.label} label={g.label}>
                  {g.events.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.title}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <select className={INPUT} value={cat} onChange={(e) => setCat(e.target.value)}>
              <option value="">Todas as categorias</option>
              {query.data.categories.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label}
                </option>
              ))}
            </select>
            <select className={INPUT} value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="all">Todo o período</option>
              <option value="30d">Últimos 30 dias</option>
              <option value="90d">Últimos 3 meses</option>
              <option value="365d">Últimos 12 meses</option>
            </select>
          </div>

          {query.data.is_superadmin && (
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={query.data.fully_anonymous}
                onChange={(e) => toggleAnon.mutate(e.target.checked)}
              />
              Modo anônimo total (esconde a autoria até de mim)
            </label>
          )}

          <div className="grid grid-cols-3 gap-2">
            <Card>
              <CardContent className="p-3">
                <p className="text-xs text-muted">Nota média</p>
                <p className="text-xl font-semibold text-ink">{query.data.avg_overall}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-3">
                <p className="text-xs text-muted">Avaliações</p>
                <p className="text-xl font-semibold text-ink">{query.data.total}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-3">
                <p className="text-xs text-muted">Eventos avaliados</p>
                <p className="text-xl font-semibold text-ink">{query.data.events_rated}</p>
              </CardContent>
            </Card>
          </div>

          {query.data.by_category.length > 0 && (
            <Card>
              <CardContent className="space-y-1 p-3">
                <p className="text-xs font-medium text-muted">Médias por categoria</p>
                {query.data.by_category.map((c) => (
                  <div key={c.key} className="flex items-center justify-between text-sm">
                    <span className="text-ink">{c.label}</span>
                    <span className="tabular-nums text-muted">
                      {c.avg} ({c.count})
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {query.data.attention.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-red">Pontos de atenção</h3>
              {query.data.attention.map((c, i) => (
                <Card key={i}>
                  <CardContent className="space-y-1 p-3">
                    <div className="flex items-center justify-between">
                      <Stars score={c.score} />
                      <span className="text-xs text-muted">{formatDate(c.event_date)}</span>
                    </div>
                    <p className="text-sm text-ink">{c.comment || "(sem comentário)"}</p>
                    <p className="text-xs text-muted">
                      {c.event_title} · {c.author}
                      {c.author_funcao && ` (${c.author_funcao})`} · {c.cat_label}
                      {c.subject_name && ` · ${c.subject_name}`}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted">Comentários</h3>
            {query.data.comments.length === 0 && <p className="text-sm text-muted">Nenhum comentário no recorte.</p>}
            {query.data.comments.map((c, i) => (
              <Card key={i}>
                <CardContent className="space-y-1 p-3">
                  <div className="flex items-center justify-between">
                    <Stars score={c.score} />
                    <span className="text-xs text-muted">{formatDate(c.event_date)}</span>
                  </div>
                  <p className="text-sm text-ink">{c.comment}</p>
                  <p className="text-xs text-muted">
                    {c.event_title} · {c.author}
                    {c.author_funcao && ` (${c.author_funcao})`} · {c.cat_label}
                    {c.subject_name && ` · ${c.subject_name}`}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
