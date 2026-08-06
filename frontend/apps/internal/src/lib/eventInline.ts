import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

/**
 * Edição pontual por bloco da tela de detalhe (feature 215).
 *
 * A tela de abas edita cada dado onde ele é exibido — o formulário grande
 * (`useUpdateEvent`, feature 184) continua existindo para a edição em bloco, mas deixou de ser
 * o único caminho. Cada hook aqui bate num endpoint estreito que grava só o seu recorte:
 * salvar o cabeçalho não mexe no elenco, salvar os valores não mexe nos clientes.
 *
 * Todos devolvem o evento inteiro atualizado e o gravam no cache — a tela re-renderiza sem
 * refetch (mesmo padrão de `lib/casting.ts` e `lib/eventOps.ts`).
 */

/** Escreve a resposta no cache do evento e revalida a agenda quando o cabeçalho muda. */
function useEventPatch<TBody>(
  eventId: number,
  path: string,
  method: "PATCH" | "PUT",
  { touchesAgenda = false }: { touchesAgenda?: boolean } = {},
) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, TBody>({
    mutationFn: (body) =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}${path}`, {
        method,
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
      if (touchesAgenda) {
        queryClient.invalidateQueries({ queryKey: ["agenda"] });
        queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
        // A disponibilidade dos talentos é calculada contra a janela do evento: mudou a
        // data/hora, a lista de "ocupados" da busca de casting mudou junto.
        queryClient.invalidateQueries({ queryKey: ["casting-options", eventId] });
      }
    },
  });
}

export interface EventBasicsInput {
  title: string;
  event_type: string;
  /** "AAAA-MM-DD" recortado da ISO, nunca via `Date` (ver `lib/horaLocal.ts`). */
  date: string;
  /** "HH:MM" de parede. */
  start: string;
  end: string;
  location: string;
  description: string;
}

/**
 * Título, tipo, data/horário, local e descrição — cabeçalho da aba Resumo.
 * RBAC no servidor: Comercial/Superadmin (`flags.can_edit_core`).
 */
export function useUpdateEventBasics(eventId: number) {
  return useEventPatch<EventBasicsInput>(eventId, "/basico", "PATCH", { touchesAgenda: true });
}

export interface EventComercialInput {
  sale_value: number | null;
  sale_value_gross: number | null;
  transport_value: number | null;
  with_invoice: boolean;
  is_cortesia_permuta: boolean;
  seller_id: number | null;
  sale_date: string | null;
  commission_rate: number | null;
  payment_method: string | null;
  payment_installments: number | null;
  payment_due_date: string | null;
}

/**
 * Valores da venda, forma de pagamento, vendedor e comissão — aba Comercial.
 * RBAC no servidor: Comercial/Superadmin (`flags.can_edit_core`).
 */
export function useUpdateEventComercial(eventId: number) {
  return useEventPatch<EventComercialInput>(eventId, "/comercial", "PATCH");
}

export interface EventClientsInput {
  clients: { client_id: number; relation: string }[];
}

/**
 * Substitui a lista de clientes do evento (`PUT` — o corpo é a lista inteira, não um delta:
 * mandar `[]` desvincula todos).
 */
export function useSetEventClients(eventId: number) {
  return useEventPatch<EventClientsInput>(eventId, "/clients", "PUT");
}

/** Vincula (`id`) ou desvincula (`null`) o pré-contrato exibido na aba Comercial. */
export function useSetEventFormResponse(eventId: number) {
  return useEventPatch<{ form_response_id: number | null }>(
    eventId,
    "/form-response",
    "PATCH",
  );
}
