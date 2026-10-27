import { useEffect, useState } from "react";
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

/** Card da vitrine — o que a home da loja mostra de cada campanha publicada. */
export interface VirtualVitrineItem {
  slug: string;
  title: string;
  character_name: string | null;
  cover_url: string | null;
  price_live: string | null;
  price_recorded: string | null;
  /** Ainda há horário livre para chamada ao vivo. */
  tem_horario: boolean;
  /** Ainda há vídeo gravado no estoque. */
  tem_gravado: boolean;
}

/** Campanhas publicadas — a home de `alo.mantoproducoes.com.br` (feature 224e). */
export function useVitrineVirtual() {
  return useQuery<{ campanhas: VirtualVitrineItem[] }>({
    queryKey: ["virtuais-vitrine"],
    queryFn: () => apiFetch<{ campanhas: VirtualVitrineItem[] }>("/api/virtuais/vitrine"),
  });
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
  /** Segundos até a trava vencer, calculados no servidor (feature 310): independe do fuso. */
  seconds_left: number | null;
  /** Um aviso de pagamento deste pedido está sendo decidido (feature 310). */
  confirming: boolean;
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
  seconds_left: number | null;
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
    // Feature 310: também em "reservado" — o link pode ainda estar sendo gerado, e a página
    // ficava parada sem botão de pagar até a família recarregar.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "aguardando" || status === "reservado" ? 5000 : false;
    },
    // **Continua consultando com a aba em segundo plano.** É o caso normal, não a exceção: a
    // família clica em "Ir para o pagamento", vai para a aba da operadora e deixa esta aqui
    // atrás. Sem isso, ela voltaria para uma página congelada em "aguardando".
    refetchIntervalInBackground: true,
    // E, ao voltar para a aba, atualiza na hora — o padrão global do app é `false`, que aqui
    // deixaria a família olhando para um estado velho.
    refetchOnWindowFocus: true,
  });
}

/** Identificadores que a InfinitePay põe na URL de retorno do checkout (feature 310, R3). */
export interface RetornoCheckout {
  order_nsu: string;
  slug?: string | null;
  transaction_nsu?: string | null;
  capture_method?: string | null;
  receipt_url?: string | null;
}

/**
 * Manda ao servidor os identificadores do retorno do checkout (feature 310, R3).
 *
 * É a segunda prova de pagamento além do aviso: sem eles a operadora não distingue "não pago" de
 * "não achei". Quem decide continua sendo a reconsulta no servidor.
 */
export function useRetornoCheckout(token: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation<VirtualOrderSummary, ApiRequestError, RetornoCheckout>({
    mutationFn: (dados) =>
      apiFetch<VirtualOrderSummary>(`/api/virtuais/pedidos/${token}/retorno`, {
        method: "POST",
        body: JSON.stringify(dados),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["virtuais", "pedido", token], data);
    },
  });
}

/**
 * Desiste de uma reserva ainda não paga (FR-020a da 205; feature 310, FR-036).
 *
 * A regra "uma reserva ativa por telefone" mandava abandonar a reserva antiga para escolher outro
 * horário ou reservar para o irmão — sem este botão, a família ficava presa até a trava vencer.
 * Com sinal de pagamento o servidor recusa (409): quem decide é a operadora.
 */
export function useAbandonarReserva() {
  return useMutation<
    VirtualOrderSummary,
    ApiRequestError,
    { token: string; clientToken: string }
  >({
    mutationFn: ({ token, clientToken }) =>
      apiFetch<VirtualOrderSummary>(`/api/virtuais/pedidos/${token}/abandonar`, {
        method: "POST",
        body: JSON.stringify({ client_token: clientToken }),
      }),
  });
}

const CHAVE_RESERVAS_DA_ABA = "manto_virtuais_reservas_da_aba";

/**
 * Guarda qual `client_token` criou cada reserva desta aba. É a prova que o servidor pede para
 * abandonar (o link do pedido sozinho não basta) — e o token da aba é renovado a cada reserva.
 */
export function lembrarReservaDaAba(publicToken: string, clientToken: string): void {
  try {
    const mapa = JSON.parse(window.sessionStorage.getItem(CHAVE_RESERVAS_DA_ABA) || "{}");
    mapa[publicToken] = clientToken;
    window.sessionStorage.setItem(CHAVE_RESERVAS_DA_ABA, JSON.stringify(mapa));
  } catch {
    /* sem sessionStorage: a família só não terá o botão de abandonar nesta aba */
  }
}

/** O `client_token` que criou a reserva nesta aba, ou `null` (outra aba, outro aparelho). */
export function tokenDaAbaPara(publicToken: string): string | null {
  try {
    const mapa = JSON.parse(window.sessionStorage.getItem(CHAVE_RESERVAS_DA_ABA) || "{}");
    return typeof mapa[publicToken] === "string" ? mapa[publicToken] : null;
  } catch {
    return null;
  }
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
/**
 * Descarta o token da aba depois de uma reserva criada (feature 310, FR-036): a próxima reserva
 * na mesma aba (outro horário, o irmão) nasce como pedido novo.
 */
export function renovarClientToken(): void {
  try {
    window.sessionStorage.removeItem("manto_virtuais_client_token");
  } catch {
    /* sessionStorage indisponível: o servidor já confere horário, formato, presente e criança */
  }
}

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

/**
 * Contagem regressiva a partir dos segundos que o SERVIDOR calculou (feature 310, FR-035).
 *
 * `locked_until` é hora de parede de São Paulo sem fuso: `new Date()` o lia no fuso do aparelho,
 * e uma família em Manaus via 75:00 no lugar de 15:00. O servidor manda quanto falta; aqui só se
 * desconta o tempo passado desde que a resposta chegou.
 */
export function useContagemDeSegundos(segundos: number | null | undefined): string | null {
  const [restante, setRestante] = useState<string | null>(null);
  useEffect(() => {
    if (segundos === null || segundos === undefined) {
      setRestante(null);
      return;
    }
    const alvo = Date.now() + segundos * 1000;
    const tick = () => {
      const s = Math.max(0, Math.floor((alvo - Date.now()) / 1000));
      setRestante(`${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`);
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [segundos]);
  return restante;
}
