import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
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

/** Resposta de um patch pontual — o evento inteiro + `warnings` não-bloqueantes quando o
 * endpoint removeu algo automaticamente (feature 239, decisão 7: troca de tipo saindo de SHOW). */
export type EventPatchResult = EventoDetalhe & { warnings?: string[] };

/** Escreve a resposta no cache do evento e revalida a agenda quando o cabeçalho muda. */
function useEventPatch<TBody>(
  eventId: number,
  path: string,
  method: "PATCH" | "PUT",
  { touchesAgenda = false, invalidar = [] }: { touchesAgenda?: boolean; invalidar?: QueryKey[] } = {},
) {
  const queryClient = useQueryClient();
  return useMutation<EventPatchResult, Error, TBody>({
    mutationFn: (body) =>
      apiFetch<EventPatchResult>(`/api/events/${eventId}${path}`, {
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
      for (const chave of invalidar) queryClient.invalidateQueries({ queryKey: chave });
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

/** Corpo de `PATCH /api/events/<id>/orcamento` (feature 273). */
export interface SetOrcamentoBody {
  orcamento_history_id: number | null;
  /** Aplica fora de SP + equipe vendida (padrão do servidor: true). Idempotente. */
  aplicar_equipe?: boolean;
  /** 1..4 (tabela) — só faz efeito em evento SEM venda (cortesia/permuta conta como venda). */
  aplicar_valores_duracao?: number | null;
  sale_date?: string | null;
}

/**
 * Vincula/desvincula o orçamento e aplica o que foi vendido (feature 273). A resposta é o evento
 * inteiro mais `relatorio_orcamento` (o que foi criado/marcado), e o cache do evento é atualizado
 * como em qualquer outro PATCH estreito.
 */
export function useSetEventOrcamento(eventId: number) {
  // Fora de SP e papéis novos mudam a agenda; "Ver evento" muda a linha do histórico.
  return useEventPatch<SetOrcamentoBody>(eventId, "/orcamento", "PATCH", {
    touchesAgenda: true,
    invalidar: [["orcamento-historico"]],
  });
}
