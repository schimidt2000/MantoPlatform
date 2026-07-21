import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

export interface AddObservationInput {
  obs_type: "text" | "link";
  content: string;
  label?: string;
}

/**
 * Adiciona uma observação de texto/link ao evento (feature 150). Ao suceder, atualiza o cache do
 * evento com o estado retornado (a tela re-renderiza sem reload). Sem gate de papel no servidor.
 */
export function useAddObservation(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, AddObservationInput>({
    mutationFn: (body) =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}/observations`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/**
 * Remove uma observação do evento (feature 150). Ao suceder, atualiza o cache do evento com o
 * estado retornado. Sem gate de papel no servidor.
 */
export function useDeleteObservation(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, number>({
    mutationFn: (obsId) =>
      apiFetch<EventoDetalhe>(`/api/observations/${obsId}`, { method: "DELETE" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}
