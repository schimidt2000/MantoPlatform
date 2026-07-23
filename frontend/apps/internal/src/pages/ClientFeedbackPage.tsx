import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useClientFeedback, type FeedbackPeriod } from "../lib/clientes";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
}

const PERIOD_LABELS: Record<FeedbackPeriod, string> = {
  "30d": "30 dias",
  "90d": "90 dias",
  "365d": "365 dias",
  custom: "Personalizado",
  all: "Todos",
};

export function ClientFeedbackPage() {
  const [period, setPeriod] = useState<FeedbackPeriod>("all");
  const [score, setScore] = useState<number | undefined>(undefined);
  const [tag, setTag] = useState<string | undefined>(undefined);
  const [clientId, setClientId] = useState<number | undefined>(undefined);

  const query = useClientFeedback({ period, score, tag, client_id: clientId });
  const data = query.data;
  const hasFilters = period !== "all" || Boolean(score) || Boolean(tag) || Boolean(clientId);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>

      <PageHeader title="Avaliações das clientes" className="mb-0" />

      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={period}
          onChange={(e) => setPeriod(e.target.value as FeedbackPeriod)}
          aria-label="Período"
        >
          {(Object.entries(PERIOD_LABELS) as [FeedbackPeriod, string][]).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={score ?? ""}
          onChange={(e) => setScore(e.target.value ? Number(e.target.value) : undefined)}
          aria-label="Nota"
        >
          <option value="">Todas as notas</option>
          {[1, 2, 3, 4, 5].map((s) => (
            <option key={s} value={s}>
              {s} estrela(s)
            </option>
          ))}
        </select>
        {data && data.all_tags.length > 0 && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
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
        {data && data.clients_with_feedback.length > 0 && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={clientId ?? ""}
            onChange={(e) => setClientId(e.target.value ? Number(e.target.value) : undefined)}
            aria-label="Cliente"
          >
            <option value="">Todos os clientes</option>
            {data.clients_with_feedback.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setPeriod("all");
              setScore(undefined);
              setTag(undefined);
              setClientId(undefined);
            }}
          >
            Limpar filtros
          </Button>
        )}
      </div>

      {query.isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as avaliações.
        </div>
      )}

      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-2xl font-semibold text-ink">{data.total}</p>
                <p className="text-sm text-muted">avaliações</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-2xl font-semibold text-ink">{data.avg_overall.toFixed(1)}</p>
                <p className="text-sm text-muted">média geral</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-2xl font-semibold text-ink">{data.clients_rated}</p>
                <p className="text-sm text-muted">clientes avaliadas</p>
              </CardContent>
            </Card>
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
                      <div
                        className="h-2 rounded-full bg-accent"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-6 shrink-0 text-right text-ink">{count}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {data.attention.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Atenção (notas baixas)</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-line">
                  {data.attention.map((f) => (
                    <li key={f.id} className="py-1.5 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-ink">{f.event_title}</span>
                        <span className="text-muted">{formatDate(f.submitted_at)}</span>
                      </div>
                      <span className="text-xs text-red">{f.score} estrela(s)</span>
                      {f.tags.length > 0 && (
                        <span className="ml-2 text-xs text-muted">{f.tags.join(", ")}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {data.feedbacks.length === 0 && (
            <p className="text-sm text-muted">Nenhuma avaliação encontrada.</p>
          )}
        </>
      )}
    </div>
  );
}
