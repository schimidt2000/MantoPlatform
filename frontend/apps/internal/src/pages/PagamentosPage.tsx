import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Input, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  usePagamentos,
  useSetPaymentStatus,
  useBulkPaymentAction,
  useAddSalaryAdvance,
  useDeleteSalaryAdvance,
  useExportPagamentosCsv,
  type PagamentoItem,
  type PagamentoItemType,
  type PaymentStatus,
  type BulkPaymentAction,
} from "../lib/financeiro";

const TYPE_LABELS: Record<PagamentoItemType, string> = {
  cache: "Cachê",
  salary: "Salário",
  expense: "Gasto",
  bv: "BV",
  commission: "Comissão",
  recurring: "Recorrente",
};

/** Tipos elegíveis para seleção/ação em massa (mesmo escopo de `bulk_payment_action`). */
const SELECTABLE_TYPES: PagamentoItemType[] = ["cache", "salary", "expense", "commission"];

const STATUS_OPTIONS_BY_TYPE: Record<PagamentoItemType, PaymentStatus[]> = {
  cache: ["nao_pago", "pago", "no_banco"],
  salary: ["nao_pago", "pago", "no_banco"],
  expense: ["nao_pago", "pago", "no_banco"],
  bv: ["nao_pago", "pago", "no_banco"],
  commission: ["nao_pago", "pago"],
  recurring: ["nao_pago", "pago"],
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

function itemKey(item: PagamentoItem): string {
  return `${item.type}-${item.id}`;
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

interface AdvanceFormProps {
  salaryPaymentId: number;
  onDone: () => void;
}

function AdvanceForm({ salaryPaymentId, onDone }: AdvanceFormProps) {
  const [amount, setAmount] = useState("");
  const [advanceDate, setAdvanceDate] = useState("");
  const [proof, setProof] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const addAdvance = useAddSalaryAdvance(currentMonth());

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!proof) {
      setError("Anexe o comprovante do adiantamento.");
      return;
    }
    addAdvance.mutate(
      { salaryPaymentId, amount, advanceDate: advanceDate || undefined, proof },
      {
        onSuccess: () => {
          setAmount("");
          setAdvanceDate("");
          setProof(null);
          onDone();
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : "Não foi possível registrar o adiantamento.");
        },
      },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex flex-wrap items-end gap-2 text-xs">
      <div>
        <label className="block text-muted">Valor</label>
        <Input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="R$ 0,00"
          className="h-8 w-28"
          disabled={addAdvance.isPending}
        />
      </div>
      <div>
        <label className="block text-muted">Data</label>
        <Input
          type="date"
          value={advanceDate}
          onChange={(e) => setAdvanceDate(e.target.value)}
          className="h-8 w-36"
          disabled={addAdvance.isPending}
        />
      </div>
      <div>
        <label className="block text-muted">Comprovante</label>
        <input
          type="file"
          onChange={(e) => setProof(e.target.files?.[0] ?? null)}
          className="text-xs"
          disabled={addAdvance.isPending}
        />
      </div>
      <button
        type="submit"
        disabled={addAdvance.isPending}
        className="h-8 rounded-md bg-blue px-3 text-xs font-medium text-white disabled:opacity-50"
      >
        {addAdvance.isPending ? "Salvando…" : "Adicionar"}
      </button>
      {error && <p className="w-full text-red">{error}</p>}
    </form>
  );
}

interface PagamentoRowProps {
  item: PagamentoItem;
  statusLabels: Record<string, string>;
  month: string;
  selected: boolean;
  selectable: boolean;
  onToggleSelect: (item: PagamentoItem) => void;
}

function PagamentoRow({ item, statusLabels, month, selected, selectable, onToggleSelect }: PagamentoRowProps) {
  const isNegativeLike = item.status === "nao_pago" && item.is_future;
  const setStatus = useSetPaymentStatus(month);
  const deleteAdvance = useDeleteSalaryAdvance(month);
  const [showAdvanceForm, setShowAdvanceForm] = useState(false);
  const statusOptions = STATUS_OPTIONS_BY_TYPE[item.type];

  return (
    <tr className="border-b border-line align-top last:border-0">
      <td className="px-3 py-2">
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(item)}
            aria-label="Selecionar item"
          />
        )}
      </td>
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
        {item.type === "salary" && (
          <details className="mt-1 text-left" open={showAdvanceForm}>
            <summary
              className="cursor-pointer text-xs text-blue"
              onClick={(e) => {
                e.preventDefault();
                setShowAdvanceForm((v) => !v);
              }}
            >
              Adiantamentos ({brl(item.advance_amount)})
            </summary>
            <ul className="mt-1 space-y-0.5 text-xs text-muted">
              <li>Bruto: {brl(item.gross_amount)}</li>
              {(item.advances ?? []).map((a) => (
                <li key={a.id} className="flex items-center gap-1">
                  {formatDate(a.date)} — {brl(a.amount)}
                  {a.proof ? " (com comprovante)" : ""}
                  <button
                    type="button"
                    onClick={() => deleteAdvance.mutate(a.id)}
                    disabled={deleteAdvance.isPending}
                    className="text-red hover:underline disabled:opacity-50"
                  >
                    remover
                  </button>
                </li>
              ))}
            </ul>
            {typeof item.id === "number" && (
              <AdvanceForm salaryPaymentId={item.id} onDone={() => setShowAdvanceForm(true)} />
            )}
          </details>
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        <div className="flex flex-wrap items-center gap-1">
          <select
            value={item.status}
            onChange={(e) =>
              setStatus.mutate({
                item_type: item.type,
                item_id: item.id,
                status: e.target.value as PaymentStatus,
              })
            }
            disabled={setStatus.isPending}
            className="rounded-md border border-line bg-surface-2 px-1.5 py-0.5 text-xs text-muted disabled:opacity-50"
          >
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {statusLabels[s] ?? s}
              </option>
            ))}
          </select>
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
  const [selected, setSelected] = useState<Record<string, PagamentoItem>>({});
  const query = usePagamentos(month);
  const bulkAction = useBulkPaymentAction(month);
  const exportCsv = useExportPagamentosCsv();

  const isSelectable = (item: PagamentoItem) => SELECTABLE_TYPES.includes(item.type);

  const toggleSelect = (item: PagamentoItem) => {
    setSelected((prev) => {
      const key = itemKey(item);
      const next = { ...prev };
      if (next[key]) {
        delete next[key];
      } else {
        next[key] = item;
      }
      return next;
    });
  };

  const selectedItems = Object.values(selected);

  const runBulkAction = (action: BulkPaymentAction) => {
    bulkAction.mutate(
      {
        action,
        role_ids: selectedItems.filter((i) => i.type === "cache").map((i) => Number(i.id)),
        salary_ids: selectedItems.filter((i) => i.type === "salary").map((i) => Number(i.id)),
        expense_ids: selectedItems.filter((i) => i.type === "expense").map((i) => Number(i.id)),
        commission_ids: selectedItems
          .filter((i) => i.type === "commission")
          .map((i) => String(i.id)),
        month,
      },
      { onSuccess: () => setSelected({}) },
    );
  };

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
        <button
          type="button"
          onClick={() => exportCsv.mutate(month)}
          disabled={exportCsv.isPending}
          className="h-9 rounded-md border border-line px-3 text-sm text-ink disabled:opacity-50"
        >
          {exportCsv.isPending ? "Exportando…" : "Exportar CSV"}
        </button>
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

          {selectedItems.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-sm">
              <span className="text-ink">{selectedItems.length} selecionado(s)</span>
              <button
                type="button"
                onClick={() => runBulkAction("pago")}
                disabled={bulkAction.isPending}
                className="rounded-md bg-blue px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
              >
                Marcar como pago
              </button>
              <button
                type="button"
                onClick={() => runBulkAction("nao_pago")}
                disabled={bulkAction.isPending}
                className="rounded-md border border-line px-2 py-1 text-xs text-ink disabled:opacity-50"
              >
                Marcar como não pago
              </button>
              <button
                type="button"
                onClick={() => runBulkAction("delete")}
                disabled={bulkAction.isPending}
                className="rounded-md border border-red px-2 py-1 text-xs text-red disabled:opacity-50"
              >
                Excluir
              </button>
              {bulkAction.data?.skipped.map((msg) => (
                <span key={msg} className="w-full text-xs text-muted">
                  Ignorado: {msg}.
                </span>
              ))}
            </div>
          )}

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
                  <table className="w-full min-w-[820px] border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                        <th className="px-3 py-2" />
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
                          key={itemKey(item)}
                          item={item}
                          statusLabels={query.data!.status_labels}
                          month={month}
                          selected={Boolean(selected[itemKey(item)])}
                          selectable={isSelectable(item)}
                          onToggleSelect={toggleSelect}
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
