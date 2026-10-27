import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { BUCKET_TONE, matchesSearch, normalizeSearch, rawAmount, type BucketTone } from "./pagamentos";

export type ExpenseStatus = "pendente" | "aprovado" | "rejeitado";
/** `cliente` = devolução à cliente: nasce só pelo cancelamento do evento (feature 306). */
export type DisbursementType = "reembolso" | "fornecedor" | "cliente" | null;

/** Lote de reembolso gerado pelo auditor de marketing (feature 256) — detalhe por campanha. */
export interface GastoMarketingBatch {
  platform: string;
  month_ref: string;
  reported_total: string;
  frozen: boolean;
  run_id: string | null;
  lines: { campaign_name: string; amount: string; clicks: number | null; results: number | null }[];
}

export interface GastoExtra {
  id: number;
  /** Presente só nos gastos criados pelo auditor de marketing; `null` nos demais. */
  marketing_batch: GastoMarketingBatch | null;
  description: string;
  category: string;
  amount: number;
  expense_date: string;
  status: ExpenseStatus;
  approved_with_edits: boolean;
  notes: string;
  receipt_url: string | null;
  disbursement_type: DisbursementType;
  payee_name: string;
  payee_pix: string;
  payment_status: string;
  paid_at_creation: boolean;
  event_id: number | null;
  event_title: string | null;
  created_by_name: string | null;
  created_at: string;
  approved_by_name: string | null;
  approved_at: string | null;
  /**
   * Feature 306: devolução de evento cancelado — valor, data, categoria e vínculo travados (só o
   * "Alterar devolução" do evento os muda). Opcionais: backend antigo.
   */
  locked?: boolean;
  event_cancelled?: boolean;
  /**
   * Feature 314: situação única do gasto nesta tela, calculada no servidor
   * (`gastos_ops.situacao_do_gasto`). Opcional porque backend e bundle ficam em versões diferentes
   * por alguns minutos em todo deploy — sem ela, vale `situacaoDe`.
   */
  situacao?: GastoSituacao;
}

/** Feature 314 — onde o gasto está: esperando aprovação, no caminho do pagamento, resolvido ou recusado. */
export type GastoSituacao = "aguardando_aprovacao" | "a_pagar" | "no_banco" | "pago" | "rejeitado";

/** Ordem dos cartões-filtro e de leitura da tela. */
export const SITUACAO_ORDEM: GastoSituacao[] = [
  "aguardando_aprovacao",
  "a_pagar",
  "no_banco",
  "pago",
  "rejeitado",
];

/** As que pedem ação: ficam na lista principal. Pagos e rejeitados abrem recolhidos. */
export const SITUACOES_A_VISTA: ReadonlySet<GastoSituacao> = new Set([
  "aguardando_aprovacao",
  "a_pagar",
  "no_banco",
]);

/** Rótulo de um gasto (selo da linha). */
export const SITUACAO_LABELS: Record<GastoSituacao, string> = {
  aguardando_aprovacao: "Aguardando aprovação",
  a_pagar: "A pagar",
  no_banco: "No banco",
  pago: "Pago",
  rejeitado: "Rejeitado",
};

/** Rótulo do cartão-filtro e do grupo (vários gastos). */
export const SITUACAO_LABELS_GRUPO: Record<GastoSituacao, string> = {
  aguardando_aprovacao: "Aguardando aprovação",
  a_pagar: "A pagar",
  no_banco: "No banco",
  pago: "Pagos",
  rejeitado: "Rejeitados",
};

/**
 * Cores por situação. A pagar, no banco e pago repetem as de Pagamentos (pendente, no banco, pago),
 * para o mesmo gasto ter a mesma cor nas duas telas. Aguardando usa o `gold` de atenção. Rejeitado
 * é neutro: é um fim, não pede nada.
 */
export const SITUACAO_TONE: Record<GastoSituacao, BucketTone> = {
  aguardando_aprovacao: BUCKET_TONE.futuro,
  a_pagar: BUCKET_TONE.pendente,
  no_banco: BUCKET_TONE.no_banco,
  pago: BUCKET_TONE.pago,
  rejeitado: {
    row: "",
    cardActive: "border-line-strong bg-surface-2 ring-2 ring-line",
    text: "text-muted",
    select: "border-line bg-surface-2 text-muted",
  },
};

/**
 * Situação do gasto para a tela. Com o backend da 314 é sempre `situacao`. Sem ela (bundle novo,
 * backend velho, nos minutos do deploy), o aprovado cai do lado seguro, "a pagar", à vista: sem a
 * regra do servidor não se sabe se ele já foi pago, e um gasto escondido por engano é pior que um a
 * mais na lista. Pendente e rejeitado não dependem da regra.
 */
export function situacaoDe(expense: GastoExtra): GastoSituacao {
  if (expense.situacao) return expense.situacao;
  if (expense.status === "pendente") return "aguardando_aprovacao";
  if (expense.status === "rejeitado") return "rejeitado";
  return "a_pagar";
}

/** A data do gasto chega pura ("2026-10-17"): recorte de string, nunca `new Date` (armadilha 1). */
export function formatarDataGasto(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/** Filtro de desembolso da tela; `nenhum` = gasto sem ninguém a pagar. */
export type DesembolsoFiltro = "reembolso" | "fornecedor" | "cliente" | "nenhum";

export const DESEMBOLSO_FILTRO_LABELS: Record<DesembolsoFiltro, string> = {
  reembolso: "Reembolso",
  fornecedor: "Fornecedor",
  cliente: "Devolução à cliente",
  nenhum: "Sem desembolso",
};

/** O recorte da tela, que mora na URL (`busca`, `categoria`, `desembolso`, `mes`, `situacao`). */
export interface FiltrosDeGastos {
  busca: string;
  categoria: string | null;
  desembolso: DesembolsoFiltro | null;
  /** "AAAA-MM"; `null` = todos os meses (a abertura — nenhum pendente antigo some). */
  mes: string | null;
  situacao: GastoSituacao | null;
}

const MES_VALIDO = /^\d{4}-(0[1-9]|1[0-2])$/;

/**
 * Lê o recorte da URL. Valor desconhecido (categoria que não existe, mês malformado, situação
 * inventada) vira "sem esse filtro" (FR-011): um link velho ou digitado errado abre a tela inteira,
 * nunca uma lista vazia sem explicação.
 */
export function lerFiltrosDaUrl(params: URLSearchParams, categorias: readonly string[]): FiltrosDeGastos {
  const categoria = params.get("categoria");
  const desembolso = params.get("desembolso");
  const mes = params.get("mes");
  const situacao = params.get("situacao");
  return {
    busca: params.get("busca") ?? "",
    categoria: categoria && categorias.includes(categoria) ? categoria : null,
    desembolso: desembolso && desembolso in DESEMBOLSO_FILTRO_LABELS ? (desembolso as DesembolsoFiltro) : null,
    mes: mes && MES_VALIDO.test(mes) ? mes : null,
    situacao: situacao && (SITUACAO_ORDEM as string[]).includes(situacao) ? (situacao as GastoSituacao) : null,
  };
}

/**
 * Texto pesquisável de um gasto — a busca varre o DADO, não o DOM, então vale igual para a tabela e
 * para o cartão. O valor entra formatado ("1.234,56") e cru ("1234,56"), como em Pagamentos.
 */
export function searchIndexOfGasto(expense: GastoExtra): string {
  return normalizeSearch(
    [
      formatarDataGasto(expense.expense_date),
      expense.expense_date,
      expense.description,
      expense.notes,
      expense.category,
      expense.payee_name,
      expense.payee_pix,
      expense.event_title ?? "",
      expense.created_by_name ?? "",
      SITUACAO_LABELS[situacaoDe(expense)],
      formatBRL(expense.amount),
      rawAmount(expense.amount),
    ].join(" "),
  );
}

/**
 * Aplica busca, categoria, desembolso e mês — de propósito NÃO a situação: os cartões-filtro somam
 * este recorte, e escolher "A pagar" não pode zerar os outros cartões (FR-009).
 */
export function filtrarGastos(
  expenses: GastoExtra[],
  filtros: FiltrosDeGastos,
  terms: string[],
  indice: ReadonlyMap<number, string>,
): GastoExtra[] {
  return expenses.filter((e) => {
    if (filtros.categoria && e.category !== filtros.categoria) return false;
    if (filtros.desembolso === "nenhum" && e.disbursement_type) return false;
    if (filtros.desembolso && filtros.desembolso !== "nenhum" && e.disbursement_type !== filtros.desembolso) {
      return false;
    }
    if (filtros.mes && !e.expense_date.startsWith(filtros.mes)) return false;
    return terms.length === 0 || matchesSearch(indice.get(e.id) ?? "", terms);
  });
}

export interface GastosTotal {
  count: number;
  total: number;
}

export interface GastosTotals {
  todos: GastosTotal;
  pendente: GastosTotal;
  aprovado: GastosTotal;
  rejeitado: GastosTotal;
}

export interface GastosExtrasResponse {
  expenses: GastoExtra[];
  /** FINANCEIRO/SUPERADMIN: gestão completa de todos os gastos. Demais: só os próprios. */
  can_manage: boolean;
  categories: string[];
  /** Só presente quando `can_manage` é `true`. */
  totals?: GastosTotals;
}

/** Gastos extras (feature 128/177/179) — FINANCEIRO/SUPERADMIN vê todos, demais só os próprios. */
export function useGastosExtras() {
  return useQuery<GastosExtrasResponse>({
    queryKey: ["gastos-extras"],
    queryFn: () => apiFetch<GastosExtrasResponse>("/api/gastos"),
  });
}

export interface GastoEvento {
  id: number;
  label: string;
}

/** Eventos de uma data, para o seletor de vínculo de um gasto. */
export function useGastosEventos(date: string) {
  return useQuery<{ events: GastoEvento[] }>({
    queryKey: ["gastos-eventos", date],
    queryFn: () => apiFetch<{ events: GastoEvento[] }>(`/api/gastos/eventos?date=${date}`),
    enabled: Boolean(date),
  });
}

export interface GastoFuncionario {
  id: number;
  name: string;
}

/** Colaboradores ativos, para o seletor de "Reembolso a funcionário". */
export function useGastosFuncionarios() {
  return useQuery<{ funcionarios: GastoFuncionario[] }>({
    queryKey: ["gastos-funcionarios"],
    queryFn: () => apiFetch<{ funcionarios: GastoFuncionario[] }>("/api/gastos/funcionarios"),
    staleTime: 5 * 60 * 1000,
  });
}

export interface CreateGastoInput {
  description: string;
  category: string;
  amount: number;
  expense_date: string;
  notes?: string;
  disbursement_type?: "reembolso" | "fornecedor" | "";
  reimburse_user_id?: number;
  supplier_name?: string;
  supplier_pix?: string;
  paid_at_creation?: boolean;
  event_id?: number;
  receipt: File;
}

/** Registra um novo gasto extra (multipart — comprovante obrigatório). */
export function useCreateGasto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateGastoInput) => {
      const form = new FormData();
      form.set("description", input.description);
      form.set("category", input.category);
      form.set("amount", String(input.amount));
      form.set("expense_date", input.expense_date);
      if (input.notes) form.set("notes", input.notes);
      if (input.disbursement_type) form.set("disbursement_type", input.disbursement_type);
      if (input.reimburse_user_id) form.set("reimburse_user_id", String(input.reimburse_user_id));
      if (input.supplier_name) form.set("supplier_name", input.supplier_name);
      if (input.supplier_pix) form.set("supplier_pix", input.supplier_pix);
      if (input.paid_at_creation) form.set("paid_at_creation", "true");
      if (input.event_id) form.set("event_id", String(input.event_id));
      form.set("receipt", input.receipt);
      return apiFetch<GastoExtra>("/api/gastos", { method: "POST", body: form });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

export interface UpdateGastoInput {
  id: number;
  description: string;
  category: string;
  amount: number;
  expense_date: string;
  /** `cliente` só se o gasto já era devolução à cliente (o servidor recusa a conversão). */
  disbursement_type?: "reembolso" | "fornecedor" | "cliente" | "";
  reimburse_user_id?: number;
  supplier_name?: string;
  supplier_pix?: string;
  event_id?: number | null;
  /** Aprova (ou reconsidera, se rejeitado) o gasto nesta mesma edição. */
  aprovar?: boolean;
}

/** Edita um gasto (qualquer status, exceto rejeitado sem `aprovar`). FINANCEIRO/SUPERADMIN. */
export function useUpdateGasto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: UpdateGastoInput) =>
      apiFetch<GastoExtra>(`/api/gastos/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

/** Aprova um gasto pendente, sem edição (FINANCEIRO/SUPERADMIN). */
export function useApproveGasto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<GastoExtra>(`/api/gastos/${id}/aprovar`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

/** Rejeita um gasto pendente com motivo opcional (SUPERADMIN). */
export function useRejectGasto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo?: string }) =>
      apiFetch<GastoExtra>(`/api/gastos/${id}/rejeitar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

/** Exclui um gasto (autor enquanto pendente, ou SUPERADMIN sempre). */
export function useDeleteGasto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/gastos/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

/** Vincula/remove o evento de um gasto (SUPERADMIN). */
export function useLinkGastoEvento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, event_id }: { id: number; event_id: number | null }) =>
      apiFetch<GastoExtra>(`/api/gastos/${id}/vincular-evento`, {
        method: "POST",
        body: JSON.stringify({ event_id }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gastos-extras"] }),
  });
}

// ══════════════════════════════════════════════════════════════════
//  Gastos Recorrentes (feature 110/177)
// ══════════════════════════════════════════════════════════════════

export type RecurringType = "variavel" | "debito_automatico" | "assinatura" | "programado";
export type RecurringFrequency = "mensal" | "semanal" | "quinzenal" | "anual";
export type EntryStatus = "a_pagar" | "pago" | "registrado" | "pulado";

export interface RecurringEntry {
  id: number;
  recurring_id: number;
  month_ref: string;
  amount: number | null;
  pix: string | null;
  due_date: string | null;
  status: EntryStatus;
  out_of_range: boolean;
  paid_at: string | null;
}

export interface RecurringExpenseItem {
  id: number;
  name: string;
  expense_type: RecurringType;
  amount: number | null;
  amount_min: number | null;
  amount_max: number | null;
  due_day: number;
  frequency: RecurringFrequency;
  weekday: number | null;
  start_date: string;
  end_date: string | null;
  default_pix: string | null;
  card_name: string | null;
  notes: string | null;
  is_active: boolean;
  /** Rótulo da faixa/valor esperado — só conta variável (feature 189). */
  expected_label: string | null;
  /** "dia 10" / "toda semana (terça)" — rótulo do vencimento. */
  dia_label: string;
  /** "desde 01/2026" / "01/2026 – 12/2026" — vigência da conta. */
  vigencia_label: string;
  /** "3 parcelas · R$ 4.500,00 no total" — só pagamento programado. */
  parcelas_summary: string | null;
  /** Custo mensal estimado (frequência normalizada para mês). */
  estimated_monthly: number;
  /** True se a conta já tem lançamentos — bloqueia exclusão (o caminho é desativar). */
  has_entries: boolean;
  /** Cobranças no mês de referência; `0` = fora do ciclo/vigência. `null` fora da listagem. */
  occurrences: number | null;
  entry: RecurringEntry | null;
  /** Todas as parcelas — preenchido só para `programado`. */
  entries: RecurringEntry[] | null;
}

export interface RecurringAlert {
  recurring_id: number;
  name: string;
  estado: "aguardando" | "a_pagar";
  entry: RecurringEntry | null;
}

export interface GastosRecorrentesResponse {
  grupos: Record<RecurringType, RecurringExpenseItem[]>;
  month_ref: string;
  ref_year: number;
  ref_month: number;
  is_current_month: boolean;
  type_labels: Record<RecurringType, string>;
  frequency_labels: Record<RecurringFrequency, string>;
  weekday_labels: string[];
  /** Estimativa mensal por tipo (só contas ativas) — feature 189. */
  somas: Record<RecurringType, number>;
  /** Total ainda a pagar das parcelas de pagamentos programados ativos. */
  programado_pendente_total: number;
  alerts: RecurringAlert[];
}

/** Contas recorrentes por tipo + lançamento do mês + alertas (FINANCEIRO/SUPERADMIN). */
export function useGastosRecorrentes(monthRef?: string) {
  return useQuery<GastosRecorrentesResponse>({
    queryKey: ["gastos-recorrentes", monthRef ?? "current"],
    queryFn: () =>
      apiFetch<GastosRecorrentesResponse>(
        `/api/gastos/recorrentes${monthRef ? `?month=${monthRef}` : ""}`,
      ),
  });
}

export interface RecorrenteHistorico {
  conta_id: number;
  conta_name: string;
  entries: RecurringEntry[];
}

/**
 * Histórico completo de lançamentos de uma conta (feature 189) — equivale ao painel
 * `?conta=<id>` da tela Jinja legada. Só busca quando `contaId` está definido (Dialog aberto).
 */
export function useRecorrenteHistorico(contaId: number | null) {
  return useQuery<RecorrenteHistorico>({
    queryKey: ["gastos-recorrentes-historico", contaId],
    queryFn: () => apiFetch<RecorrenteHistorico>(`/api/gastos/recorrentes/${contaId}/historico`),
    enabled: contaId != null,
  });
}

export interface CreateRecorrenteInput {
  name: string;
  expense_type: RecurringType;
  frequency?: RecurringFrequency;
  weekday?: number;
  due_day?: number;
  amount?: number;
  ref_mode?: "faixa" | "exato";
  amount_min?: number;
  amount_max?: number;
  start_date?: string;
  end_date?: string;
  default_pix?: string;
  card_name?: string;
  notes?: string;
  parcelas?: { date: string; amount: number }[];
}

function invalidateRecorrentes(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["gastos-recorrentes"] });
}

/** Cadastra uma conta recorrente (ou pagamento programado, via `expense_type: "programado"`). */
export function useCreateRecorrente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateRecorrenteInput) =>
      apiFetch<RecurringExpenseItem>("/api/gastos/recorrentes", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Edita uma conta recorrente comum. */
export function useUpdateRecorrente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: CreateRecorrenteInput & { id: number }) =>
      apiFetch<RecurringExpenseItem>(`/api/gastos/recorrentes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Ativa/desativa uma conta recorrente. */
export function useToggleRecorrente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<RecurringExpenseItem>(`/api/gastos/recorrentes/${id}/toggle`, { method: "POST" }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Exclui uma conta recorrente sem lançamentos (com histórico, o caminho é desativar). */
export function useDeleteRecorrente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/gastos/recorrentes/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Preenche a conta variável do mês (valor + PIX + vencimento): lançamento a pagar. */
export function useFillEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      contaId,
      amount,
      pix,
      due_date,
      month_ref,
    }: {
      contaId: number;
      amount: number;
      pix?: string;
      due_date?: string;
      month_ref?: string;
    }) =>
      apiFetch<RecurringEntry>(`/api/gastos/recorrentes/${contaId}/preencher`, {
        method: "POST",
        body: JSON.stringify({ amount, pix, due_date, month_ref }),
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Pula o mês de uma conta variável (boleto não veio). */
export function useSkipEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contaId, month_ref }: { contaId: number; month_ref?: string }) =>
      apiFetch<RecurringEntry>(`/api/gastos/recorrentes/${contaId}/pular`, {
        method: "POST",
        body: JSON.stringify({ month_ref }),
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Marca um lançamento a pagar como pago. */
export function usePayEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) =>
      apiFetch<RecurringEntry>(`/api/gastos/recorrentes/entry/${entryId}/pagar`, {
        method: "POST",
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Reabre um lançamento (pago volta a "a pagar"; pulado é removido). */
export function useReopenEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) =>
      apiFetch<RecurringEntry | undefined>(`/api/gastos/recorrentes/entry/${entryId}/reabrir`, {
        method: "POST",
      }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}

/** Exclui uma parcela avulsa de pagamento programado ainda não paga. */
export function useDeleteEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: number) =>
      apiFetch<void>(`/api/gastos/recorrentes/entry/${entryId}`, { method: "DELETE" }),
    onSuccess: () => invalidateRecorrentes(queryClient),
  });
}
