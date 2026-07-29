import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CopyButton,
  Input,
  PageHeader,
  Skeleton,
  cn,
} from "@manto/ui";
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
 * `app/api/financeiro_write.py`). Todos os tipos aceitam as mesmas 3 situações (feature 199).
 */
const STATUS_OPTIONS_BY_TYPE: Record<PagamentoItemType, PaymentStatus[]> = {
  cache: ["nao_pago", "no_banco", "pago"],
  salary: ["nao_pago", "no_banco", "pago"],
  expense: ["nao_pago", "no_banco", "pago"],
  bv: ["nao_pago", "no_banco", "pago"],
  commission: ["nao_pago", "no_banco", "pago"],
  recurring: ["nao_pago", "no_banco", "pago"],
};

/**
 * As 4 faixas que o financeiro enxerga na planilha. É a MESMA classificação que o backend usa
 * para somar `totals` (`_pagamentos` em `app/api/financeiro_read.py`): "pendente" é o que já
 * venceu (`nao_pago` sem `is_future`) e "futuro" é o que ainda vai vencer. Derivar as duas do
 * `is_future` que a API já manda — em vez de recomparar datas no cliente — garante que o filtro
 * do card sempre bata com o valor exibido nele.
 */
type PagamentoBucket = "pago" | "no_banco" | "pendente" | "futuro";

/** Filtro ativo dos cards de KPI; `null` = "Total no período" (nenhum filtro). */
type PagamentoFilter = PagamentoBucket | null;

interface BucketTone {
  /** Nuance de fundo da linha da tabela — leitura "bate o olho e entende". */
  row: string;
  /** Card selecionado: borda grossa viva + fundo colorido. */
  cardActive: string;
  /** Cor do valor no card e do seletor de situação. */
  text: string;
  /** Seletor de situação da linha. */
  select: string;
}

/**
 * Paleta única por faixa — card, linha da tabela e seletor de situação saem daqui, então a cor
 * que o operador clica no card é exatamente a cor das linhas que aparecem.
 *
 * "Futuro" usa `gold` (cor de atenção do design system) e não `amber`: a paleta padrão do
 * Tailwind não combina com o dourado da marca — ver `@manto/ui/tailwind-preset`.
 */
const BUCKET_TONE: Record<PagamentoBucket, BucketTone> = {
  pago: {
    row: "bg-green-50",
    cardActive: "border-green-500 bg-green-50/50 ring-2 ring-green-500/20",
    text: "text-green",
    select: "border-green bg-green-soft text-green",
  },
  no_banco: {
    row: "bg-blue-50",
    cardActive: "border-blue-500 bg-blue-50/50 ring-2 ring-blue-500/20",
    text: "text-blue",
    select: "border-blue bg-blue-soft text-blue",
  },
  pendente: {
    row: "bg-rose-50",
    cardActive: "border-red-500 bg-rose-50/50 ring-2 ring-red-500/20",
    text: "text-red",
    select: "border-red bg-red-soft text-red",
  },
  futuro: {
    row: "bg-gold-50",
    cardActive: "border-gold-500 bg-gold-50/50 ring-2 ring-gold-500/20",
    text: "text-gold",
    select: "border-gold bg-gold-soft text-gold",
  },
};

const BUCKET_LABELS: Record<PagamentoBucket, string> = {
  pago: "Pagos",
  no_banco: "No banco",
  pendente: "Pendentes",
  futuro: "Futuro",
};

/** Ordem dos cards de filtro, depois do card neutro "Total no período". */
const BUCKET_ORDER: PagamentoBucket[] = ["pago", "no_banco", "pendente", "futuro"];

/** Rótulo do botão de cada ação em lote — a barra flutuante lê daqui. */
const BULK_ACTION_LABELS: Record<Exclude<BulkPaymentAction, "delete">, string> = {
  pago: "Marcar pago",
  no_banco: "No banco",
  nao_pago: "Não pago",
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

/** Faixa a que o item pertence — fonte única do filtro, da cor da linha e do seletor. */
function bucketOf(item: PagamentoItem): PagamentoBucket {
  if (item.status === "pago") return "pago";
  if (item.status === "no_banco") return "no_banco";
  return item.is_future ? "futuro" : "pendente";
}

/** Valor cru em formato "1234,56" — o que o operador cola no internet banking. */
function rawAmount(value: number): string {
  return value.toFixed(2).replace(".", ",");
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
  const bucket = bucketOf(item);
  const tone = BUCKET_TONE[bucket];
  const setStatus = useSetPaymentStatus(month);
  const deleteAdvance = useDeleteSalaryAdvance(month);
  const [showAdvanceForm, setShowAdvanceForm] = useState(false);
  const statusOptions = STATUS_OPTIONS_BY_TYPE[item.type];
  const descricao = item.event_title || item.copy_label || "—";

  return (
    <tr className={cn("border-b border-line align-top transition-colors last:border-0", tone.row)}>
      {/* Seleção em lote — barra lateral roxa marca a linha marcada. A borda existe sempre
          (transparente quando não selecionada) para a linha não "pular" 4px ao marcar. */}
      <td
        className={cn(
          "border-l-4 border-l-transparent px-2 py-2",
          selected && "border-l-accent bg-accent-soft",
        )}
      >
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
            <Link to={`/events/${item.event_id}`} className="font-bold text-ink hover:underline">
              {descricao}
            </Link>
          ) : (
            <span className="font-bold text-ink">{descricao}</span>
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
        <div className="flex items-center justify-end gap-1 font-bold tabular-nums text-ink">
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
          {bucket === "futuro" && (
            <span className="rounded-md bg-gold-soft px-1.5 py-0.5 text-[10px] font-bold text-gold">
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
            className={cn(
              "rounded-md border px-1.5 py-1 text-[11px] font-bold disabled:opacity-50",
              tone.select,
            )}
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

interface TotalCardProps {
  label: string;
  value: number;
  /** Nº de itens da faixa — mostra ao operador o tamanho do filtro antes do clique. */
  count: number;
  /** Faixa filtrada ao clicar; `null` = card "Total no período" (limpa o filtro). */
  bucket: PagamentoBucket | null;
  active: boolean;
  /** Há um filtro ativo em OUTRO card — este fica apagado para não competir. */
  dimmed: boolean;
  onClick: () => void;
}

/**
 * Card de KPI que também é o seletor de filtro da tabela (feature de usabilidade 2026-07-28).
 * Clicar filtra; clicar de novo no card ativo limpa. Cores e destaque vêm de `BUCKET_TONE`,
 * então o card e as linhas que ele revela têm sempre a mesma cor.
 */
function TotalCard({ label, value, count, bucket, active, dimmed, onClick }: TotalCardProps) {
  const tone = bucket ? BUCKET_TONE[bucket] : null;
  return (
    // As classes vão TODAS no `Card` (que passa por `cn`/twMerge e resolve `border` vs
    // `border-2`, `bg-panel` vs `bg-green-50/50`); o `Slot` do `asChild` só concatena o
    // className do filho, sem desempatar conflito de utilitário.
    <Card
      asChild
      className={cn(
        "border-2 p-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? tone
            ? `${tone.cardActive} shadow-md`
            : "border-accent bg-accent-soft shadow-md"
          : "border-line bg-panel hover:border-accent/40 hover:shadow-md",
        dimmed && "opacity-60 grayscale-[35%] hover:opacity-100 hover:grayscale-0",
      )}
    >
      {/* `span`, não `p`: o conteúdo de um `<button>` só aceita phrasing content. */}
      <button type="button" onClick={onClick} aria-pressed={active}>
        <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
          {label}
        </span>
        <span className={cn("mt-1 block text-lg font-bold tabular-nums", tone?.text ?? "text-ink")}>
          {brl(value)}
        </span>
        <span className="mt-0.5 block text-[10px] font-semibold text-muted">
          {count} {count === 1 ? "item" : "itens"}
          {active ? " · filtro ativo" : ""}
        </span>
      </button>
    </Card>
  );
}

interface PagamentoBulkBarProps {
  count: number;
  /** Soma dos itens marcados, formatada com `@manto/money` na exibição. */
  total: number;
  /** Ação em execução agora — só o botão dela mostra spinner (Princípio V). */
  runningAction: BulkPaymentAction | null;
  onAction: (action: BulkPaymentAction) => void;
  onClear: () => void;
}

/**
 * Barra flutuante de ações em massa da planilha — aparece no topo da tabela assim que há 1+
 * itens marcados e some ao voltar a 0. Segue o padrão de `CatalogBulkActionBar` (feature 186),
 * com a diferença de mostrar a soma monetária da seleção, que é o número que o financeiro
 * confere antes de disparar o lote no banco.
 */
function PagamentoBulkBar({
  count,
  total,
  runningAction,
  onAction,
  onClear,
}: PagamentoBulkBarProps) {
  const shouldReduceMotion = useReducedMotion();
  const busy = runningAction !== null;

  return (
    <AnimatePresence>
      {count > 0 && (
        <motion.div
          initial={shouldReduceMotion ? false : { opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={shouldReduceMotion ? undefined : { opacity: 0, y: -8 }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.2, ease: "easeOut" }}
          className="flex flex-wrap items-center gap-2 border-b-2 border-accent bg-accent-soft px-3 py-2.5"
        >
          <span className="mr-1 text-sm font-bold tabular-nums text-ink">
            {count} selecionado{count === 1 ? "" : "s"} • {brl(total)}
          </span>
          {(Object.keys(BULK_ACTION_LABELS) as Array<keyof typeof BULK_ACTION_LABELS>).map(
            (action) => (
              <Button
                key={action}
                size="sm"
                variant={action === "pago" ? "default" : "outline"}
                loading={runningAction === action}
                disabled={busy && runningAction !== action}
                onClick={() => onAction(action)}
              >
                {BULK_ACTION_LABELS[action]}
              </Button>
            ),
          )}
          <Button
            size="sm"
            variant="ghost"
            className="text-red"
            loading={runningAction === "delete"}
            disabled={busy && runningAction !== "delete"}
            onClick={() => {
              if (window.confirm(`Excluir ${count} item(ns) selecionado(s)?`)) {
                onAction("delete");
              }
            }}
          >
            Excluir
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} onClick={onClear}>
            Limpar seleção
          </Button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function PagamentosPage() {
  const [month, setMonth] = useState(currentMonth());
  const [selected, setSelected] = useState<Record<string, PagamentoItem>>({});
  const [filter, setFilter] = useState<PagamentoFilter>(null);
  const query = usePagamentos(month);
  const bulkAction = useBulkPaymentAction(month);
  const exportCsv = useExportPagamentosCsv();

  const data = query.data;
  const items = useMemo(() => data?.items ?? [], [data]);
  const isSelectable = (item: PagamentoItem) => SELECTABLE_TYPES.includes(item.type);

  /** Quantos itens há em cada faixa — alimenta o subtítulo dos cards de filtro. */
  const counts = useMemo(() => {
    const acc: Record<PagamentoBucket, number> = { pago: 0, no_banco: 0, pendente: 0, futuro: 0 };
    items.forEach((item) => {
      acc[bucketOf(item)] += 1;
    });
    return acc;
  }, [items]);

  const visibleItems = useMemo(
    () => (filter ? items.filter((item) => bucketOf(item) === filter) : items),
    [items, filter],
  );
  const visibleSelectable = visibleItems.filter(isSelectable);

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
  /** Soma monetária da seleção — exibida na barra em lote via `@manto/money` (Princípio VII). */
  const selectedTotal = selectedItems.reduce((sum, item) => sum + item.amount, 0);

  // "Selecionar tudo" opera sobre o que está VISÍVEL: com um filtro ligado, marcar tudo marca
  // só aquela faixa, sem tocar no que já estava selecionado fora dela.
  const allVisibleSelected =
    visibleSelectable.length > 0 && visibleSelectable.every((i) => Boolean(selected[itemKey(i)]));

  const toggleSelectAll = () => {
    setSelected((prev) => {
      const next = { ...prev };
      visibleSelectable.forEach((item) => {
        if (allVisibleSelected) {
          delete next[itemKey(item)];
        } else {
          next[itemKey(item)] = item;
        }
      });
      return next;
    });
  };

  /** Clique no card: alterna a faixa; o card neutro (ou reclicar o ativo) limpa o filtro. */
  const handleFilterClick = (bucket: PagamentoFilter) => {
    setFilter((prev) => (bucket === null || prev === bucket ? null : bucket));
  };

  const handleMonthChange = (nextMonth: string) => {
    setMonth(nextMonth);
    setSelected({});
    setFilter(null);
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

  // `variables` da mutation em voo diz QUAL ação está rodando — assim só o botão clicado gira,
  // em vez de os quatro spinnerem juntos (Princípio V). Fora do `isPending` ele guarda o último
  // envio, por isso a guarda.
  const runningAction: BulkPaymentAction | null = bulkAction.isPending
    ? bulkAction.variables?.action ?? null
    : null;

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
          onChange={(e) => handleMonthChange(e.target.value)}
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
            <TotalCard
              label="Total no período"
              value={data.totals.total}
              count={items.length}
              bucket={null}
              active={filter === null}
              dimmed={false}
              onClick={() => handleFilterClick(null)}
            />
            {BUCKET_ORDER.map((bucket) => (
              <TotalCard
                key={bucket}
                label={BUCKET_LABELS[bucket]}
                value={data.totals[bucket]}
                count={counts[bucket]}
                bucket={bucket}
                active={filter === bucket}
                dimmed={filter !== null && filter !== bucket}
                onClick={() => handleFilterClick(bucket)}
              />
            ))}
          </div>

          <p aria-live="polite" className="sr-only">
            {filter
              ? `Filtro ${BUCKET_LABELS[filter]} ativo: ${visibleItems.length} de ${items.length} itens.`
              : "Nenhum filtro ativo."}
          </p>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
              <CardTitle className="text-base">
                Itens do mês ({visibleItems.length}
                {filter ? ` de ${items.length}` : ""})
              </CardTitle>
              {filter && (
                <Button variant="ghost" size="sm" onClick={() => setFilter(null)}>
                  Limpar filtro · {BUCKET_LABELS[filter]} ✕
                </Button>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <PagamentoBulkBar
                count={selectedItems.length}
                total={selectedTotal}
                runningAction={runningAction}
                onAction={runBulkAction}
                onClear={() => setSelected({})}
              />

              {(bulkAction.isSuccess || bulkAction.isError || bulkAction.isPending) && (
                <div className="border-b border-line px-3 py-2">
                  <span aria-live="polite" className="text-xs text-muted">
                    {bulkAction.isPending
                      ? "Aplicando ação em lote…"
                      : bulkAction.isSuccess
                        ? `${bulkAction.data?.changed ?? 0} item(ns) atualizado(s).`
                        : ""}
                  </span>
                  {bulkAction.data?.skipped.map((msg) => (
                    <span key={msg} className="block text-xs text-muted">
                      Ignorado: {msg}.
                    </span>
                  ))}
                  {bulkAction.isError && (
                    <span className="block text-xs text-red">
                      Não foi possível aplicar a ação em lote.
                    </span>
                  )}
                </div>
              )}

              {visibleItems.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted">
                  {items.length === 0 ? (
                    <p>Nenhum item de pagamento neste mês.</p>
                  ) : (
                    <>
                      <p>Nenhum item na faixa “{filter ? BUCKET_LABELS[filter] : ""}”.</p>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={() => setFilter(null)}
                      >
                        Ver todos os {items.length} itens
                      </Button>
                    </>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1040px] border-collapse text-[13px]">
                    <thead>
                      <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
                        <th className="w-8 px-2 py-2">
                          <input
                            type="checkbox"
                            checked={allVisibleSelected}
                            onChange={toggleSelectAll}
                            aria-label="Selecionar tudo"
                            disabled={visibleSelectable.length === 0}
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
                      {visibleItems.map((item) => (
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
