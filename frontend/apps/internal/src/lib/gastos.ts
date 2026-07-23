import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export type ExpenseStatus = "pendente" | "aprovado" | "rejeitado";
export type DisbursementType = "reembolso" | "fornecedor" | null;

export interface GastoExtra {
  id: number;
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
  disbursement_type?: "reembolso" | "fornecedor" | "";
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
  entry: RecurringEntry | null;
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
  is_current_month: boolean;
  type_labels: Record<RecurringType, string>;
  frequency_labels: Record<RecurringFrequency, string>;
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
