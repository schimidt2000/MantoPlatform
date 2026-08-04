import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiRequestError } from "@manto/api-client";

/**
 * Loja de Interações Virtuais — superfície pública (feature 205, US2).
 *
 * Fonte única do contrato de `/api/virtuais/*` para o app público. A campanha, os horários e a
 * reserva vêm daqui; nenhuma tela monta `fetch` por conta própria (Princípio I).
 *
 * **Dinheiro** chega em reais decimais (`"150.00"`), nunca em centavos; exibir é sempre `formatBRL`
 * do `@manto/money` (Princípio IX).
 */

export type VirtualModality = "ao_vivo" | "gravado";

export interface VirtualGiftItem {
  id: number;
  name: string;
  photo_url: string | null;
}

export interface VirtualFaqItem {
  pergunta: string;
  resposta: string;
}

export interface VirtualCampaignPublic {
  slug: string;
  title: string;
  character: { name: string; photo_url: string | null } | null;
  cover_url: string | null;
  intro_html: string | null;
  tolerance_terms: string | null;
  faq: VirtualFaqItem[];
  whatsapp_phone: string | null;
  price_live: string | null;
  price_recorded: string | null;
  price_gift: string | null;
  recorded_available: number;
  recorded_delivery_days: number;
  gift_items: VirtualGiftItem[];
}

export interface VirtualSlotPublic {
  id: number;
  start_at: string;
}

export interface VirtualOrderSummary {
  status: "reservado" | "aguardando" | "pago" | "expirado" | "cancelado";
  modality: VirtualModality;
  start_at: string | null;
  total_value: string | null;
  locked_until: string | null;
  payment_url: string | null;
  requires_verification: boolean;
  phone_hint: string | null;
  /** Sala da chamada — só vem com o pedido pago. */
  meet_url: string | null;
  /** True quando a sala ainda não materializou do lado do Google (FR-037). */
  meet_pending: boolean;
  campaign: {
    slug: string;
    title: string;
    whatsapp_phone: string | null;
    recorded_delivery_days: number;
  } | null;
}

/** Corpo enviado ao reservar. Dinheiro não vai aqui — o servidor congela os valores. */
export interface ReservaInput {
  modality: VirtualModality;
  slot_id?: number | null;
  gift_item_id?: number | null;
  client_token: string;
  child_name: string;
  child_age: number;
  behavior_notes?: string;
  contact_phone: string;
  contact_email: string;
  delivery_address?: string;
}

export interface ReservaResponse {
  public_token: string;
  order_nsu: string;
  locked_until: string | null;
  total_value: string | null;
  payment_url: string | null;
}

export function useCampanhaVirtual(slug: string | undefined) {
  return useQuery<VirtualCampaignPublic>({
    queryKey: ["virtuais", "campanha", slug],
    queryFn: () => apiFetch<VirtualCampaignPublic>(`/api/virtuais/campanhas/${slug}`),
    enabled: Boolean(slug),
    retry: false,
  });
}

export function useHorariosVirtuais(slug: string | undefined, enabled: boolean) {
  return useQuery<{ slots: VirtualSlotPublic[] }>({
    queryKey: ["virtuais", "horarios", slug],
    queryFn: () => apiFetch<{ slots: VirtualSlotPublic[] }>(
      `/api/virtuais/campanhas/${slug}/horarios`,
    ),
    enabled: Boolean(slug) && enabled,
    // Horário é estoque disputado: revalidar ao voltar para a aba evita a família tentar
    // reservar algo que já foi.
    refetchOnWindowFocus: true,
    staleTime: 15 * 1000,
  });
}

export function useReservar(slug: string | undefined) {
  return useMutation<ReservaResponse, ApiRequestError, ReservaInput>({
    mutationFn: (input) =>
      apiFetch<ReservaResponse>(`/api/virtuais/campanhas/${slug}/reservar`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export function usePedidoVirtual(token: string | undefined) {
  return useQuery<VirtualOrderSummary>({
    queryKey: ["virtuais", "pedido", token],
    queryFn: () => apiFetch<VirtualOrderSummary>(`/api/virtuais/pedidos/${token}`),
    enabled: Boolean(token),
    retry: false,
    // O padrão global do app é `staleTime: 30s` — aqui não serve: esta página existe justamente
    // para refletir uma mudança que vem de fora (o aviso da operadora).
    staleTime: 0,
    // Enquanto o pagamento não confirma, a página se atualiza sozinha (FR-035a): a família não
    // precisa saber o que é "pagamento assíncrono" nem recarregar na mão.
    refetchInterval: (query) => (query.state.data?.status === "aguardando" ? 5000 : false),
    // **Continua consultando com a aba em segundo plano.** É o caso normal, não a exceção: a
    // família clica em "Ir para o pagamento", vai para a aba da operadora e deixa esta aqui
    // atrás. Sem isso, ela voltaria para uma página congelada em "aguardando".
    refetchIntervalInBackground: true,
    // E, ao voltar para a aba, atualiza na hora — o padrão global do app é `false`, que aqui
    // deixaria a família olhando para um estado velho.
    refetchOnWindowFocus: true,
  });
}

/** Pedido completo — só chega depois da validação dupla (FR-044a). */
export interface VirtualOrderFull extends VirtualOrderSummary {
  verified: true;
  child_name: string;
  child_age: number;
  behavior_notes: string | null;
  delivery_address: string | null;
  gift: { name: string; photo_url: string | null } | null;
  /** Endereço do endpoint que serve o vídeo — nunca o caminho do arquivo (FR-038e). */
  video_url: string | null;
  recorded_due_date: string | null;
}

/** Valida o telefone da compra e abre a sessão de acesso (FR-044a–044c). */
export function useVerificarPedido(token: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation<VirtualOrderFull, ApiRequestError, string>({
    mutationFn: (phone) =>
      apiFetch<VirtualOrderFull>(`/api/virtuais/pedidos/${token}/verificar`, {
        method: "POST",
        body: JSON.stringify({ phone }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["virtuais", "pedido-completo", token], data);
    },
  });
}

/**
 * Dados completos do pedido, quando a sessão de acesso já está aberta.
 *
 * `enabled` só liga depois da validação: consultar antes devolveria 401 e sujaria a tela com um
 * erro que não é erro — é simplesmente a proteção funcionando.
 */
export function usePedidoCompleto(token: string | undefined, enabled: boolean) {
  return useQuery<VirtualOrderFull>({
    queryKey: ["virtuais", "pedido-completo", token],
    queryFn: () => apiFetch<VirtualOrderFull>(`/api/virtuais/pedidos/${token}/completo`),
    enabled: Boolean(token) && enabled,
    retry: false,
    staleTime: 0,
  });
}

/**
 * Token estável do navegador — é o que faz o duplo clique devolver o mesmo pedido (FR-026).
 *
 * Guardado em `sessionStorage` de propósito: some quando a aba fecha, então uma compra futura da
 * mesma família nasce limpa, sem herdar a reserva antiga.
 */
export function getClientToken(): string {
  const CHAVE = "manto_virtuais_client_token";
  const existente = window.sessionStorage.getItem(CHAVE);
  if (existente) return existente;
  const novo =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  window.sessionStorage.setItem(CHAVE, novo);
  return novo;
}

/** Converte o valor decimal da API em número, para o `formatBRL`. */
export function apiMoneyToNumber(value: string | null): number {
  if (!value) return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** Mapa campo→mensagem do envelope de erro, para destacar o campo culpado (Princípio V). */
export function fieldErrorsFrom(error: unknown): Record<string, string> {
  if (error instanceof ApiRequestError && error.fields) {
    return error.fields as Record<string, string>;
  }
  return {};
}
