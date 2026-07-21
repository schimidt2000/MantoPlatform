import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

/** Opções do formulário de criação de evento (feature 152) — `GET /api/events/new/options`. */
export interface EventCreateOptions {
  figurino_sheets: { id: number; character_name: string; photo_url: string | null }[];
  sellers: { id: number; name: string }[];
  assignable_talents: { id: number; name: string }[];
  client_relation_tipos: string[];
}

export function useEventCreateOptions() {
  return useQuery<EventCreateOptions>({
    queryKey: ["event-create-options"],
    queryFn: () => apiFetch<EventCreateOptions>("/api/events/new/options"),
    staleTime: 5 * 60 * 1000,
  });
}

/** Cachê de um item do orçamento, por duração (feature 152). */
export interface OrcamentoCache {
  label: string;
  cache_1h: number;
  cache_2h: number;
  cache_3h: number;
  cache_4h: number;
  needs_makeup: boolean;
  is_singer: boolean;
  role_type: string;
}

/** Pré-preenchimento a partir de um orçamento salvo — `GET /api/events/new/prefill`. */
export interface OrcamentoPrefill {
  orcamento_id?: number;
  date?: string;
  start_time?: string;
  location?: string;
  client_name?: string;
  total_1h?: number;
  total_2h?: number;
  total_3h?: number;
  total_4h?: number;
  total_custom?: number | null;
  duracao_custom?: number | null;
  has_show?: boolean;
  transport_value?: number;
  acrescimo_value?: number;
  acrescimos?: unknown[];
  with_invoice?: boolean;
  caches?: OrcamentoCache[];
}

export function useOrcamentoPrefill(orcamentoId: number | null) {
  return useQuery<OrcamentoPrefill>({
    queryKey: ["orcamento-prefill", orcamentoId],
    queryFn: () =>
      apiFetch<OrcamentoPrefill>(`/api/events/new/prefill?orcamento_id=${orcamentoId}`),
    enabled: orcamentoId != null,
  });
}

export interface CharacterInput {
  name: string;
  figurino_sheet_id: number | null;
  cache_value: number | null;
  needs_makeup: boolean;
  is_singer: boolean;
  talent_id: number | null;
}

export interface ObservationInput {
  obs_type: "text" | "link";
  content: string;
  label: string;
}

export interface ClientLinkInput {
  client_id: number;
  relation: string;
}

/** Corpo de `POST /api/events` (feature 152) — sem nenhum campo de arquivo. */
export interface EventCreateInput {
  title: string;
  event_type: string;
  date: string;
  start: string;
  end: string;
  location: string;
  description: string;
  needs_rehearsal: boolean;
  sale_value: number;
  sale_value_gross: number;
  transport_value: number;
  acrescimo_value: number;
  with_invoice: boolean;
  is_cortesia_permuta: boolean;
  seller_id: number | null;
  sale_date: string | null;
  payment_method: string | null;
  payment_installments: number | null;
  payment_due_date: string | null;
  orcamento_history_id: number | null;
  duracao: string;
  characters: CharacterInput[];
  orc_caches: OrcamentoCache[];
  acrescimos: unknown[];
  coordinator_talent_id: number | null;
  clients: ClientLinkInput[];
  form_response_id: number | null;
  has_reembolso: boolean;
  reembolso_description: string;
  reembolso_amount: number;
  observations: ObservationInput[];
}

export interface EventCreateResult extends EventoDetalhe {
  warnings: string[];
}

/** Cria um evento novo (feature 152). RBAC no servidor: `_CAN_CREATE` (Comercial/Superadmin). */
export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation<EventCreateResult, Error, EventCreateInput>({
    mutationFn: (body) =>
      apiFetch<EventCreateResult>("/api/events", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
    },
  });
}
