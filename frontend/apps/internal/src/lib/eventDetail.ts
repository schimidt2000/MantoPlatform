import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe, EventMensagens, PaymentStatus, RoleItem } from "./agenda";

/**
 * Mutações e utilitários da tela de detalhe do evento (feature 190).
 *
 * Toda mutação devolve o `EventoDetalhe` já atualizado pelo servidor e o grava no cache do
 * TanStack Query — mesmo padrão de `casting.ts`/`eventAttachments.ts`, para a tela
 * re-renderizar sem refetch e sem lógica de merge no cliente.
 */

/** Escreve o evento devolvido pelo servidor no cache, atualizando a tela inteira. */
function useEventMutation<TInput>(
  eventId: number,
  request: (input: TInput) => Promise<EventoDetalhe>,
) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, TInput>({
    mutationFn: request,
    onSuccess: (updated) => queryClient.setQueryData(["event", eventId], updated),
  });
}

/** Grava o status de pagamento do cachê de um cargo. */
export function useSetPaymentStatus(eventId: number) {
  return useEventMutation<{ roleId: number; payment_status: PaymentStatus }>(
    eventId,
    ({ roleId, payment_status }) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}/payment-status`, {
        method: "POST",
        body: JSON.stringify({ payment_status }),
      }),
  );
}

/** Vincula (ou desvincula, com `sheetId: null`) a ficha de figurino de um cargo. */
export function useLinkFigurinoSheet(eventId: number) {
  return useEventMutation<{ roleId: number; sheetId: number | null }>(
    eventId,
    ({ roleId, sheetId }) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}/figurino-sheet`, {
        method: "POST",
        body: JSON.stringify({ sheet_id: sheetId }),
      }),
  );
}

/** Liga/desliga "figurino separado" de um cargo (caixa de seleção do card de Figurino). */
export function useToggleFigurinoDone(eventId: number) {
  return useEventMutation<{ roleId: number; done: boolean }>(eventId, ({ roleId, done }) =>
    apiFetch<EventoDetalhe>(`/api/roles/${roleId}/figurino-done`, {
      method: done ? "POST" : "DELETE",
    }),
  );
}

/** Recalcula a estimativa de trajeto pelo Google Maps. */
export function useTravelEstimate(eventId: number) {
  return useEventMutation<void>(eventId, () =>
    apiFetch<EventoDetalhe>(`/api/events/${eventId}/travel-estimate`, { method: "POST" }),
  );
}

/** Anexa um arquivo de material de ensaio (multipart, até 20 MB). */
export function useAddMaterialFile(eventId: number) {
  return useEventMutation<{ file: File; label?: string }>(eventId, ({ file, label }) => {
    const form = new FormData();
    form.append("file", file);
    if (label) form.append("label", label);
    return apiFetch<EventoDetalhe>(`/api/events/${eventId}/materials`, {
      method: "POST",
      body: form,
    });
  });
}

/** Anexa um link de material de ensaio (Drive, YouTube…). */
export function useAddMaterialLink(eventId: number) {
  return useEventMutation<{ url: string; label?: string }>(eventId, (body) =>
    apiFetch<EventoDetalhe>(`/api/events/${eventId}/materials`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  );
}

/** Remove um material de ensaio. */
export function useDeleteMaterial(eventId: number) {
  return useEventMutation<number>(eventId, (materialId) =>
    apiFetch<EventoDetalhe>(`/api/materials/${materialId}`, { method: "DELETE" }),
  );
}

/** Gera (na primeira vez) e devolve o link público de avaliação da cliente. */
export function useFeedbackLink(eventId: number) {
  return useMutation<{ url: string }, Error, void>({
    mutationFn: () =>
      apiFetch<{ url: string }>(`/api/events/${eventId}/feedback-link`, { method: "POST" }),
  });
}

// ── Ensaios: agendamento e presença (restaurado na 206) ─────────────────────────

export interface CreateEnsaioInput {
  date: string;
  start: string;
  end: string;
  description: string;
  location_type: "manto" | "outro";
  location: string;
}

/** Agenda um ensaio para o show — a resposta é o detalhe do próprio show. */
export function useCreateEnsaio(eventId: number) {
  return useEventMutation<CreateEnsaioInput>(eventId, (body) =>
    apiFetch<EventoDetalhe>(`/api/events/${eventId}/ensaios`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  );
}

/** Cancela um ensaio a partir da página do SHOW — a resposta é o detalhe do show. */
export function useDeleteEnsaioFromShow(eventId: number) {
  return useEventMutation<number>(eventId, (ensaioId) =>
    apiFetch<EventoDetalhe>(`/api/ensaios/${ensaioId}`, { method: "DELETE" }),
  );
}

/** Define/limpa o Técnico de Som (Presença) — tarefa da equipe de ensaio. */
export function useAssignPresenca(eventId: number) {
  return useEventMutation<number | null>(eventId, (talentId) =>
    apiFetch<EventoDetalhe>(`/api/events/${eventId}/presenca`, {
      method: "POST",
      body: JSON.stringify({ talent_id: talentId }),
    }),
  );
}

export interface EditEnsaioInput {
  ensaioId: number;
  date: string;
  start: string;
  end: string;
  description: string;
  location: string;
}

/**
 * Edita um ensaio a partir da página do PRÓPRIO ensaio. A resposta do PATCH é o detalhe do
 * show pai — não pode ir para `setQueryData(["event", ensaioId])` (corromperia o cache do
 * ensaio), então aqui invalida-se os prefixos e o servidor responde os refetches.
 */
export function useEditEnsaio() {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, EditEnsaioInput>({
    mutationFn: ({ ensaioId, ...body }) =>
      apiFetch<EventoDetalhe>(`/api/ensaios/${ensaioId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["event"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

/** Exclui um ensaio (inclusive órfão) a partir da página do próprio ensaio. */
export function useDeleteEnsaio() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (ensaioId) => apiFetch<unknown>(`/api/ensaios/${ensaioId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["event"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["agenda"] });
    },
  });
}

/** Vincula um ensaio órfão a um show — a resposta é o detalhe do próprio ensaio. */
export function useVincularEnsaio(ensaioId: number) {
  return useEventMutation<number>(ensaioId, (parentEventId) =>
    apiFetch<EventoDetalhe>(`/api/ensaios/${ensaioId}/vincular`, {
      method: "POST",
      body: JSON.stringify({ parent_event_id: parentEventId }),
    }),
  );
}

// ── Mensagens de WhatsApp ────────────────────────────────────────────────────
// A saudação depende da hora de quem copia, então é montada aqui (o servidor manda só os
// trechos que dependem do evento, em `EventoDetalhe.mensagens`).

/** Saudação por faixa de horário, como no fluxo Jinja de hoje. */
function saudacao(): string {
  const hora = new Date().getHours();
  if (hora >= 5 && hora < 12) return "Bom dia";
  if (hora >= 12 && hora < 18) return "Boa tarde";
  return "Boa noite";
}

/** Mensagem de confirmação do evento com a cliente. */
export function buildConfirmacaoMsg(m: EventMensagens): string {
  return [
    `${saudacao()}! Como vai?`,
    "Passando para confirmar seu evento!",
    "",
    m.characters,
    m.date_line,
    ...(m.location ? [m.location] : []),
    "",
    "Tudo certinho? Estamos ansiosos por esse momento!",
  ].join("\n");
}

/** Mensagem de cobrança do valor em aberto. */
export function buildCobrancaMsg(m: EventMensagens): string {
  const valor = m.cobranca_due
    ? `Consta um valor em aberto de ${m.cobranca_amount} com vencimento em ${m.cobranca_due}.`
    : `Consta um valor em aberto de ${m.cobranca_amount}.`;
  return [
    `${saudacao()}! Tudo bem?`,
    "Passando sobre o pagamento do seu evento:",
    "",
    m.characters,
    m.date_line,
    ...(m.location ? [m.location] : []),
    "",
    valor,
    "Poderia, por gentileza, confirmar o pagamento? Qualquer dúvida estou à disposição!",
  ].join("\n");
}

/** Mensagem de cobrança dos reembolsos pendentes. */
export function buildCobrancaReembolsoMsg(m: EventMensagens): string {
  return [
    `${saudacao()}! Tudo bem?`,
    "Passando sobre os reembolsos pendentes do seu evento:",
    "",
    m.characters,
    m.date_line,
    "",
    ...m.reembolso_lines.map((linha) => `• ${linha}`),
    "",
    "Poderia, por gentileza, providenciar o reembolso? Qualquer dúvida estou à disposição!",
  ].join("\n");
}

/** Mensagem com o link público de avaliação da cliente. */
export function buildFeedbackMsg(url: string): string {
  return [
    "Olá! Como vai?",
    "Obrigado por contar com a Manto para um momento tão mágico e especial!",
    "Se puder, deixe uma avaliação no link abaixo. Seu feedback faz toda a diferença! 💙",
    "",
    `👉 ${url}`,
    "",
    "Até a próxima!",
  ].join("\n");
}

interface ConviteContext {
  title: string;
  dateLabel: string;
  timeLabel: string;
  location: string | null;
  makeupTime: string | null;
  makeupLocation: string | null;
}

/**
 * Endereço público do Portal do Artista (feature 269).
 *
 * É constante de propósito, e NÃO vem de `PORTAL_URL` da API: toda mensagem que usa este
 * endereço é copiada por alguém do staff e enviada por WhatsApp para um talento **de fora**.
 * Quando o valor vinha da env, quem estivesse rodando o ambiente local mandava
 * `http://localhost:5000/` para uma pessoa real — link morto —, e quando a env não estava setada
 * a mensagem saía sem link nenhum. O endereço do portal é fixo e público; deixá-lo depender de
 * configuração de ambiente só criava as duas formas de errar.
 *
 * `PORTAL_URL` continua existindo e é a fonte certa para os e-mails do SERVIDOR (onde um
 * ambiente de teste precisa mesmo apontar para si).
 */
export const PORTAL_PUBLICO = "portal.mantoproducoes.com.br";

/** Mensagem de convite individual de um talento (botão "Copiar convite" do card). */
export function buildConviteMsg(role: RoleItem, ctx: ConviteContext, cache: string): string {
  const linhas = [
    `Ola, ${role.talent?.first_name ?? ""}! Voce tem um convite da Manto Producoes. 🎉`,
    "",
    `🎪 *${ctx.title}*`,
    `👤 Personagem: *${role.character_name}*`,
  ];
  if (ctx.dateLabel) linhas.push(`📅 ${ctx.dateLabel}`);
  if (ctx.timeLabel) linhas.push(`🕐 ${ctx.timeLabel}`);
  if (ctx.location) linhas.push(`📍 ${ctx.location}`);
  if (cache) linhas.push(`💰 Cache: ${cache}`);
  if (ctx.makeupTime) {
    linhas.push("", "💄 *Maquiagem*", `🕐 Horario: ${ctx.makeupTime}`);
    if (ctx.makeupLocation) linhas.push(`📍 Local: ${ctx.makeupLocation}`);
  }
  linhas.push(
    "",
    "Acesse o portal Manto para confirmar sua presença. ✅",
    PORTAL_PUBLICO,
  );
  return linhas.join("\n");
}
