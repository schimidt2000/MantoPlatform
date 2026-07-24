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

// ── Detalhe do evento (leitura) ──────────────────────────────────────────────
// Blocos financeiros são OPCIONAIS: só vêm no JSON conforme o papel (RBAC no servidor).

export interface RoleItem {
  role_id: number;
  character_name: string;
  role_type: string;
  talent: { id: number; name: string } | null;
  figurino_done: boolean;
  invite_status: string | null;
  dismissed: boolean;
  cache_value?: number | null; // só para casting/superadmin
  figurino_sheet_id: number | null;
  needs_makeup: boolean;
  is_singer: boolean;
}

export interface EventoDetalhe {
  event: {
    id: number;
    title: string;
    event_type: string;
    start_at: string | null;
    end_at: string | null;
    location: string | null;
    confirmed: boolean;
    confirmed_by: string | null;
    is_satellite: boolean;
    group_name: string | null;
    characters: string[];
    is_ensaio: boolean;
    // Logística (feature 149)
    makeup_time: string | null;
    makeup_location: string | null;
    departure_time: string | null;
    departure_location: string | null;
    needs_rehearsal: boolean;
  };
  flags: Record<string, boolean>;
  logs: { ts: string; actor_name: string; actor_role: string; message: string }[];
  elenco?: RoleItem[];
  observations?: {
    id: number;
    obs_type: string;
    content: string | null;
    label: string | null;
    image_url?: string | null;
  }[];
  venda?: {
    sale_value: number | null;
    sale_value_gross: number | null;
    transport_value: number | null;
    acrescimo_value: number | null;
    is_cortesia_permuta: boolean;
    with_invoice: boolean;
    seller: string | null;
    seller_id: number | null;
    sale_date: string | null;
    commission_rate: number | null;
    payment_method: string | null;
    payment_installments: number | null;
    payment_due_date: string | null;
    clients: { client_id: number; name: string | null; relation: string }[];
    form_response: { id: number; name: string; form_type: string } | null;
  };
  contratos?: { id: number; file_path: string; is_signed: boolean; created_at: string | null }[];
  notas_fiscais?: {
    id: number;
    amount: number | null;
    issue_date: string | null;
    status: string;
    file: string | null;
  }[];
  cobranca?: { outstanding: number | null; due: string | null; enabled: boolean };
  kpi?: {
    sale_value: number | null;
    cost: number | null;
    expenses_total: number | null;
    bv_total: number | null;
    commission: number | null;
    lucro: number | null;
    rate: number;
    group_size: number;
    seller: string | null;
  };
  pagamentos?: {
    items: { id: number; amount: number | null; file_path: string; created_at: string | null }[];
    received_total: number | null;
  };
  reembolsos?: {
    items: {
      id: number;
      description: string;
      amount: number | null;
      invoice_file_path: string | null;
      is_collected: boolean;
      collected_amount: number | null;
      receipt_file_path: string | null;
      created_at: string | null;
    }[];
    pendentes_total: number | null;
  };
}

/** Detalhe de um evento (leitura). */
export function useEvent(id: number) {
  return useQuery<EventoDetalhe>({
    queryKey: ["event", id],
    queryFn: () => apiFetch<EventoDetalhe>(`/api/events/${id}`),
    enabled: Number.isFinite(id),
  });
}
