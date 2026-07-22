import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Input, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { usePagamentos, type PagamentoItem, type PagamentoItemType } from "../lib/financeiro";

const TYPE_LABELS: Record<PagamentoItemType, string> = {
  cache: "Cachê",
  salary: "Salário",
  bv: "BV",
  commission: "Comissão",
  recurring: "Recorrente",
};

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

function TotalCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase text-muted">{label}</p>
        <p className="mt-1 text-lg font-semibold text-ink">{brl(value)}</p>
      </CardContent>
    </Card>
  );
}

function PagamentoRow({ item, statusLabels }: { item: PagamentoItem; statusLabels: Record<string, string> }) {
  const isNegativeLike = item.status === "nao_pago" && item.is_future;
  return (
    <tr className="border-b border-line align-top last:border-0">
      <td className="whitespace-nowrap px-3 py-2">
        <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
          {TYPE_LABELS[item.type]}
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(item.date)}</td>
      <td className="px-3 py-2 text-ink">
        <div>{item.person_name || "—"}</div>
        {item.sublabel && <div className="text-xs text-muted">{item.sublabel}</div>}
      </td>
      <td className="px-3 py-2 text-ink">
        {item.event_id ? (
          <Link to={`/events/${item.event_id}`} className="text-blue hover:underline">
            {item.event_title}
          </Link>
        ) : (
          item.event_title || "—"
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
        {brl(item.amount)}
        {item.type === "salary" && item.advances && item.advances.length > 0 && (
          <details className="mt-1 text-left">
            <summary className="cursor-pointer text-xs text-blue">
              Adiantamentos ({brl(item.advance_amount)})
            </summary>
            <ul className="mt-1 space-y-0.5 text-xs text-muted">
              <li>Bruto: {brl(item.gross_amount)}</li>
              {item.advances.map((a) => (
                <li key={a.id}>
                  {formatDate(a.date)} — {brl(a.amount)}
                  {a.proof ? " (com comprovante)" : ""}
                </li>
              ))}
            </ul>
          </details>
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        <div className="flex flex-wrap gap-1">
          <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
            {statusLabels[item.status] ?? item.status}
          </span>
          {isNegativeLike && (
            <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">Futuro</span>
          )}
          {item.type === "bv" && item.missing_data && (
            <span className="rounded-md bg-red-soft px-1.5 py-0.5 text-xs text-red">
              Dados pendentes
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}

export function PagamentosPage() {
  const [month, setMonth] = useState(currentMonth());
  const query = usePagamentos(month);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <h1 className="text-2xl font-semibold text-ink">Planilha de Pagamentos</h1>

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
          Não foi possível carregar a planilha de pagamentos.
        </div>
      )}

      {query.data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <TotalCard label="Total do mês" value={query.data.totals.total} />
            <TotalCard label="Pago" value={query.data.totals.pago} />
            <TotalCard label="No banco" value={query.data.totals.no_banco} />
            <TotalCard label="Pendente" value={query.data.totals.pendente} />
            <TotalCard label="Futuro" value={query.data.totals.futuro} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Itens do mês</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {query.data.items.length === 0 ? (
                <p className="p-6 text-center text-sm text-muted">
                  Nenhum item de pagamento neste mês.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                        <th className="px-3 py-2">Tipo</th>
                        <th className="px-3 py-2">Data</th>
                        <th className="px-3 py-2">Favorecido</th>
                        <th className="px-3 py-2">Evento</th>
                        <th className="px-3 py-2 text-right">Valor</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {query.data.items.map((item) => (
                        <PagamentoRow
                          key={`${item.type}-${item.id}`}
                          item={item}
                          statusLabels={query.data!.status_labels}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
