import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AccordionRow,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  Button,
  Input,
  MetricBadge,
  PageHeader,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  exportComissoesCsv,
  useComissoes,
  usePagarMesComissao,
  type CommissionEntry,
  type CommissionMonthSummaryRow,
  type CommissionStatus,
} from "../lib/financeiro";

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

function monthLabel(month: string): string {
  const [year, mon] = month.split("-");
  const date = new Date(Number(year), Number(mon) - 1, 1);
  return date.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
}

function EntryRow({ entry }: { entry: CommissionEntry }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(entry.sale_date)}</td>
      <td className="px-3 py-2 text-ink">
        {entry.event_id ? (
          <Link to={`/events/${entry.event_id}`} className="text-blue hover:underline">
            {entry.event_title}
          </Link>
        ) : (
          entry.event_title
        )}
      </td>
      <td
        className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
          entry.amount < 0 ? "text-red" : "text-ink"
        }`}
      >
        {brl(entry.amount)}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
          {entry.status_label}
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(entry.paid_at)}</td>
    </tr>
  );
}

interface PayoutDialogProps {
  row: CommissionMonthSummaryRow;
  month: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function PayoutDialog({ row, month, open, onOpenChange }: PayoutDialogProps) {
  const payout = usePagarMesComissao();

  const handleConfirm = () => {
    payout.mutate(
      { seller_id: row.seller_id, month },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !payout.isPending && onOpenChange(next)}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>Confirmar pagamento</DialogTitle>
          <DialogDescription>
            Confirmar pagamento de <strong className="text-ink">{brl(row.pending_amount)}</strong>{" "}
            para <strong className="text-ink">{row.seller_name}</strong> relativo ao mês{" "}
            <strong className="text-ink">{month}</strong>?
          </DialogDescription>
        </DialogHeader>
        {payout.isError && (
          <p className="mb-2 text-sm text-red" role="alert">
            Não foi possível concluir o pagamento. Tente novamente.
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={payout.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} loading={payout.isPending}>
            Confirmar pagamento
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SellerSummaryRow({ row, month }: { row: CommissionMonthSummaryRow; month: string }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const isPending = row.month_status === "pendente";

  return (
    <>
      <AccordionRow
        className="px-3 py-3"
        summary={
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium text-ink">{row.seller_name}</p>
              <p className="text-xs text-muted">{row.sale_count} venda(s)</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold tabular-nums text-ink">{brl(row.total_amount)}</p>
              <MetricBadge tone={isPending ? "gold" : "green"}>
                {isPending ? "Pendente" : "Pago"}
              </MetricBadge>
            </div>
          </div>
        }
        actions={
          isPending && (
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              Pagar Mês ({brl(row.pending_amount)})
            </Button>
          )
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-xs">
            <thead>
              <tr className="border-b border-line text-left uppercase text-muted">
                <th className="px-3 py-1.5">Data</th>
                <th className="px-3 py-1.5">Evento</th>
                <th className="px-3 py-1.5 text-right">Valor</th>
                <th className="px-3 py-1.5">Status</th>
                <th className="px-3 py-1.5">Pago em</th>
              </tr>
            </thead>
            <tbody>
              {row.entries.map((e) => (
                <EntryRow key={e.id} entry={e} />
              ))}
            </tbody>
          </table>
        </div>
      </AccordionRow>
      {isPending && <PayoutDialog row={row} month={month} open={dialogOpen} onOpenChange={setDialogOpen} />}
    </>
  );
}

function SummaryBySellerView({
  rows,
  month,
}: {
  rows: CommissionMonthSummaryRow[];
  month: string;
}) {
  if (rows.length === 0) {
    return <p className="p-6 text-center text-sm text-muted">Nenhuma comissão neste mês.</p>;
  }
  return (
    <div>
      {rows.map((row) => (
        <SellerSummaryRow key={row.seller_id} row={row} month={month} />
      ))}
    </div>
  );
}

function DetailView({ entries }: { entries: CommissionEntry[] }) {
  const [eventFilter, setEventFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<CommissionStatus | "todos">("todos");

  const filtered = useMemo(() => {
    const needle = eventFilter.trim().toLowerCase();
    return entries.filter((e) => {
      if (needle && !e.event_title.toLowerCase().includes(needle)) return false;
      if (statusFilter !== "todos" && e.status !== statusFilter) return false;
      return true;
    });
  }, [entries, eventFilter, statusFilter]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
        <Input
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
          placeholder="Buscar por evento…"
          className="h-9 w-56"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as CommissionStatus | "todos")}
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
        >
          <option value="todos">Todos os status</option>
          <option value="a_pagar">A pagar</option>
          <option value="pago">Pago</option>
        </select>
      </div>
      {filtered.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted">Nenhuma comissão encontrada.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                <th className="px-3 py-2">Data da venda</th>
                <th className="px-3 py-2">Vendedor</th>
                <th className="px-3 py-2">Evento</th>
                <th className="px-3 py-2 text-right">Valor</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Pago em</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.id} className="border-b border-line last:border-0">
                  <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(e.sale_date)}</td>
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
      )}
    </div>
  );
}

export function ComissoesPage() {
  const [month, setMonth] = useState(currentMonth());
  const [sellerFilter, setSellerFilter] = useState<number | null>(null);
  const query = useComissoes(month, sellerFilter);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader title={query.data?.title ?? "Comissões"} className="mb-0" />

      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="h-9 w-40"
        />
        {query.data?.can_manage && (
          <>
            <select
              value={sellerFilter ?? ""}
              onChange={(e) => setSellerFilter(e.target.value ? Number(e.target.value) : null)}
              className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            >
              <option value="">Todos os vendedores</option>
              {query.data.sellers?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportComissoesCsv(query.data!.by_seller, month)}
            >
              Exportar Relatório (CSV)
            </Button>
          </>
        )}
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted">Total de comissões do mês</p>
                <p className="mt-1 text-xl font-semibold text-ink">{brl(query.data.kpis.total_month)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted">Total pago</p>
                <p className="mt-1 text-xl font-semibold text-green">{brl(query.data.kpis.total_paid)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase text-muted">A pagar / pendente</p>
                <p className="mt-1 text-xl font-semibold text-gold">{brl(query.data.kpis.total_pending)}</p>
              </CardContent>
            </Card>
          </div>

          {query.data.can_manage ? (
            <Card>
              <CardHeader>
                <CardTitle>Comissões de {monthLabel(query.data.month)}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Tabs defaultValue="resumo" className="p-3">
                  <TabsList>
                    <TabsTrigger value="resumo">Resumo por Vendedor</TabsTrigger>
                    <TabsTrigger value="detalhamento">Detalhamento de Vendas</TabsTrigger>
                  </TabsList>
                  <TabsContent value="resumo">
                    <SummaryBySellerView rows={query.data.by_seller} month={query.data.month} />
                  </TabsContent>
                  <TabsContent value="detalhamento">
                    <DetailView entries={query.data.entries} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Comissões de {monthLabel(query.data.month)}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {query.data.entries.length === 0 ? (
                  <p className="p-6 text-center text-sm text-muted">Nenhuma comissão neste mês.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                          <th className="px-3 py-2">Evento</th>
                          <th className="px-3 py-2">Data da venda</th>
                          <th className="px-3 py-2 text-right">Valor</th>
                          <th className="px-3 py-2">Status</th>
                          <th className="px-3 py-2">Pago em</th>
                        </tr>
                      </thead>
                      <tbody>
                        {query.data.entries.map((e) => (
                          <tr key={e.id} className="border-b border-line last:border-0">
                            <td className="px-3 py-2 text-ink">
                              {e.event_id ? (
                                <Link to={`/events/${e.event_id}`} className="text-blue hover:underline">
                                  {e.event_title}
                                </Link>
                              ) : (
                                e.event_title
                              )}
                            </td>
                            <td className="whitespace-nowrap px-3 py-2 text-muted">
                              {formatDate(e.sale_date)}
                            </td>
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
                            <td className="whitespace-nowrap px-3 py-2 text-muted">
                              {formatDate(e.paid_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
