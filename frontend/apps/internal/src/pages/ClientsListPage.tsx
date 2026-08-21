import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { useClients, useClientsMetrics, type ClientsMonthMetric } from "../lib/clientes";
import { NovaClienteDialog } from "../components/NovaClienteDialog";

/** "2026-08" → "ago/26" — rótulo curto do gráfico de novos clientes. */
function monthLabel(month: string): string {
  const NAMES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const [year, m] = month.split("-");
  const idx = Number(m) - 1;
  if (!year || idx < 0 || idx > 11) return month;
  return `${NAMES[idx]}/${year.slice(2)}`;
}

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">{value}</p>
        {hint && <p className="mt-1.5 text-xs text-muted">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function NewClientsChart({ months }: { months: ClientsMonthMetric[] }) {
  const max = Math.max(...months.map((m) => m.total), 1);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Novos clientes por mês</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {months.map((m) => (
          <div key={m.month} className="flex items-center gap-2 text-sm">
            <span className="w-14 shrink-0 text-muted">{monthLabel(m.month)}</span>
            <div className="h-2 flex-1 rounded-full bg-surface-2">
              <div
                className="h-2 rounded-full bg-accent"
                style={{ width: `${(m.total / max) * 100}%` }}
              />
            </div>
            <span
              className="w-10 shrink-0 text-right tabular-nums text-ink"
              title={`Formulário: ${m.formulario} · Kommo: ${m.kommo} · Manual: ${m.manual}`}
            >
              {m.total}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function ClientsListPage() {
  const [q, setQ] = useState("");
  const query = useClients(q);
  const metrics = useClientsMetrics();

  const months = metrics.data?.new_by_month ?? [];
  const currentMonth = new Date().toISOString().slice(0, 7);
  const newThisMonth = months.find((m) => m.month === currentMonth)?.total ?? 0;

  return (
    <div className="mx-auto max-w-[1400px] p-4 sm:p-6">
      <PageHeader
        title="Clientes"
        className="mb-4"
        subtitle={
          query.data ? `${query.data.total_clients} cliente(s) cadastrado(s)` : undefined
        }
        actions={
          <>
            <Button asChild variant="ghost" size="sm">
              <Link to="/clientes/avaliacoes">Avaliações ›</Link>
            </Button>
            <NovaClienteDialog />
          </>
        }
      />

      {/* ── Métricas do negócio (decisão de 06/08/2026): novos por mês + recorrência ── */}
      {metrics.data && (
        <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_1fr_2fr]">
          <div className="grid gap-3">
            <KpiCard
              label="Novos este mês"
              value={String(newThisMonth)}
              hint="clientes que entraram na base"
            />
            <KpiCard
              label="Com evento"
              value={String(metrics.data.clients_with_event)}
              hint="clientes com pelo menos 1 evento"
            />
          </div>
          <KpiCard
            label="Recorrentes"
            value={String(metrics.data.recurring_clients)}
            hint="2+ eventos — alvo natural de recompra"
          />
          <NewClientsChart months={months} />
        </div>
      )}

      {/* Busca não acompanha a largura da página: um campo de 1400px é mais difícil de ler que
          um de 480px, e a grade abaixo é que deve ocupar o espaço horizontal. */}
      <input
        className="mb-4 h-11 w-full max-w-lg rounded-md border border-line bg-panel px-3 text-sm text-ink"
        placeholder="Buscar por nome ou telefone…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Buscar cliente"
      />

      {query.isLoading && (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os clientes.
        </div>
      )}

      {query.data && query.data.items.length === 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-muted">
            {q ? `Nenhum cliente encontrado para "${q}".` : "Nenhum cliente cadastrado ainda."}
          </p>
          <NovaClienteDialog />
        </div>
      )}

      {query.data && query.data.items.length > 0 && (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {query.data.items.map((c) => (
            <Card key={c.id}>
              <CardContent className="flex items-center justify-between gap-3 p-3">
                <div className="min-w-0">
                  <Link to={`/clientes/${c.id}`} className="font-medium text-ink hover:underline">
                    {c.name}
                  </Link>
                  <div className="text-sm text-muted">
                    {[c.phone_display, c.company].filter(Boolean).join(" · ")}
                  </div>
                </div>
                <span className="shrink-0 rounded-md bg-surface-2 px-2 py-1 text-xs text-muted">
                  {c.event_count} evento(s)
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
