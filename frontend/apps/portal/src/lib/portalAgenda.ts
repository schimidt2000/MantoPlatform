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
  /** Cachê da apresentação, sem o deslocamento. */
  cache_value: number;
  /** Ajuda de deslocamento, quando houver. */
  travel_cache: number;
  /** `cache_value + travel_cache` — o que o artista recebe por esta escalação. */
  cache_total: number;
  /** `false` enquanto a produção ainda não definiu o cachê — distingue de "combinado R$ 0,00". */
  cache_defined: boolean;
  payment_status: string;
  /**
   * Há ficha de figurino que ESTA pessoa pode ver neste evento — como intérprete (personagem
   * dela) ou como coordenadora (elenco inteiro). `false` esconde o link: mandar o artista para
   * uma tela que diz "ainda não há ficha" é o que fazia parecer que o figurino não subiu.
   */
  has_figurino: boolean;
  /**
   * `null` = convite nunca enviado · `pending` = enviado, sem resposta · `accepted`.
   *
   * A lista passou a incluir escalação não aceita (feature 230), então a tela precisa poder
   * avisar que falta responder — só `pending` tem o que responder.
   */
  invite_status: string | null;
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
