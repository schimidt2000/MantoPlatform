import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Input, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useComissoes, type CommissionEntry } from "../lib/financeiro";

function brl(v: number | null | undefined): string {
  if (!v) return "R$ 0,00";
  return `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function CommissionTable({
  entries,
  emptyLabel,
}: {
  entries: CommissionEntry[];
  emptyLabel: string;
}) {
  if (entries.length === 0) {
    return <p className="p-6 text-center text-sm text-muted">{emptyLabel}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
            <th className="px-3 py-2">Vendedor</th>
            <th className="px-3 py-2">Evento</th>
            <th className="px-3 py-2">Data da venda</th>
            <th className="px-3 py-2 text-right">Valor</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Pago em</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id} className="border-b border-line last:border-0">
              <td className="px-3 py-2 text-ink">{e.seller_name}</td>
              <td className="px-3 py-2 text-ink">
                {e.event_id ? (
                  <Link to={`/events/${e.event_id}`} className="text-blue hover:underline">
                    {e.event_title}
                  </Link>
                ) : (
                  e.event_title
                )}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(e.sale_date)}</td>
              <td
                className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
                  e.amount < 0 ? "text-red" : "text-ink"
                }`}
              >
                {brl(e.amount)}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                  {e.status_label}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(e.paid_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ComissoesPage() {
  const [month, setMonth] = useState(currentMonth());
  const query = useComissoes(month);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <h1 className="text-2xl font-semibold text-ink">Comissões</h1>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="h-9 w-40"
        />
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as comissões.
        </div>
      )}

      {query.data && (
        <>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs uppercase text-muted">Total a pagar no mês</p>
              <p className="mt-1 text-xl font-semibold text-ink">{brl(query.data.total_a_pagar)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Comissões do mês</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <CommissionTable
                entries={query.data.entries}
                emptyLabel="Nenhuma comissão neste mês."
              />
            </CardContent>
          </Card>

          {query.data.estornos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Estornos pendentes</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <CommissionTable entries={query.data.estornos} emptyLabel="" />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
