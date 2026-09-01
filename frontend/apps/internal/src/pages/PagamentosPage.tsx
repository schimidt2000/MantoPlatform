import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, Trash2, X } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  Input,
  PageHeader,
  Skeleton,
  cn,
} from "@manto/ui";
import {
  usePagamentos,
  useBulkPaymentAction,
  useExportPagamentosCsv,
  type PagamentoItem,
  type BulkPaymentAction,
} from "../lib/financeiro";
import {
  BULK_ACTION_LABELS,
  BULK_ACTION_SHORT_LABELS,
  BUCKET_LABELS,
  BUCKET_ORDER,
  BUCKET_TONE,
  brl,
  bucketOf,
  currentMonth,
  isSelectable,
  itemKey,
  matchesSearch,
  monthLabel,
  searchIndexOf,
  searchTerms,
  shiftMonth,
  type PagamentoBucket,
  type PagamentoFilter,
} from "../lib/pagamentos";
import { PagamentoCard, PagamentoRow } from "../components/Pagamentos/PagamentoItemViews";
import { SalaryAdvancesDialog } from "../components/Pagamentos/SalaryAdvancesDialog";

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
  /** Ajuste de grade (ex.: o card neutro ocupando a linha inteira no celular). */
  className?: string;
  onClick: () => void;
}

/**
 * Card de KPI que também é o seletor de filtro da tabela (feature de usabilidade 2026-07-28).
 * Clicar filtra; clicar de novo no card ativo limpa. Cores e destaque vêm de `BUCKET_TONE`,
 * então o card e as linhas que ele revela têm sempre a mesma cor.
 */
function TotalCard({
  label,
  value,
  count,
  bucket,
  active,
  dimmed,
  className,
  onClick,
}: TotalCardProps) {
  const tone = bucket ? BUCKET_TONE[bucket] : null;
  return (
    // As classes vão TODAS no `Card` (que passa por `cn`/twMerge e resolve `border` vs
    // `border-2`, `bg-panel` vs `bg-green-50/50`); o `Slot` do `asChild` só concatena o
    // className do filho, sem desempatar conflito de utilitário.
    <Card
      asChild
      className={cn(
        "border-2 p-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-4",
        active
          ? tone
            ? `${tone.cardActive} shadow-md`
            : "border-accent bg-accent-soft shadow-md"
          : "border-line bg-panel hover:border-accent/40 hover:shadow-md",
        dimmed && "opacity-60 grayscale-[35%] hover:opacity-100 hover:grayscale-0",
        className,
      )}
    >
      {/* `span`, não `p`: o conteúdo de um `<button>` só aceita phrasing content. */}
      <button type="button" onClick={onClick} aria-pressed={active}>
        <span className="block text-[10px] font-bold uppercase tracking-wide text-muted sm:text-[11px]">
          {label}
        </span>
        <span
          className={cn(
            "mt-1 block text-base font-bold tabular-nums sm:text-lg",
            tone?.text ?? "text-ink",
          )}
        >
          {brl(value)}
        </span>
        <span className="mt-0.5 block text-[10px] font-semibold text-muted">
          {count} {count === 1 ? "item" : "itens"}
          {/* O card neutro fica "ativo" quando NÃO há filtro — anunciar "filtro ativo" nele
              dizia o contrário do que acontece. */}
          {active && bucket ? " · filtro ativo" : ""}
        </span>
      </button>
    </Card>
  );
}

interface PagamentoBulkBarProps {
  count: number;
  /** Soma dos itens marcados, formatada com `@manto/money` na exibição. */
  total: number;
  /** Marcados que a busca/filtro esconderam — a ação em lote os inclui, então precisa avisar. */
  hiddenCount: number;
  /** Ação em execução agora — só o botão dela mostra spinner (Princípio V). */
  runningAction: BulkPaymentAction | null;
  onAction: (action: BulkPaymentAction) => void;
  /** Pede a confirmação da exclusão — quem abre o diálogo é a página, não a barra. */
  onRequestDelete: () => void;
  onClear: () => void;
}

/**
 * Barra de ações em massa da planilha — aparece assim que há 1+ itens marcados e some ao voltar
 * a 0. Segue o padrão de `CatalogBulkActionBar` (feature 186), com a diferença de mostrar a soma
 * monetária da seleção, que é o número que o financeiro confere antes de disparar o lote.
 *
 * No celular ela é **rodapé fixo** (feature 226): ancorada no topo da tabela, a barra saía da
 * tela no primeiro rolar e o operador marcava itens sem ver o que fazer com eles. No desktop
 * continua no lugar de sempre, no topo da lista.
 */
function PagamentoBulkBar({
  count,
  total,
  hiddenCount,
  runningAction,
  onAction,
  onRequestDelete,
  onClear,
}: PagamentoBulkBarProps) {
  const shouldReduceMotion = useReducedMotion();
  const busy = runningAction !== null;

  return (
    <AnimatePresence>
      {count > 0 && (
        <motion.div
          initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={shouldReduceMotion ? undefined : { opacity: 0, y: 8 }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.2, ease: "easeOut" }}
          className={cn(
            "flex flex-wrap items-center gap-2 border-accent px-3 py-2.5",
            // Rodapé fixo no celular. Fundo OPACO (`bg-panel`): `accent-soft` é translúcido de
            // propósito e deixaria os cartões passarem por baixo da barra.
            "fixed inset-x-0 bottom-0 z-30 border-t-2 bg-panel shadow-lg",
            "pb-[calc(0.625rem+env(safe-area-inset-bottom))]",
            "xl:static xl:z-auto xl:border-b-2 xl:border-t-0 xl:bg-accent-soft xl:pb-2.5 xl:shadow-none",
          )}
        >
          {/* No celular o resumo ocupa a linha inteira e os botões vêm embaixo, em UMA linha
              (rótulo curto + ícone) — é o que mantém a barra em ~80px em vez de 146px. */}
          <div className="flex w-full flex-wrap items-baseline gap-x-2 xl:mr-1 xl:w-auto">
            <span className="text-sm font-bold tabular-nums text-ink">
              {count} selecionado{count === 1 ? "" : "s"} • {brl(total)}
            </span>
            {hiddenCount > 0 && (
              <span className="text-[11px] font-semibold text-muted">
                ({hiddenCount} fora do filtro/busca)
              </span>
            )}
          </div>
          {(Object.keys(BULK_ACTION_LABELS) as Array<keyof typeof BULK_ACTION_LABELS>).map(
            (action) => (
              <Button
                key={action}
                size="sm"
                className="h-11 xl:h-9"
                variant={action === "pago" ? "default" : "outline"}
                loading={runningAction === action}
                disabled={busy && runningAction !== action}
                onClick={() => onAction(action)}
              >
                <span className="xl:hidden">{BULK_ACTION_SHORT_LABELS[action]}</span>
                <span className="hidden xl:inline">{BULK_ACTION_LABELS[action]}</span>
              </Button>
            ),
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-11 w-11 px-0 text-red xl:h-9 xl:w-auto xl:px-3"
            aria-label="Excluir selecionados"
            loading={runningAction === "delete"}
            disabled={busy && runningAction !== "delete"}
            onClick={onRequestDelete}
          >
            <Trash2 className="h-4 w-4 xl:hidden" aria-hidden />
            <span className="hidden xl:inline">Excluir</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-11 w-11 px-0 xl:h-9 xl:w-auto xl:px-3"
            aria-label="Limpar seleção"
            disabled={busy}
            onClick={onClear}
          >
            <X className="h-4 w-4 xl:hidden" aria-hidden />
            <span className="hidden xl:inline">Limpar seleção</span>
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
  const [search, setSearch] = useState("");
  /**
   * Adiantamentos: guardamos só o **id** do lançamento de salário e derivamos o item da query
   * (nunca uma cópia em estado). O diálogo grava adiantamento e remove adiantamento — com um
   * instantâneo, ele seguiria mostrando o total anterior depois de gravar. O `open` é separado
   * do id para a janela poder animar a saída antes de desmontar.
   */
  const [advanceSalaryId, setAdvanceSalaryId] = useState<number | null>(null);
  const [advanceOpen, setAdvanceOpen] = useState(false);
  /** Confirmação da exclusão em lote — ver `ConfirmDialog` no fim do arquivo. */
  const [confirmDelete, setConfirmDelete] = useState(false);

  const query = usePagamentos(month);
  const bulkAction = useBulkPaymentAction();
  const exportCsv = useExportPagamentosCsv();

  const data = query.data;
  const items = useMemo(() => data?.items ?? [], [data]);
  const statusLabels = data?.status_labels;

  /** Índice de busca por item, montado uma vez por resposta da API (não por tecla digitada). */
  const searchIndex = useMemo(() => {
    const index = new Map<string, string>();
    items.forEach((item) => index.set(itemKey(item), searchIndexOf(item, statusLabels ?? {})));
    return index;
  }, [items, statusLabels]);

  const terms = useMemo(() => searchTerms(search), [search]);

  /** Quantos itens há em cada faixa — alimenta o subtítulo dos cards de filtro. */
  const counts = useMemo(() => {
    const acc: Record<PagamentoBucket, number> = { pago: 0, no_banco: 0, pendente: 0, futuro: 0 };
    items.forEach((item) => {
      acc[bucketOf(item)] += 1;
    });
    return acc;
  }, [items]);

  // Faixa (card de KPI) e busca se somam: o card recorta a situação, a busca recorta o texto.
  const visibleItems = useMemo(
    () =>
      items.filter((item) => {
        if (filter && bucketOf(item) !== filter) return false;
        if (terms.length === 0) return true;
        return matchesSearch(searchIndex.get(itemKey(item)) ?? "", terms);
      }),
    [items, filter, terms, searchIndex],
  );
  const visibleSelectable = visibleItems.filter(isSelectable);
  const visibleTotal = visibleItems.reduce((sum, item) => sum + item.amount, 0);

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
  const visibleKeys = new Set(visibleItems.map(itemKey));
  const hiddenSelectedCount = selectedItems.filter((item) => !visibleKeys.has(itemKey(item))).length;

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
    if (!nextMonth) return;
    setMonth(nextMonth);
    setSelected({});
    setFilter(null);
    setSearch("");
    setAdvanceOpen(false);
  };

  const openAdvances = (item: PagamentoItem) => {
    if (typeof item.id !== "number") return;
    setAdvanceSalaryId(item.id);
    setAdvanceOpen(true);
  };

  // O id sobrevive ao fechamento (para a animação de saída rodar), então o item continua
  // resolvível enquanto a janela desaparece.
  const advanceItem =
    advanceSalaryId === null
      ? undefined
      : items.find((item) => item.type === "salary" && item.id === advanceSalaryId);

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
      {
        onSuccess: () => {
          setSelected({});
          setConfirmDelete(false);
        },
      },
    );
  };

  // `variables` da mutation em voo diz QUAL ação está rodando — assim só o botão clicado gira,
  // em vez de os quatro spinnerem juntos (Princípio V). Fora do `isPending` ele guarda o último
  // envio, por isso a guarda.
  const runningAction: BulkPaymentAction | null = bulkAction.isPending
    ? bulkAction.variables?.action ?? null
    : null;

  // Erro do lote de EXCLUSÃO fica dentro do diálogo (que continua aberto para nova tentativa);
  // a faixa de status abaixo do cabeçalho cuida das outras três ações.
  const deleteError =
    bulkAction.isError && bulkAction.variables?.action === "delete"
      ? bulkAction.error instanceof Error
        ? bulkAction.error.message
        : "Não foi possível excluir os itens selecionados."
      : null;

  const itemViewProps = (item: PagamentoItem) => ({
    item,
    statusLabels: statusLabels ?? {},
    month,
    selected: Boolean(selected[itemKey(item)]),
    selectable: isSelectable(item),
    onToggleSelect: toggleSelect,
    onOpenAdvances: openAdvances,
  });

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Planilha de Pagamentos"
        subtitle="Cachês, salários, gastos, BVs, comissões e contas recorrentes do mês"
        className="mb-0"
      />

      {/* Navegação de mês: as setas existem para o celular, onde acertar o seletor nativo de
          mês com o dedo é a parte mais difícil da tela. */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-9 w-9 p-0"
            aria-label="Mês anterior"
            onClick={() => handleMonthChange(shiftMonth(month, -1))}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </Button>
          <Input
            type="month"
            value={month}
            onChange={(e) => handleMonthChange(e.target.value)}
            className="h-9 w-[9.5rem]"
            aria-label="Mês de referência"
          />
          <Button
            variant="outline"
            size="sm"
            className="h-9 w-9 p-0"
            aria-label="Mês seguinte"
            onClick={() => handleMonthChange(shiftMonth(month, 1))}
          >
            <ChevronRight className="h-4 w-4" aria-hidden />
          </Button>
        </div>
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
          {/* "Total no período" ocupa a linha inteira no celular; as 4 faixas ficam num 2×2
              embaixo dele, em vez de um card órfão no fim da grade. */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 xl:grid-cols-5">
            <TotalCard
              label="Total no período"
              value={data.totals.total}
              count={items.length}
              bucket={null}
              active={filter === null}
              dimmed={false}
              className="col-span-2 sm:col-span-1"
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

          {/* Busca por qualquer dado da linha — a mesma da planilha antiga, agora varrendo o
              dado (e não o DOM), então ela vale igual para a tabela e para os cartões. */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-0 flex-1 sm:max-w-lg">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
                aria-hidden
              />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por evento, nome, função, valor, PIX, data…"
                aria-label="Buscar na planilha de pagamentos"
                autoComplete="off"
                className="pl-9 pr-10"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  aria-label="Limpar busca"
                  title="Limpar busca"
                  className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-ink"
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
              )}
            </div>
            {terms.length > 0 && (
              <span className="text-xs font-bold tabular-nums text-ink">
                {visibleItems.length} {visibleItems.length === 1 ? "item" : "itens"} ·{" "}
                {brl(visibleTotal)}
              </span>
            )}
          </div>

          <p aria-live="polite" className="sr-only">
            {filter || terms.length > 0
              ? `${visibleItems.length} de ${items.length} itens em exibição.`
              : "Nenhum filtro ativo."}
          </p>

          <Card>
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 pb-2">
              <CardTitle className="text-base">
                Itens de {monthLabel(month)} ({visibleItems.length}
                {visibleItems.length !== items.length ? ` de ${items.length}` : ""})
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
                hiddenCount={hiddenSelectedCount}
                runningAction={runningAction}
                onAction={runBulkAction}
                onRequestDelete={() => setConfirmDelete(true)}
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
                <div className="space-y-3 p-6 text-center text-sm text-muted">
                  {items.length === 0 ? (
                    <p>Nenhum item de pagamento neste mês.</p>
                  ) : (
                    <>
                      <p>
                        Nenhum item
                        {terms.length > 0 ? " para esta busca" : ""}
                        {filter ? ` na faixa “${BUCKET_LABELS[filter]}”` : ""}.
                      </p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {terms.length > 0 && (
                          <Button variant="outline" size="sm" onClick={() => setSearch("")}>
                            Limpar busca
                          </Button>
                        )}
                        {filter && (
                          <Button variant="outline" size="sm" onClick={() => setFilter(null)}>
                            Ver todos os {items.length} itens
                          </Button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <>
                  {/* Celular e tablet: cartões. Uma coluna no telefone, duas do tablet para
                      cima — sem isso, no tablet o cartão esticava para ~900px e o valor ficava
                      a meia tela de distância do nome. `[&>*]:min-w-0` vale em TODOS os
                      breakpoints de propósito: um item de grade sem isso herda
                      `min-width: auto` e se recusa a encolher abaixo do conteúdo (o vazamento
                      lateral que a chave PIX longa causava no telefone). */}
                  <div className="p-3 xl:hidden">
                    <label className="flex min-h-11 items-center gap-2 text-xs font-semibold text-muted">
                      <input
                        type="checkbox"
                        className="h-5 w-5"
                        checked={allVisibleSelected}
                        onChange={toggleSelectAll}
                        disabled={visibleSelectable.length === 0}
                      />
                      Selecionar {visibleSelectable.length}{" "}
                      {visibleSelectable.length === 1 ? "item" : "itens"} em exibição
                    </label>
                    <div className="grid gap-2 md:grid-cols-2 [&>*]:min-w-0">
                      {visibleItems.map((item) => (
                        <PagamentoCard key={itemKey(item)} {...itemViewProps(item)} />
                      ))}
                    </div>
                    {/* Respiro para o rodapé fixo de ações não cobrir o último cartão (a barra
                        tem ~94px: resumo numa linha + botões na outra). */}
                    {selectedItems.length > 0 && <div className="h-28" aria-hidden />}
                  </div>

                  {/* Desktop: a tabela densa de sempre. */}
                  <div className="hidden overflow-x-auto xl:block">
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
                          <PagamentoRow key={itemKey(item)} {...itemViewProps(item)} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Exclusão em lote é a única ação irreversível da tela, e desde a 226 ela é um ícone de
          lixeira de 44px colado no "limpar seleção", num rodapé fixo de celular — o alerta nativo
          do `window.confirm` não mostrava o valor em jogo nem o que a busca escondeu. */}
      <ConfirmDialog
        open={confirmDelete}
        title="Excluir itens da planilha"
        description={
          <>
            <p>
              Excluir <strong className="text-ink">{selectedItems.length}</strong>{" "}
              {selectedItems.length === 1 ? "item selecionado" : "itens selecionados"}, somando{" "}
              <strong className="text-ink tabular-nums">{brl(selectedTotal)}</strong>?
            </p>
            {hiddenSelectedCount > 0 && (
              <p className="mt-2 text-red">
                {hiddenSelectedCount}{" "}
                {hiddenSelectedCount === 1
                  ? "item marcado não está na tela"
                  : "itens marcados não estão na tela"}{" "}
                (o filtro ou a busca escondeu) e {hiddenSelectedCount === 1 ? "será" : "serão"}{" "}
                excluído{hiddenSelectedCount === 1 ? "" : "s"} também.
              </p>
            )}
            <p className="mt-2">Não dá para desfazer.</p>
          </>
        }
        confirmLabel="Excluir"
        destructive
        pending={runningAction === "delete"}
        error={deleteError}
        onConfirm={() => runBulkAction("delete")}
        onOpenChange={(aberto) => !aberto && setConfirmDelete(false)}
      />

      {advanceItem && (
        <SalaryAdvancesDialog
          key={advanceItem.id}
          item={advanceItem}
          open={advanceOpen}
          onClose={() => setAdvanceOpen(false)}
        />
      )}
    </div>
  );
}
