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

export interface ClientDetail extends ClientSummary {
  cpf: string;
  cnpj: string;
  address: string;
  events: ClientEvent[];
  event_count: number;
  total_sales: number;
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
}

export interface QuickCreateClientResult extends ClientSummary {
  reused: boolean;
}

/** Cria um cliente ou reaproveita o existente por telefone (feature 165). */
export function useQuickCreateClient() {
  return useMutation({
    mutationFn: (input: QuickCreateClientInput) =>
      apiFetch<QuickCreateClientResult>("/api/clientes/quick-create", {
        method: "POST",
        body: JSON.stringify(input),
      }),
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

export interface ClientFeedbackItem {
  id: number;
  score: number;
  tags: string[];
  submitted_at: string | null;
  event_title: string;
  client_name: string;
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
  feedbacks: ClientFeedbackItem[];
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
