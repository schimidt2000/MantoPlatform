import { Link } from "react-router-dom";
import { Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useVendasPipeline, type VendasPipelineItem } from "../lib/vendas";

function brl(v: number | null | undefined): string {
  if (!v) return "—";
  return `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function Row({ item, isFinanceiro }: { item: VendasPipelineItem; isFinanceiro: boolean }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="whitespace-nowrap px-3 py-2 text-sm text-ink">
        {item.group_label ?? item.title}
        {item.group_label && (
          <span className="ml-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
            grupo
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-sm text-muted">{item.location ?? "—"}</td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-muted">{formatDate(item.sale_date)}</td>
      <td className="whitespace-nowrap px-3 py-2 text-right text-sm tabular-nums text-ink">
        {brl(item.sale_value)}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right text-sm tabular-nums text-ink">
        {brl(item.custo)}
      </td>
      {isFinanceiro && (
        <td
          className={`whitespace-nowrap px-3 py-2 text-right text-sm tabular-nums ${
            (item.lucro ?? 0) < 0 ? "text-red" : (item.lucro ?? 0) > 0 ? "text-green" : "text-ink"
          }`}
        >
          {brl(item.lucro)}
        </td>
      )}
      <td className="whitespace-nowrap px-3 py-2 text-right text-sm tabular-nums text-ink">
        {brl(item.comissao)}
      </td>
      <td className="px-3 py-2 text-center text-sm text-ink">{item.with_invoice ? "✓" : ""}</td>
      <td className="whitespace-nowrap px-3 py-2 text-right">
        <Link to={`/events/${item.event_id}`} className="text-sm text-blue hover:underline">
          Ver
        </Link>
      </td>
    </tr>
  );
}

export function VendasPipelinePage() {
  const query = useVendasPipeline();

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader title="Pipeline de vendas" className="mb-0" />
      <p className="text-sm text-muted">Eventos com dados de venda, custo e comissão.</p>

      {query.isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o pipeline de vendas.
        </div>
      )}

      {query.data && (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            {query.data.items.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted">Nenhum evento encontrado.</p>
            ) : (
              <table className="w-full min-w-[720px] border-collapse">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                    <th className="px-3 py-2">Evento</th>
                    <th className="px-3 py-2">Local</th>
                    <th className="px-3 py-2">Data venda</th>
                    <th className="px-3 py-2 text-right">Venda</th>
                    <th className="px-3 py-2 text-right">Custo</th>
                    {query.data.is_financeiro && <th className="px-3 py-2 text-right">Lucro</th>}
                    <th className="px-3 py-2 text-right">Comissão</th>
                    <th className="px-3 py-2 text-center">NF</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((item) => (
                    <Row key={item.event_id} item={item} isFinanceiro={query.data!.is_financeiro} />
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
