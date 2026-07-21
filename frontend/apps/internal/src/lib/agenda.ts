import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Resumo de um evento na agenda (data-model.md: EventoResumo). Sem dado financeiro. */
export interface EventoResumo {
  id: number;
  title: string;
  event_type: string;
  start_at: string | null;
  end_at: string | null;
  location: string | null;
  characters: string[];
  is_satellite: boolean;
  group_name: string | null;
  confirmed: boolean;
}

export interface AgendaMes {
  ym: string;
  events: EventoResumo[];
  by_day: Record<string, number[]>;
}

export interface AgendaDia {
  day: string;
  events: EventoResumo[];
}

/** Agenda de um mês (`ym` = "YYYY-MM"). */
export function useAgenda(ym: string) {
  return useQuery<AgendaMes>({
    queryKey: ["agenda", ym],
    queryFn: () => apiFetch<AgendaMes>(`/api/agenda?ym=${encodeURIComponent(ym)}`),
  });
}

/** Eventos de um dia (`date` = "YYYY-MM-DD"). */
export function useAgendaDia(date: string) {
  return useQuery<AgendaDia>({
    queryKey: ["agenda-dia", date],
    queryFn: () => apiFetch<AgendaDia>(`/api/agenda/day/${date}`),
    enabled: Boolean(date),
  });
}
