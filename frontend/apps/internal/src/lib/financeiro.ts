import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@manto/api-client";

export type PeriodFilter = "este_mes" | "30d" | "mes_anterior" | "custom";

/** Uma das 3 visões do DRE gerencial (feature 157). */
export interface DreView {
  receita_bruta: number;
  impostos: number;
  receita_liquida: number;
  cpv: number;
  lucro_bruto: number;
  margem_bruta: number;
  marketing: number;
  comissoes: number;
  pessoal: number;
  ebitda: number;
  margem_ebitda: number;
  gastos_extras: number;
  gastos_recorrentes: number;
  resultado_liquido: number;
  n_eventos: number;
  n_normais: number;
  n_permutas: number;
}

export interface FinanceiroKpis {
  ticket_medio: number;
  ratio_custo_talento: number;
  /** Margem bruta e EBITDA do consolidado (`dre.total`), já em % — feature 189. */
  margem_bruta: number;
  margem_ebitda: number;
  breakeven_pct: number;
  breakeven_atingido: boolean;
  fixed_cost: number;
  fator_r_pct: number;
  fator_r_threshold: number;
  fator_r_protegido: boolean;
  /** Alíquota de imposto provisionado (SiteSetting.tax_rate), em % — feature 189. */
  tax_rate: number;
  /** Rótulos das faixas de alíquota do Fator R (strings, ex.: "6" e "15,5"). */
  fator_r_rate_low: string;
  fator_r_rate_high: string;
}

export interface TopSeller {
  user_id: number;
  user_name: string;
  receita: number;
  lucro: number;
}

export interface MonthlyTrendItem {
  label: string;
  receita: number;
  custo: number;
  lucro: number;
  margem: number;
  n_eventos: number;
}

export interface AuditoriaItem {
  event_id: number;
  title: string;
  start_at: string | null;
}

/**
 * Consolidado do canal Loja de Interações Virtuais (feature 205, FR-053).
 *
 * A receita já está somada na cascata do DRE — este bloco só diz **quanto** dela veio da loja.
 */
export interface LojaVirtualResumo {
  canal: string;
  vendas: number;
  receita: number;
  ticket_medio: number;
}

export interface FinanceiroPaineis {
  a_receber_clientes: number;
  pagamentos_pendentes: number;
  pagamentos_realizados: number;
  receita_por_tipo: Record<string, number>;
  receita_tipo_max: number;
  loja_virtual: LojaVirtualResumo;
  /** Reflete o opt-in explícito do gestor (FR-055) — por padrão `false`. */
  incluir_loja_virtual: boolean;
  top_sellers: TopSeller[];
  monthly_trend: MonthlyTrendItem[];
  auditoria: AuditoriaItem[];
}

export type EventoStatus = "permuta" | "sem_valor" | "pago_total" | "parcial" | "pendente";

export interface FinanceiroEvento {
  event_id: number;
  title: string;
  group_label: string | null;
  start_at: string | null;
  /** Tipo do evento (SHOW/CORP/R&I…) e receita bruta da linha — feature 189. */
  event_type: string | null;
  receita: number;
  custo: number;
  lucro: number;
  comissao: number;
  rate: number;
  is_projetado: boolean;
  status: EventoStatus;
}

export interface RecebimentoPrevisto {
  date: string | null;
  event_id: number;
  event_title: string;
  amount: number;
}

export interface NotaFiscalPendente {
  id: number;
  date: string | null;
  event_id: number;
  event_title: string;
  amount: number;
}

export interface CustoNotaItem {
  event_id: number;
  event_title: string;
  amount: number;
  date: string | null;
  status: string;
  custo: number;
}

export interface FinanceiroPendencias {
  recebimentos_previstos: RecebimentoPrevisto[];
  recebimentos_previstos_total: number;
  nf_a_emitir: NotaFiscalPendente[];
  nf_a_emitir_total: number;
  custo_nota_itens: CustoNotaItem[];
  custo_nota_total: number;
}

export interface FinanceiroDashboard {
  period: PeriodFilter;
  period_label: string;
  start: string;
  end: string;
  is_full_month: boolean;
  dre: { realizado: DreView; projetado: DreView; total: DreView };
  kpis: FinanceiroKpis;
  paineis: FinanceiroPaineis;
  eventos: FinanceiroEvento[];
  pendencias: FinanceiroPendencias;
}

export interface PeriodParams {
  period: PeriodFilter;
  start?: string;
  end?: string;
  /** Desativa a busca (ex.: período "custom" ainda sem datas aplicadas). */
  enabled?: boolean;
  /**
   * Opt-in explícito para somar a Loja Virtual aos indicadores **de evento** (FR-055).
   *
   * Fora daqui a receita da loja já entra na cascata do DRE: o que este parâmetro muda é só o
   * ticket médio e o "a receber", que por padrão contam apenas evento presencial.
   */
  incluirLojaVirtual?: boolean;
}

/** Dashboard financeiro (DRE), feature 157 — Financeiro/Superadmin. */
export function useFinanceiroDashboard({
  period,
  start,
  end,
  enabled = true,
  incluirLojaVirtual = false,
}: PeriodParams) {
  const params = new URLSearchParams({ period });
  if (period === "custom" && start && end) {
    params.set("start", start);
    params.set("end", end);
  }
  if (incluirLojaVirtual) params.set("incluir_loja_virtual", "1");
  return useQuery<FinanceiroDashboard>({
    queryKey: ["financeiro-dashboard", period, start, end, incluirLojaVirtual],
    queryFn: () => apiFetch<FinanceiroDashboard>(`/api/financeiro/dashboard?${params.toString()}`),
    enabled: enabled && (period !== "custom" || Boolean(start && end)),
  });
}

export type CommissionStatus = "a_pagar" | "pago" | "cancelado";
export type CommissionMonthStatus = "pendente" | "pago";

/** Uma linha de comissão (`CommissionPayment`), feature 158 (payload evoluído na 187). */
export interface CommissionEntry {
  id: number;
  seller_id: number;
  seller_name: string;
  event_id: number | null;
  event_title: string;
  sale_date: string | null;
  amount: number;
  status: CommissionStatus;
  status_label: string;
  paid_at: string | null;
}

export interface CommissionSeller {
  id: number;
  name: string;
}

/** Os 3 KPIs do topo da tela de Comissões (feature 187). */
export interface CommissionKpis {
  total_month: number;
  total_paid: number;
  total_pending: number;
}

/** Uma linha agregada por vendedor — visão "Resumo por Vendedor" (feature 187). */
export interface CommissionMonthSummaryRow {
  seller_id: number;
  seller_name: string;
  sale_count: number;
  total_amount: number;
  pending_amount: number;
  month_status: CommissionMonthStatus;
  entries: CommissionEntry[];
}

export interface ComissoesResponse {
  month: string;
  can_manage: boolean;
  title: string;
  kpis: CommissionKpis;
  by_seller: CommissionMonthSummaryRow[];
  entries: CommissionEntry[];
  sellers?: CommissionSeller[];
}

/**
 * Comissões do mês (leitura), feature 158 — reestruturada na 187.
 * `sellerId` só tem efeito para Financeiro/Superadmin (`can_manage`); o servidor ignora/força
 * ao próprio usuário caso contrário — o filtro aqui é só conveniência de UI, nunca a fonte de
 * verdade do RBAC.
 */
export function useComissoes(month: string, sellerId?: number | null) {
  const params = new URLSearchParams({ month });
  if (sellerId != null) params.set("seller_id", String(sellerId));
  return useQuery<ComissoesResponse>({
    queryKey: ["financeiro-comissoes", month, sellerId ?? null],
    queryFn: () => apiFetch<ComissoesResponse>(`/api/financeiro/comissoes?${params.toString()}`),
  });
}

export interface PagarMesComissaoInput {
  seller_id: number;
  month: string;
}

export interface PagarMesComissaoResult {
  seller_id: number;
  month: string;
  changed_count: number;
  paid_total: number;
  summary: CommissionMonthSummaryRow | null;
}

/**
 * Liquidação em lote atômica de um vendedor/mês (feature 187) — Financeiro/Superadmin.
 * Invalida a query de leitura no sucesso para refletir KPIs/status sem F5 (FR-013).
 */
export function usePagarMesComissao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PagarMesComissaoInput) =>
      apiFetch<PagarMesComissaoResult>("/api/financeiro/comissoes/pagar-mes", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
    },
  });
}

/** Gera e baixa um CSV do resumo por vendedor do mês selecionado (feature 187) — client-side,
 * a partir dos mesmos dados já carregados na tela (garante que bate com os KPIs exibidos). */
export function exportComissoesCsv(rows: CommissionMonthSummaryRow[], month: string): void {
  const header = ["Vendedor", "Qtd de Vendas", "Valor Total (R$)", "Status"];
  const lines = rows.map((r) =>
    [
      r.seller_name,
      String(r.sale_count),
      r.total_amount.toFixed(2).replace(".", ","),
      r.month_status === "pago" ? "Pago" : "Pendente",
    ]
      .map((cell) => `"${cell.replace(/"/g, '""')}"`)
      .join(";"),
  );
  const csv = [header.join(";"), ...lines].join("\r\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `comissoes_${month}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export type PagamentoItemType = "cache" | "salary" | "expense" | "bv" | "commission" | "recurring";
export type PaymentStatus = "nao_pago" | "pago" | "no_banco";

export interface SalaryAdvanceItem {
  id: number;
  amount: number;
  date: string | null;
  proof: string;
}

/** Um item da planilha de pagamentos (feature 159) — forma varia um pouco por `type`. */
export interface PagamentoItem {
  type: PagamentoItemType;
  id: number | string;
  date: string | null;
  event_title: string | null;
  event_id: number | null;
  copy_label: string | null;
  sublabel: string | null;
  person_name: string | null;
  amount: number;
  pix_key: string;
  pix_key_type: string;
  status: PaymentStatus;
  is_future: boolean;
  gross_amount?: number;
  advance_amount?: number;
  advances?: SalaryAdvanceItem[];
  missing_data?: boolean;
}

export interface PagamentoTotals {
  total: number;
  pago: number;
  no_banco: number;
  pendente: number;
  futuro: number;
}

export interface PagamentosResponse {
  month: string;
  totals: PagamentoTotals;
  status_labels: Record<PaymentStatus, string>;
  items: PagamentoItem[];
}

/** Planilha de pagamentos do mês (leitura), feature 159 — Financeiro/Superadmin. */
export function usePagamentos(month: string) {
  return useQuery<PagamentosResponse>({
    queryKey: ["financeiro-pagamentos", month],
    queryFn: () => apiFetch<PagamentosResponse>(`/api/financeiro/pagamentos?month=${month}`),
  });
}

export interface SetPaymentStatusInput {
  item_type: PagamentoItemType;
  item_id: number | string;
  status: PaymentStatus;
}

/** Marca o status de um item de pagamento (feature 160). */
export function useSetPaymentStatus(month: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SetPaymentStatusInput) =>
      apiFetch<{ status: PaymentStatus }>("/api/financeiro/pagamentos/set-status", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos", month] });
    },
  });
}

export type BulkPaymentAction = PaymentStatus | "delete";

export interface BulkPaymentActionInput {
  action: BulkPaymentAction;
  role_ids: number[];
  salary_ids: number[];
  expense_ids: number[];
  commission_ids: string[];
  month: string;
}

export interface BulkPaymentActionResult {
  changed: number;
  skipped: string[];
}

/** Aplica uma ação em massa (status ou excluir) sobre itens selecionados (feature 160). */
export function useBulkPaymentAction(month: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: BulkPaymentActionInput) =>
      apiFetch<BulkPaymentActionResult>("/api/financeiro/pagamentos/bulk-action", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos", month] });
    },
  });
}

export interface AddSalaryAdvanceInput {
  salaryPaymentId: number;
  amount: string;
  advanceDate?: string;
  proof: File;
}

/** Registra um adiantamento de salário (valor + comprovante), feature 160. */
export function useAddSalaryAdvance(month: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ salaryPaymentId, amount, advanceDate, proof }: AddSalaryAdvanceInput) => {
      const form = new FormData();
      form.set("amount", amount);
      if (advanceDate) form.set("advance_date", advanceDate);
      form.set("advance_proof", proof);
      return apiFetch<SalaryAdvanceItem>(
        `/api/financeiro/pagamentos/salary/${salaryPaymentId}/advance`,
        { method: "POST", body: form },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos", month] });
    },
  });
}

/** Exclui um adiantamento de salário já registrado (feature 160). */
export function useDeleteSalaryAdvance(month: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (advanceId: number) =>
      apiFetch<void>(`/api/financeiro/pagamentos/salary/advance/${advanceId}/delete`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos", month] });
    },
  });
}

/** Baixa o CSV de pagamentos do mês (feature 160) — dispara o download via blob. */
export function useExportPagamentosCsv() {
  return useMutation({
    mutationFn: async (month: string) => {
      const blob = await apiFetchBlob(`/api/financeiro/pagamentos/export?month=${month}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pagamentos_${month}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
  });
}
