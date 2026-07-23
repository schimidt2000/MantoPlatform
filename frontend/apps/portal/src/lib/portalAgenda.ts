import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

const AGENDA_KEY = ["portal", "agenda"] as const;

/** Uma escalação (evento + personagem) — pendente, futura ou do histórico. */
export interface PortalRole {
  role_id: number;
  event_id: number;
  title: string;
  start_at: string | null;
  end_at: string | null;
  location: string | null;
  character_name: string;
  has_unacknowledged_change: boolean;
  change_description: string | null;
  cache_total?: number;
  payment_status?: string;
}

export interface PortalAgenda {
  pending_invites: PortalRole[];
  upcoming: PortalRole[];
  history: PortalRole[];
}

/** Agenda do talento: convites pendentes, eventos futuros e histórico com cachê. */
export function useAgenda() {
  return useQuery({
    queryKey: AGENDA_KEY,
    queryFn: () => apiFetch<PortalAgenda>("/api/portal/agenda"),
  });
}

/** Aceita um convite de casting pendente. */
export function useAcceptInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (roleId: number) =>
      apiFetch<{ role_id: number; invite_status: string }>(
        `/api/portal/invites/${roleId}/accept`,
        { method: "POST" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AGENDA_KEY });
    },
  });
}

/** Recusa um convite de casting pendente — confirmar com `window.confirm` antes de chamar. */
export function useRejectInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (roleId: number) =>
      apiFetch<{ role_id: number; invite_status: string }>(
        `/api/portal/invites/${roleId}/reject`,
        { method: "POST" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AGENDA_KEY });
    },
  });
}

/** Reconhece a alteração de um evento já aceito, limpando o aviso na Agenda. */
export function useAckEventChange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (roleId: number) =>
      apiFetch<{ role_id: number }>(`/api/portal/roles/${roleId}/ack-change`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AGENDA_KEY });
    },
  });
}
