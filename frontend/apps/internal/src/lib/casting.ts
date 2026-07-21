import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

export interface TalentoOption {
  id: number;
  name: string;
  artistic_name: string | null;
}

/** Talentos ativos para o seletor de casting. */
export function useTalents() {
  return useQuery<{ items: TalentoOption[] }>({
    queryKey: ["talents"],
    queryFn: () => apiFetch<{ items: TalentoOption[] }>("/api/talents"),
    staleTime: 5 * 60_000,
  });
}

interface AssignInput {
  roleId: number;
  talent_id: number | null;
  cache_value: number;
  travel_cache?: number;
}

/**
 * Escala/atualiza/desescala o talento de um cargo. Ao suceder, atualiza o cache do evento
 * com o estado retornado (a tela re-renderiza sem reload).
 */
export function useAssignRole(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, AssignInput>({
    mutationFn: ({ roleId, ...body }) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}/assign`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}
