import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

/**
 * Confirma/desconfirma o evento (toggle, feature 149). Ao suceder, atualiza o cache do evento
 * com o estado retornado (a tela re-renderiza sem reload). RBAC no servidor: Comercial/Superadmin.
 */
export function useToggleConfirm(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, void>({
    mutationFn: () =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}/confirm`, { method: "POST" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

export interface LogisticsInput {
  makeup_time: string;
  makeup_location: string;
  departure_time: string;
  departure_location: string;
  needs_rehearsal: boolean;
}

/**
 * Salva a logística do evento (maquiagem, saída, "precisa ensaio" — feature 149). RBAC no
 * servidor: quem pode editar o evento (`_CAN_EDIT_EVENT`).
 */
export function useSaveLogistics(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, LogisticsInput>({
    mutationFn: (body) =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}/logistics`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/**
 * Sincroniza o evento com o Google Calendar (feature 151). Ao suceder, atualiza o cache do evento
 * com o estado retornado. Sem gate de papel no servidor.
 */
export function useSyncEvent(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, void>({
    mutationFn: () => apiFetch<EventoDetalhe>(`/api/events/${eventId}/sync`, { method: "POST" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/**
 * Exclui o evento (feature 151). RBAC no servidor: `_CAN_DELETE` (Comercial/Superadmin); um evento
 * líder de grupo é recusado (409). Ao suceder, remove o cache do evento e invalida a agenda; a
 * navegação de volta fica com o componente.
 */
export function useDeleteEvent(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<{ ok: boolean; aviso: string | null }, Error, void>({
    mutationFn: () =>
      apiFetch<{ ok: boolean; aviso: string | null }>(`/api/events/${eventId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
    },
  });
}

// ── Excluir / cancelar / solicitar exclusão (feature 224) ────────────────────

/** Elenco escalado no evento, como o resumo de impacto o descreve. */
export interface ImpactoElenco {
  character_name: string;
  talent_name: string | null;
  cache_value: number;
  payment_status: string;
}

/**
 * O que será perdido/afetado ao excluir ou cancelar. A tela abre o diálogo com isso — antes ela
 * só perguntava "tem certeza?", sem dizer que havia pagamento recebido em jogo.
 */
export interface ImpactoExclusao {
  /** `"excluir"` = evento vazio, some de vez; `"cancelar"` = tem dinheiro, o registro fica. */
  acao: "excluir" | "cancelar";
  sale_value: number;
  total_recebido: number;
  devolucao_sugerida: number;
  cliente_nome: string | null;
  elenco: ImpactoElenco[];
  comissoes: { id: number; seller_name: string | null; amount: number; status: string }[];
  gastos_vinculados: { id: number; description: string; amount: number }[];
  tem_contrato: boolean;
  is_group_leader: boolean;
}

/** Resumo de impacto — só carregado quando o diálogo abre (`enabled`). */
export function useImpactoExclusao(eventId: number, enabled: boolean) {
  return useQuery<ImpactoExclusao>({
    queryKey: ["evento-impacto-exclusao", eventId],
    queryFn: () => apiFetch<ImpactoExclusao>(`/api/events/${eventId}/impacto-exclusao`),
    enabled,
    staleTime: 0,
  });
}

export interface CancelarEventoInput {
  motivo: string;
  devolucao?: { valor: number; nome: string; pix: string; observacao?: string };
}

/**
 * Cancela o evento: resolve a comissão (paga vira estorno negativo), registra a devolução como
 * Gasto Extra aprovado e tira o evento do Google Agenda. O registro **não** é apagado.
 */
export function useCancelarEvento(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<
    { ok: boolean; gasto_id: number | null; google_removido: boolean; aviso: string | null },
    Error,
    CancelarEventoInput
  >({
    mutationFn: (input) =>
      apiFetch(`/api/events/${eventId}/cancelar`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
      queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
    },
  });
}

/** Comercial pede a exclusão; o Superadmin decide depois. */
export function useSolicitarExclusao(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<{ ok: boolean }, Error, { motivo: string }>({
    mutationFn: (input) =>
      apiFetch(`/api/events/${eventId}/solicitar-exclusao`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
    },
  });
}

/** Superadmin recusa a solicitação — o evento volta ao normal. */
export function useRecusarSolicitacao(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<{ ok: boolean }, Error, { motivo?: string }>({
    mutationFn: (input) =>
      apiFetch(`/api/events/${eventId}/solicitar-exclusao`, {
        method: "DELETE",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
    },
  });
}

export interface CancelamentoPendente {
  id: number;
  title: string;
  start_at: string | null;
  sale_value: number;
  requested_at: string;
  requested_by: string | null;
  reason: string | null;
}

export interface EventoCancelado {
  id: number;
  title: string;
  start_at: string | null;
  sale_value: number;
  cancelled_at: string;
  cancelled_by: string | null;
  reason: string | null;
  devolucao: {
    id: number;
    amount: number;
    payee_name: string;
    payment_status: string;
  } | null;
}

/** Fila do Superadmin: solicitações pendentes + eventos já cancelados. */
export function useCancelamentos() {
  return useQuery<{ pendentes: CancelamentoPendente[]; cancelados: EventoCancelado[] }>({
    queryKey: ["cancelamentos"],
    queryFn: () =>
      apiFetch<{ pendentes: CancelamentoPendente[]; cancelados: EventoCancelado[] }>(
        "/api/events/cancelamentos",
      ),
  });
}
