import { useMutation, useQueryClient } from "@tanstack/react-query";
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
