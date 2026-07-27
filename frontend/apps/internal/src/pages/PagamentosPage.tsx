import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, PageHeader, Skeleton } from "@manto/ui";
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

const TYPE_BADGE_CLASS: Record<PagamentoItemType, string> = {
  cache: "bg-surface-2 text-muted",
  salary: "bg-gold-soft text-gold",
  expense: "bg-blue-soft text-blue",
  bv: "bg-accent-soft text-accent",
  commission: "bg-green-soft text-green",
  recurring: "bg-gold-soft text-gold",
};

/** Tipos elegíveis para seleção/ação em massa (mesmo escopo de `bulk_payment_action`). */
const SELECTABLE_TYPES: PagamentoItemType[] = ["cache", "salary", "expense", "commission"];

/**
 * Situações aceitas pelo backend por tipo de item (`_VALID_PAYMENT_STATUS` em
 * `app/api/financeiro_write.py`). Comissão e conta recorrente não têm estado "no banco" — o
 * seletor não oferece a opção nesses casos, em vez de deixar o backend rejeitar.
 */
const STATUS_OPTIONS_BY_TYPE: Record<PagamentoItemType, PaymentStatus[]> = {
  cache: ["nao_pago", "no_banco", "pago"],
  salary: ["nao_pago", "no_banco", "pago"],
  expense: ["nao_pago", "no_banco", "pago"],
  bv: ["nao_pago", "no_banco", "pago"],
  commission: ["nao_pago", "pago"],
  recurring: ["nao_pago", "pago"],
};

/** Cor da linha por situação — mesma leitura rápida da planilha Jinja legada. */
const ROW_CLASS: Record<PaymentStatus, string> = {
  pago: "bg-green-soft/40",
  no_banco: "bg-blue-soft/40",
  nao_pago: "",
};

const STATUS_SELECT_CLASS: Record<PaymentStatus, string> = {
  pago: "border-green bg-green-soft text-green",
  no_banco: "border-blue bg-blue-soft text-blue",
  nao_pago: "border-line bg-panel text-ink",
};

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
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

/** Valor cru em formato "1234,56" — o que o operador cola no internet banking. */
function rawAmount(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

interface CopyButtonProps {
  value: string;
  label: string;
}

/**
 * Botão compacto de cópia rápida (Princípio V — nunca fica "morto" ao clique): troca para
 * "✓ Copiado" por ~1,8 s e anuncia o resultado por `aria-live` para leitores de tela.
 */
function CopyButton({ value, label }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Clipboard bloqueado (contexto não seguro): o texto continua visível para seleção manual.
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <>
      <button
        type="button"
        onClick={copy}
        title={label}
        aria-label={label}
        className="shrink-0 rounded-md border border-line px-1 py-0.5 text-[10px] leading-none text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      >
        {copied ? "✓" : "⧉"}
      </button>
      <span aria-live="polite" className="sr-only">
        {copied ? `${label}: copiado` : ""}
      </span>
    </>
  );
}

interface AdvanceFormProps {
  salaryPaymentId: number;
  month: string;
  onDone: () => void;
}

function AdvanceForm({ salaryPaymentId, month, onDone }: AdvanceFormProps) {
  const [amount, setAmount] = useState("");
  const [advanceDate, setAdvanceDate] = useState("");
  const [proof, setProof] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const addAdvance = useAddSalaryAdvance(month);

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
      <Button type="submit" size="sm" loading={addAdvance.isPending}>
        Adicionar
      </Button>
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

function PagamentoRow({
  item,
  statusLabels,
  month,
  selected,
  selectable,
  onToggleSelect,
}: PagamentoRowProps) {
  const isFuturoPendente = item.status === "nao_pago" && item.is_future;
  const setStatus = useSetPaymentStatus(month);
  const deleteAdvance = useDeleteSalaryAdvance(month);
  const [showAdvanceForm, setShowAdvanceForm] = useState(false);
  const statusOptions = STATUS_OPTIONS_BY_TYPE[item.type];
  const descricao = item.event_title || item.copy_label || "—";

  return (
    <tr className={`border-b border-line align-top last:border-0 ${ROW_CLASS[item.status]}`}>
      {/* Seleção em lote */}
      <td className="px-2 py-2">
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(item)}
            aria-label={`Selecionar ${descricao}`}
          />
        )}
      </td>

      {/* Vencimento */}
      <td className="whitespace-nowrap px-3 py-2 text-xs text-muted">{formatDate(item.date)}</td>

      {/* Descrição detalhada: tipo + item */}
      <td className="px-3 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${TYPE_BADGE_CLASS[item.type]}`}
          >
            {TYPE_LABELS[item.type]}
          </span>
          {item.type === "bv" && item.missing_data && (
            <span
              className="rounded-md bg-red-soft px-1.5 py-0.5 text-[10px] font-bold text-red"
              title="Falta o PIX de quem recebe o BV"
            >
              ⚠ falta PIX
            </span>
          )}
          {item.event_id ? (
            <Link to={`/events/${item.event_id}`} className="font-semibold text-ink hover:underline">
              {descricao}
            </Link>
          ) : (
            <span className="font-semibold text-ink">{descricao}</span>
          )}
          {item.copy_label && (
            <CopyButton value={item.copy_label} label="Copiar descrição e data" />
          )}
        </div>
        {item.sublabel && <div className="mt-0.5 text-[11px] text-muted">{item.sublabel}</div>}
      </td>

      {/* Favorecido */}
      <td className="px-3 py-2 font-bold text-ink">{item.person_name || "—"}</td>

      {/* Valor */}
      <td className="whitespace-nowrap px-3 py-2 text-right">
        <div className="flex items-center justify-end gap-1 font-semibold tabular-nums text-ink">
          <span>{brl(item.amount)}</span>
          <CopyButton value={rawAmount(item.amount)} label="Copiar valor" />
        </div>
        {item.type === "salary" && (item.advance_amount ?? 0) > 0 && (
          <div className="text-[10px] font-semibold text-gold">
            adiantado {brl(item.advance_amount)}
            {(item.advances?.length ?? 0) > 1 ? ` (${item.advances?.length}x)` : ""}
          </div>
        )}
        {item.type === "salary" && (
          <details className="mt-1 text-left" open={showAdvanceForm}>
            <summary
              className="cursor-pointer text-[11px] text-blue"
              onClick={(e) => {
                e.preventDefault();
                setShowAdvanceForm((v) => !v);
              }}
            >
              ✎ Adiantamentos
            </summary>
            <ul className="mt-1 space-y-0.5 text-[11px] text-muted">
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
              <AdvanceForm
                salaryPaymentId={item.id}
                month={month}
                onDone={() => setShowAdvanceForm(true)}
              />
            )}
          </details>
        )}
      </td>

      {/* Chave PIX + cópia rápida */}
      <td className="px-3 py-2 text-[11px]">
        {item.pix_key ? (
          <div className="flex items-start gap-1">
            <div className="min-w-0">
              <span className="break-all text-ink">{item.pix_key}</span>
              {item.pix_key_type && (
                <span className="mt-0.5 block text-[10px] font-semibold uppercase text-muted">
                  {item.pix_key_type}
                </span>
              )}
            </div>
            <CopyButton value={item.pix_key} label="Copiar chave PIX" />
          </div>
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>

      {/* Situação */}
      <td className="whitespace-nowrap px-3 py-2">
        <div className="flex flex-col items-start gap-1">
          {isFuturoPendente && (
            <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-muted">
              ⏳ Futuro
            </span>
          )}
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
            aria-label={`Situação de ${descricao}`}
            className={`rounded-md border px-1.5 py-1 text-[11px] font-semibold disabled:opacity-50 ${
              STATUS_SELECT_CLASS[item.status]
            }`}
          >
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {statusLabels[s] ?? s}
              </option>
            ))}
          </select>
          <span aria-live="polite" className="sr-only">
            {setStatus.isPending ? "Salvando situação…" : ""}
          </span>
          {setStatus.isError && (
            <span className="text-[10px] text-red">Falha ao salvar — tente de novo.</span>
          )}
        </div>
      </td>
    </tr>
  );
}

function TotalCard({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <Card className="p-4">
      <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-lg font-bold tabular-nums ${tone ?? "text-ink"}`}>{brl(value)}</p>
    </Card>
  );
}

export function PagamentosPage() {
  const [month, setMonth] = useState(currentMonth());
  const [selected, setSelected] = useState<Record<string, PagamentoItem>>({});
  const query = usePagamentos(month);
  const bulkAction = useBulkPaymentAction(month);
  const exportCsv = useExportPagamentosCsv();

  const data = query.data;
  const items = data?.items ?? [];
  const isSelectable = (item: PagamentoItem) => SELECTABLE_TYPES.includes(item.type);
  const selectableItems = items.filter(isSelectable);

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
  const allSelected =
    selectableItems.length > 0 && selectedItems.length === selectableItems.length;

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelected({});
      return;
    }
    setSelected(Object.fromEntries(selectableItems.map((i) => [itemKey(i), i])));
  };

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
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Planilha de Pagamentos"
        subtitle="Cachês, salários, gastos, BVs, comissões e contas recorrentes do mês"
        className="mb-0"
      />

      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="h-9 w-40"
          aria-label="Mês de referência"
        />
        <Button
          variant="outline"
          size="sm"
          loading={exportCsv.isPending}
          onClick={() => exportCsv.mutate(month)}
        >
          Exportar CSV
        </Button>
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a planilha de pagamentos.
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <TotalCard label="Total do mês" value={data.totals.total} />
            <TotalCard label="Pago" value={data.totals.pago} tone="text-green" />
            <TotalCard label="No banco" value={data.totals.no_banco} tone="text-blue" />
            <TotalCard label="Pendente" value={data.totals.pendente} tone="text-red" />
            <TotalCard label="Futuro" value={data.totals.futuro} tone="text-muted" />
          </div>

          {selectedItems.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-sm">
              <span className="font-semibold text-ink">
                {selectedItems.length} selecionado(s)
              </span>
              <Button
                size="sm"
                loading={bulkAction.isPending}
                onClick={() => runBulkAction("pago")}
              >
                Marcar como pago
              </Button>
              <Button
                size="sm"
                variant="outline"
                loading={bulkAction.isPending}
                onClick={() => runBulkAction("no_banco")}
              >
                Marcar como no banco
              </Button>
              <Button
                size="sm"
                variant="outline"
                loading={bulkAction.isPending}
                onClick={() => runBulkAction("nao_pago")}
              >
                Marcar como não pago
              </Button>
              <Button
                size="sm"
                variant="ghost"
                loading={bulkAction.isPending}
                className="text-red"
                onClick={() => {
                  if (window.confirm(`Excluir ${selectedItems.length} item(ns) selecionado(s)?`)) {
                    runBulkAction("delete");
                  }
                }}
              >
                Excluir
              </Button>
              <span aria-live="polite" className="w-full text-xs text-muted">
                {bulkAction.isPending
                  ? "Aplicando ação em lote…"
                  : bulkAction.isSuccess
                    ? `${bulkAction.data?.changed ?? 0} item(ns) atualizado(s).`
                    : ""}
              </span>
              {bulkAction.data?.skipped.map((msg) => (
                <span key={msg} className="w-full text-xs text-muted">
                  Ignorado: {msg}.
                </span>
              ))}
              {bulkAction.isError && (
                <span className="w-full text-xs text-red">
                  Não foi possível aplicar a ação em lote.
                </span>
              )}
            </div>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Itens do mês ({items.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {items.length === 0 ? (
                <p className="p-6 text-center text-sm text-muted">
                  Nenhum item de pagamento neste mês.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1040px] border-collapse text-[13px]">
                    <thead>
                      <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
                        <th className="w-8 px-2 py-2">
                          <input
                            type="checkbox"
                            checked={allSelected}
                            onChange={toggleSelectAll}
                            aria-label="Selecionar tudo"
                            disabled={selectableItems.length === 0}
                          />
                        </th>
                        <th className="px-3 py-2">Vencimento</th>
                        <th className="px-3 py-2">Descrição</th>
                        <th className="px-3 py-2">Favorecido</th>
                        <th className="px-3 py-2 text-right">Valor</th>
                        <th className="px-3 py-2">Chave PIX</th>
                        <th className="w-36 px-3 py-2">Situação</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <PagamentoRow
                          key={itemKey(item)}
                          item={item}
                          statusLabels={data.status_labels}
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
