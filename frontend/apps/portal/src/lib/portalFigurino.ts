import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FigurinoSheet {
  character_name: string;
  photo_url: string | null;
  /** Quem interpreta o personagem — só interessa na visão do coordenador. */
  talent_name: string | null;
  notes: string | null;
  pieces: { name: string; qty: number }[];
}

export interface FigurinoResponse {
  event: { id: number; title: string; start_at: string | null };
  /** O talento é o coordenador deste evento: recebe as fichas do elenco inteiro. */
  is_coordinator: boolean;
  sheets: FigurinoSheet[];
}

/** Ficha(s) de figurino do talento num evento em que está escalado. */
export function useFigurino(eventId: number | undefined) {
  return useQuery({
    queryKey: ["portal", "figurino", eventId],
    queryFn: () => apiFetch<FigurinoResponse>(`/api/portal/events/${eventId}/figurino`),
    enabled: eventId !== undefined,
  });
}
