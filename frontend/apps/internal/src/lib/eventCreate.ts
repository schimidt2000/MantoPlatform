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
  /** Presente ao carregar um evento existente para edição (feature 184); `null` para uma linha
   * nova. Usado pelo backend para reconciliar o elenco por identidade em vez de substituir tudo. */
  role_id?: number | null;
  name: string;
  figurino_sheet_id: number | null;
  cache_value: number | null;
  needs_makeup: boolean;
  is_singer: boolean;
  talent_id: number | null;
}

export interface ObservationInput {
  obs_type: "text" | "link" | "image";
  content: string;
  label: string;
  /** Só para `obs_type === "image"` (feature 184) — enviado na fase 2, via
   * `POST /events/<id>/observations` multipart. */
  file?: File | null;
}

export interface ClientLinkInput {
  client_id: number;
  relation: string;
}

/** Comprovante de pagamento pendente de envio (feature 184) — vive só no estado local do
 * formulário até o evento existir; então é enviado via `POST /events/<id>/payments`. */
export interface PendingPaymentProof {
  file: File;
  amount: number;
}

/** Corpo de `POST /api/events` (feature 152) — sem nenhum campo de arquivo. O reembolso (feature
 * 184) deixou de ser enviado aqui — vira uma chamada separada em
 * `POST /events/<id>/reimbursements` depois que o evento existe (ver `EventCreatePage.tsx`,
 * fase 2 de anexos). Observações do tipo "image" também não entram aqui — só texto/link. */
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
  observations: Array<Omit<ObservationInput, "obs_type" | "file"> & { obs_type: "text" | "link" }>;
}

/** Corpo de `PATCH /api/events/<id>` (feature 184) — atualização em bloco dos campos centrais.
 * Anexos (comprovantes/contrato/reembolso/observação com foto) NÃO passam por aqui — usam os
 * endpoints já existentes de `lib/eventAttachments.ts`, igual à tela de detalhe. */
export interface EventUpdateInput {
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
  coordinator_talent_id: number | null;
  form_response_id: number | null;
  characters: CharacterInput[];
  clients: ClientLinkInput[];
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

/** Atualiza os campos centrais de um evento existente (feature 184). RBAC no servidor: mesmo
 * nível de criação (Comercial/Superadmin) — o payload cobre os mesmos campos financeiros. */
export function useUpdateEvent(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, EventUpdateInput>({
    mutationFn: (body) =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
    },
  });
}
