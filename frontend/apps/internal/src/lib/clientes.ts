import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Cliente do CRM (feature 165) — chave real é o telefone normalizado. */
export interface ClientSummary {
  id: number;
  name: string;
  phone: string;
  phone_display: string;
  email: string;
  company: string;
}

export interface ClientListItem extends ClientSummary {
  event_count: number;
}

export interface ClientsListResponse {
  items: ClientListItem[];
  total_clients: number;
}

export interface ClientEvent {
  id: number;
  title: string;
  start_at: string | null;
  relation: string;
}

/** Festa registrada em formulário — inclui as anteriores à agenda de 2026. */
export interface ClientFormHistoryItem {
  id: number;
  form_type_label: string;
  event_date: string | null;
  created_at: string;
  /** Preenchidos quando a festa também existe como evento no calendário. */
  event_id: number | null;
  event_title: string | null;
}

export interface ClientDetail extends ClientSummary {
  cpf: string;
  cnpj: string;
  address: string;
  events: ClientEvent[];
  event_count: number;
  total_sales: number;
  form_history: ClientFormHistoryItem[];
}

/** Um mês do gráfico de novos clientes (origem agregada no servidor). */
export interface ClientsMonthMetric {
  month: string;
  total: number;
  formulario: number;
  kommo: number;
  manual: number;
}

export interface ClientsMetrics {
  new_by_month: ClientsMonthMetric[];
  recurring_clients: number;
  clients_with_event: number;
}

/** Métricas da página de clientes: novos por mês e recorrentes. */
export function useClientsMetrics() {
  return useQuery<ClientsMetrics>({
    queryKey: ["clientes-metricas"],
    queryFn: () => apiFetch<ClientsMetrics>("/api/clientes/metricas"),
  });
}

/** Busca clientes por nome/telefone (sem acentos), feature 165 — usado pelo `ClientPicker`. */
export function useClientSearch(q: string) {
  return useQuery<ClientSummary[]>({
    queryKey: ["clientes-search", q],
    queryFn: () => apiFetch<ClientSummary[]>(`/api/clientes/search?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 2,
  });
}

/** Lista de clientes com contagem de eventos (feature 165). */
export function useClients(q: string) {
  return useQuery<ClientsListResponse>({
    queryKey: ["clientes-list", q],
    queryFn: () => apiFetch<ClientsListResponse>(`/api/clientes/?q=${encodeURIComponent(q)}`),
  });
}

/** Ficha do cliente (feature 165). */
export function useClientDetail(id: number) {
  return useQuery<ClientDetail>({
    queryKey: ["clientes-detail", id],
    queryFn: () => apiFetch<ClientDetail>(`/api/clientes/${id}`),
    enabled: Number.isFinite(id),
  });
}

export interface QuickCreateClientInput {
  name: string;
  phone: string;
  phone_display?: string;
  email?: string;
  company?: string;
  /** Opcionais do cadastro manual pela tela de Clientes (feature 258). */
  cpf?: string;
  cnpj?: string;
  address?: string;
}

export interface QuickCreateClientResult extends ClientSummary {
  reused: boolean;
}

/** Cria um cliente ou reaproveita o existente por telefone (feature 165).
 *
 * Invalida lista e métricas ao criar de verdade (feature 258): a tela de Clientes mostra as duas
 * coisas, e um cadastro que não aparece na lista parece que não salvou. Reaproveitamento
 * (`reused`) não mexe em nada — nada mudou na base. */
export function useQuickCreateClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: QuickCreateClientInput) =>
      apiFetch<QuickCreateClientResult>("/api/clientes/quick-create", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: (result) => {
      if (result.reused) return;
      queryClient.invalidateQueries({ queryKey: ["clientes-list"] });
      queryClient.invalidateQueries({ queryKey: ["clientes-metricas"] });
      queryClient.invalidateQueries({ queryKey: ["clientes-search"] });
    },
  });
}

export interface UpdateClientInput {
  cpf?: string;
  cnpj?: string;
  address?: string;
}

/** Atualiza CPF/CNPJ/endereço do cliente (feature 119, migrado na 165). */
export function useUpdateClient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateClientInput) =>
      apiFetch<ClientDetail>(`/api/clientes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clientes-detail", id] });
    },
  });
}

/** Exclui um cliente, desvinculando eventos associados (feature 165). */
export function useDeleteClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/clientes/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clientes-list"] });
    },
  });
}

export type FeedbackPeriod = "30d" | "90d" | "365d" | "custom" | "all";

/** Evento avaliado, aninhado na avaliação (feature 197). Nulo se o evento foi apagado. */
export interface ClientFeedbackEvent {
  id: number;
  title: string;
  /** ISO de `CalendarEvent.start_at` — data em que o evento aconteceu. */
  event_date: string | null;
}

/**
 * Quem foi atendido. `id` é nulo quando o nome veio do próprio formulário público
 * (`ClientFeedback.client_name`, feature 132) e não de uma cliente cadastrada.
 */
export interface ClientFeedbackClient {
  id: number | null;
  full_name: string;
}

export interface ClientFeedbackItem {
  id: number;
  score: number;
  comment: string;
  tags: string[];
  submitted_at: string | null;
  event: ClientFeedbackEvent | null;
  client: ClientFeedbackClient | null;
}

/** KPIs de satisfação calculados no servidor sobre o recorte filtrado (feature 197). */
export interface ClientFeedbackKpis {
  media_geral: number;
  total_avaliacoes: number;
  percentual_5_estrelas: number;
}

export interface ClientFeedbackFilters {
  period: FeedbackPeriod;
  from?: string;
  to?: string;
  score?: number;
  tag?: string;
  client_id?: number;
}

export interface ClientFeedbackSummary {
  /** Capacidade de excluir avaliações — o servidor decide (SUPERADMIN), a UI só espelha. */
  can_delete?: boolean;
  feedbacks: ClientFeedbackItem[];
  kpis: ClientFeedbackKpis;
  total: number;
  avg_overall: number;
  clients_rated: number;
  dist: Record<string, number>;
  dist_max: number;
  attention: ClientFeedbackItem[];
  clients_with_feedback: { id: number; name: string }[];
  all_tags: string[];
  filters: ClientFeedbackFilters;
}

/**
 * Exclui uma avaliação recebida incorretamente (SUPERADMIN). Invalida a página de
 * satisfação E o prefixo ["event"] — o painel de feedback do detalhe do evento usa o mesmo
 * dado e ficaria com o registro fantasma sem a segunda invalidação.
 */
export function useDeleteClientFeedback() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (feedbackId) =>
      apiFetch<void>(`/api/clientes/avaliacoes/${feedbackId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["clientes-avaliacoes"] });
      void queryClient.invalidateQueries({ queryKey: ["event"] });
    },
  });
}

/** Resumo do feedback das clientes (feature 130/131), migrado na 165. */
export function useClientFeedback(filters: ClientFeedbackFilters) {
  const params = new URLSearchParams({ period: filters.period });
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.score) params.set("score", String(filters.score));
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.client_id) params.set("client_id", String(filters.client_id));
  return useQuery<ClientFeedbackSummary>({
    queryKey: ["clientes-avaliacoes", filters],
    queryFn: () => apiFetch<ClientFeedbackSummary>(`/api/clientes/avaliacoes?${params.toString()}`),
  });
}
