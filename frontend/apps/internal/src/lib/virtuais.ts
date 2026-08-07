import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, type ApiRequestError } from "@manto/api-client";

/**
 * Loja de Interações Virtuais (feature 205) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/virtuais/*`: as telas de gestão consomem daqui, nenhuma
 * monta `fetch` por conta própria (Princípio I).
 *
 * **Dinheiro**: a API trafega reais em string decimal (`"150.00"`), nunca centavos. Converter para
 * número é sempre `parseBRL`/`Number`, e exibir é sempre `formatBRL` do `@manto/money` — nenhuma
 * máscara própria em tela nenhuma (Princípio IX).
 */

/** Estados de uma campanha. Só `publicada` aceita reservas novas. */
export type VirtualCampaignStatus = "rascunho" | "publicada" | "pausada";

export const VIRTUAL_CAMPAIGN_STATUS_LABELS: Record<VirtualCampaignStatus, string> = {
  rascunho: "Rascunho",
  publicada: "Publicada",
  pausada: "Pausada",
};

/** Tom do `Badge` de cada status — paleta do design system, zero cor hardcoded. */
export const VIRTUAL_CAMPAIGN_STATUS_TONES: Record<
  VirtualCampaignStatus,
  "neutral" | "green" | "gold"
> = {
  rascunho: "neutral",
  publicada: "green",
  pausada: "gold",
};

/** Personagem do catálogo vinculado à campanha (subset para a miniatura quadrada). */
export interface VirtualCampaignCharacter {
  name: string;
  /** Foto do personagem; passar por `assetUrl()` antes de exibir. */
  photo_url: string | null;
}

/** Item do FAQ exibido no fim da landing. */
export interface VirtualFaqItem {
  pergunta: string;
  resposta: string;
}

/** Peça do Acervo 3D liberada para oferta na campanha. */
export interface VirtualGiftItem {
  id: number;
  name: string;
  /** Foto de preview; passar por `assetUrl()` antes de exibir. */
  photo_url: string | null;
}

/** Campanha como o admin a vê — inclui configuração e números de venda. */
export interface VirtualCampaign {
  id: number;
  slug: string;
  status: VirtualCampaignStatus;
  title: string;
  character: VirtualCampaignCharacter | null;
  cover_url: string | null;
  intro_html: string | null;
  tolerance_terms: string | null;
  faq: VirtualFaqItem[];
  whatsapp_phone: string | null;
  /** Reais em string decimal (ex.: `"150.00"`) — nunca centavos. */
  price_live: string | null;
  price_recorded: string | null;
  price_gift: string | null;
  recorded_available: number;
  recorded_capacity: number;
  recorded_sold: number;
  recorded_delivery_days: number;
  catalog_character_id: number;
  talent_id: number | null;
  figurino_sheet_id: number | null;
  max_reservations_per_origin: number;
  reservation_window_minutes: number;
  gift_items: VirtualGiftItem[];
  /** Acervo 3D ativo inteiro — as opções do seletor de peças liberadas. */
  available_gift_items: VirtualGiftItem[];
  acervo_item_ids: number[];
  created_at: string | null;
  /** Métricas de acompanhamento (FR-009). */
  sold_count: number;
  revenue: string | null;
  slots_total: number;
  slots_available: number;
  recorded_used: number;
  recorded_capacity_total: number;
}

/** Horário de 10 minutos do estoque da campanha. */
export interface VirtualSlot {
  id: number;
  start_at: string;
  status: "livre" | "travado" | "vendido";
  locked_until: string | null;
}

export interface VirtualCampaignDetail extends VirtualCampaign {
  slots: VirtualSlot[];
}

interface VirtualCampaignsResponse {
  campaigns: VirtualCampaign[];
}

/** Resultado da geração de horários: `skipped` são os que já existiam (FR-004 é idempotente). */
export interface GerarSlotsResult {
  created: number;
  skipped: number;
}

const CAMPAIGNS_KEY = ["virtuais", "campanhas"] as const;

const campaignKey = (id: number) => ["virtuais", "campanha", id] as const;

/** Converte o valor decimal da API em número para o `MoneyInput`. */
export function apiMoneyToNumber(value: string | null): number {
  if (!value) return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * Converte o número do `MoneyInput` de volta para o formato decimal da API (`"150.00"`).
 *
 * O `toFixed` aqui é **serialização de transporte**, não formatação de tela: quem exibe dinheiro
 * ao usuário é sempre `formatBRL` de `@manto/money` (Princípio IX). Mesma convenção de
 * `lib/financeiro.ts`.
 */
export function numberToApiMoney(value: number): string {
  return value.toFixed(2);
}

export function useVirtualCampaigns() {
  return useQuery<VirtualCampaignsResponse>({
    queryKey: CAMPAIGNS_KEY,
    queryFn: () => apiFetch<VirtualCampaignsResponse>("/api/virtuais/campanhas"),
  });
}

export function useVirtualCampaign(id: number | null) {
  return useQuery<VirtualCampaignDetail>({
    queryKey: campaignKey(id ?? 0),
    queryFn: () => apiFetch<VirtualCampaignDetail>(`/api/virtuais/campanhas/${id}/admin`),
    enabled: id !== null,
  });
}

/** Campos aceitos na criação/edição — dinheiro sempre em string decimal de reais. */
export interface VirtualCampaignInput {
  catalog_character_id?: number;
  title?: string;
  price_live?: string;
  price_recorded?: string;
  price_gift?: string;
  recorded_capacity?: number;
  recorded_delivery_days?: number;
  intro_html?: string;
  tolerance_terms?: string;
  faq?: VirtualFaqItem[];
  whatsapp_phone?: string;
  talent_id?: number | null;
  figurino_sheet_id?: number | null;
  max_reservations_per_origin?: number;
  reservation_window_minutes?: number;
  /**
   * Foto de capa. Quando presente, a requisição vira `multipart` — o servidor lê o arquivo do
   * campo `cover`. É **obrigatória para publicar**: sem ela a campanha não sai do rascunho.
   */
  cover?: File;
}

/**
 * Monta o corpo da requisição: `FormData` quando há capa, JSON quando não há.
 *
 * O backend sempre aceitou os dois (`_payload` em `app/api/virtuais_write.py`), mas a tela só
 * mandava JSON — e por isso `cover_url` nunca era preenchido e nenhuma campanha conseguia ser
 * publicada. Objetos (o FAQ) viajam serializados, que é como o `_payload` os lê do form.
 */
function campaignBody(input: VirtualCampaignInput): FormData | string {
  if (!input.cover) return JSON.stringify(input);

  const form = new FormData();
  Object.entries(input).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (value instanceof File) {
      form.set(key, value);
    } else if (typeof value === "object") {
      form.set(key, JSON.stringify(value));
    } else {
      form.set(key, String(value));
    }
  });
  return form;
}

function useInvalidateCampaigns() {
  const queryClient = useQueryClient();
  return (id?: number) => {
    void queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
    if (id !== undefined) {
      void queryClient.invalidateQueries({ queryKey: campaignKey(id) });
    }
  };
}

export function useCreateVirtualCampaign() {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (input: VirtualCampaignInput) =>
      apiFetch<VirtualCampaign>("/api/virtuais/campanhas", {
        method: "POST",
        body: campaignBody(input),
      }),
    onSuccess: () => invalidate(),
  });
}

export function useUpdateVirtualCampaign(id: number) {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (input: VirtualCampaignInput) =>
      apiFetch<VirtualCampaign>(`/api/virtuais/campanhas/${id}`, {
        method: "PATCH",
        body: campaignBody(input),
      }),
    onSuccess: () => invalidate(id),
  });
}

/** Publica, pausa ou devolve a campanha para rascunho (FR-007). */
export function useSetVirtualCampaignStatus(id: number) {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (status: VirtualCampaignStatus) =>
      apiFetch<VirtualCampaign>(`/api/virtuais/campanhas/${id}/publicar`, {
        method: "POST",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => invalidate(id),
  });
}

/** Define as peças do Acervo 3D liberadas para a campanha (FR-006). */
export function useSetVirtualCampaignAcervo(id: number) {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (itemIds: number[]) =>
      apiFetch<VirtualCampaign>(`/api/virtuais/campanhas/${id}/acervo`, {
        method: "PUT",
        body: JSON.stringify({ item_ids: itemIds }),
      }),
    onSuccess: () => invalidate(id),
  });
}

export interface GerarSlotsInput {
  date: string;
  start: string;
  end: string;
}

export function useGerarSlots(id: number) {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (input: GerarSlotsInput) =>
      apiFetch<GerarSlotsResult>(`/api/virtuais/campanhas/${id}/horarios`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidate(id),
  });
}

/** Os três únicos estados de produção (FR-048a). Enviar o vídeo é ação, não estado. */
export type ProducaoStatus = "pendente" | "gravando" | "finalizado";

export const PRODUCAO_STATUSES: ProducaoStatus[] = ["pendente", "gravando", "finalizado"];

export const PRODUCAO_STATUS_LABELS: Record<ProducaoStatus, string> = {
  pendente: "Pendente",
  gravando: "Gravando",
  finalizado: "Finalizado",
};

export const PRODUCAO_STATUS_TONES: Record<ProducaoStatus, "neutral" | "gold" | "green"> = {
  pendente: "neutral",
  gravando: "gold",
  finalizado: "green",
};

/** Uma linha da Fila de Produção de Mídia — os quatro blocos na mesma altura (FR-046). */
export interface VirtualDelivery {
  id: number;
  /** Id do **pedido** — é ele que as ações de reenvio e de sala endereçam, não o da entrega. */
  order_id: number;
  order_token: string;
  order_nsu: string;
  modality: "ao_vivo" | "gravado";
  start_at: string | null;
  due_date: string | null;
  prazo_vencido: boolean;
  prazo_proximo: boolean;
  status: ProducaoStatus;
  child_name: string;
  child_age: number;
  behavior_notes: string | null;
  campaign_title: string | null;
  meet_url: string | null;
  meet_pending: boolean;
  /** Presente 3D, no mesmo formato da Fila de Impressão (fonte única). */
  gift: {
    status: string;
    item: { name: string; photo_url: string | null } | null;
  } | null;
  has_video: boolean;
  last_upload_error: string | null;
  whatsapp_url: string | null;
  /** Avisos automáticos que **não** chegaram à família (FR-039c). Só os falhados. */
  avisos_falhos: AvisoFalho[];
  /** A sala parou de ser retentada — precisa de ação humana agora (FR-056a). */
  meet_retry_esgotado: boolean;
  meet_attempts: number;
}

/** Um aviso automático que falhou, com o progresso da política de retry (FR-039c, FR-056a). */
export interface AvisoFalho {
  kind: string;
  /** Rótulo em pt-BR — o `kind` cru nunca vai para a tela. */
  label: string;
  error_message: string | null;
  attempts: number;
  /** `true` = as 3 tentativas acabaram; o sistema desistiu e ninguém mais vai tentar sozinho. */
  esgotado: boolean;
  last_attempt_at: string | null;
}

const PRODUCAO_KEY = ["virtuais", "producao"] as const;

export interface FilaFiltros {
  campaign_id?: number | null;
  date?: string | null;
  status?: ProducaoStatus | null;
}

export function useFilaProducao(filtros: FilaFiltros) {
  const params = new URLSearchParams();
  if (filtros.campaign_id) params.set("campaign_id", String(filtros.campaign_id));
  if (filtros.date) params.set("date", filtros.date);
  if (filtros.status) params.set("status", filtros.status);
  const qs = params.toString();

  return useQuery<{ deliveries: VirtualDelivery[] }>({
    queryKey: [...PRODUCAO_KEY, qs],
    queryFn: () => apiFetch<{ deliveries: VirtualDelivery[] }>(`/api/virtuais/producao?${qs}`),
    // Filtro não recarrega a página: a query key muda e o TanStack mantém a lista anterior
    // visível enquanto busca a nova (FR-050).
    placeholderData: (anterior) => anterior,
  });
}

export function useAtualizarStatusEntrega() {
  const queryClient = useQueryClient();
  return useMutation<VirtualDelivery, ApiRequestError, { id: number; status: ProducaoStatus }>({
    mutationFn: ({ id, status }) =>
      apiFetch<VirtualDelivery>(`/api/virtuais/producao/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCAO_KEY });
    },
  });
}

/** Envia o vídeo finalizado. É a ação que permite a entrega chegar a `finalizado` (FR-048). */
export function useEnviarVideo() {
  const queryClient = useQueryClient();
  return useMutation<VirtualDelivery, ApiRequestError, { id: number; file: File }>({
    mutationFn: ({ id, file }) => {
      const form = new FormData();
      form.append("video", file);
      return apiFetch<VirtualDelivery>(`/api/virtuais/producao/${id}/video`, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCAO_KEY });
    },
  });
}

/**
 * Reenvia um aviso que falhou, por decisão da equipe (FR-039c).
 *
 * Só reentrega o que já falhou — nunca cria aviso novo. Invalida a fila **e** o evento aberto,
 * porque a mesma falha aparece nos dois lugares e vê-la sumir de um só seria pior que não sumir.
 */
export function useReenviarAviso() {
  const queryClient = useQueryClient();
  return useMutation<
    { kind: string; sent_ok: boolean; attempts: number },
    ApiRequestError,
    { orderId: number; kind: string }
  >({
    mutationFn: ({ orderId, kind }) =>
      apiFetch<{ kind: string; sent_ok: boolean; attempts: number }>(
        `/api/virtuais/pedidos/${orderId}/avisos/${kind}/reenviar`,
        { method: "POST" },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCAO_KEY });
      void queryClient.invalidateQueries({ queryKey: ["event"] });
    },
  });
}

/** Tenta de novo a sala do Meet que ficou pendente (FR-037). */
export function useRegerarSala() {
  const queryClient = useQueryClient();
  return useMutation<
    { meet_url: string | null; meet_pending: boolean; meet_retry_esgotado: boolean },
    ApiRequestError,
    { orderId: number }
  >({
    mutationFn: ({ orderId }) =>
      apiFetch<{ meet_url: string | null; meet_pending: boolean; meet_retry_esgotado: boolean }>(
        `/api/virtuais/pedidos/${orderId}/sala`,
        { method: "POST" },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRODUCAO_KEY });
      void queryClient.invalidateQueries({ queryKey: ["event"] });
    },
  });
}

/** Devolução aberta quando um pagamento cai em horário indisponível (FR-042/FR-043). */
export interface VirtualRefund {
  id: number;
  status: "pendente" | "concluida";
  /** Reais em string decimal. */
  amount: string | null;
  reason: string;
  /** Frase em pt-BR da origem do conflito — o `reason` cru é chave de sistema (FR-018b). */
  reason_label: string;
  /** O horário foi liberado sem confirmação da operadora: a família pode ter pago no prazo. */
  sem_confirmacao: boolean;
  invoice_slug: string | null;
  transaction_nsu: string | null;
  created_at: string | null;
  resolved_at: string | null;
  order: {
    order_nsu: string;
    child_name: string;
    contact_phone_display: string | null;
    contact_email: string;
    campaign_title: string | null;
  } | null;
}

const REFUNDS_KEY = ["virtuais", "devolucoes"] as const;

export function useVirtualRefunds(status: "pendente" | "concluida" = "pendente") {
  return useQuery<{ refunds: VirtualRefund[] }>({
    queryKey: [...REFUNDS_KEY, status],
    queryFn: () =>
      apiFetch<{ refunds: VirtualRefund[] }>(`/api/virtuais/devolucoes?status=${status}`),
  });
}

/** Marca a devolução como concluída **depois** de executá-la no painel da operadora. */
export function useConcluirDevolucao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<VirtualRefund>(`/api/virtuais/devolucoes/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "concluida" }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: REFUNDS_KEY });
    },
  });
}

export function useRemoverSlot(campaignId: number) {
  const invalidate = useInvalidateCampaigns();
  return useMutation({
    mutationFn: (slotId: number) =>
      apiFetch<{ deleted: boolean }>(`/api/virtuais/horarios/${slotId}`, { method: "DELETE" }),
    onSuccess: () => invalidate(campaignId),
  });
}
