import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe, RoleAvailability } from "./agenda";

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

/** Talento escalável neste evento — com rosto e agenda do dia (feature 215). */
export interface TalentoEscalavel extends TalentoOption {
  photo_url: string | null;
  availability: RoleAvailability;
}

/**
 * Talentos escaláveis com foto e disponibilidade calculada contra a janela DESTE evento
 * (feature 215) — é o que a busca de casting precisa mostrar antes de escalar alguém.
 *
 * Chave por evento (a disponibilidade muda com a data) e sem `staleTime`: escalar alguém
 * muda a agenda dos outros, então a lista é revalidada ao voltar para a tela.
 */
export function useCastingOptions(eventId: number) {
  return useQuery<{ items: TalentoEscalavel[] }>({
    queryKey: ["casting-options", eventId],
    queryFn: () =>
      apiFetch<{ items: TalentoEscalavel[] }>(`/api/events/${eventId}/casting-options`),
    enabled: Number.isFinite(eventId),
  });
}

interface AssignInput {
  roleId: number;
  talent_id: number | null;
  /**
   * Ausente = não mexe no cachê. Feature 312: tirar da escala no cancelado manda só
   * `{talent_id: null}` — com cachê no corpo o servidor recusa (a tela é só consulta).
   */
  cache_value?: number;
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

interface AddRoleInput {
  character_name: string;
  talent_id?: number | null;
  cache_value?: number;
  role_type?: string;
}

/** Adiciona um cargo ao evento. */
export function useAddRole(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, AddRoleInput>({
    mutationFn: (body) =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}/roles`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/** Remove um cargo do evento. */
export function useDeleteRole(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, number>({
    mutationFn: (roleId) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}`, { method: "DELETE" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/** Ação simples sobre um cargo (POST sem corpo) que devolve o evento atualizado. */
function useRoleAction(eventId: number, path: (roleId: number) => string) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, number>({
    mutationFn: (roleId) =>
      apiFetch<EventoDetalhe>(path(roleId), { method: "POST" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/** Reenvia o convite de um cargo com talento. */
export function useSendInvite(eventId: number) {
  return useRoleAction(eventId, (roleId) => `/api/roles/${roleId}/invite`);
}

/** Marca o figurino de um cargo como separado. */
export function useSetFigurinoDone(eventId: number) {
  return useRoleAction(eventId, (roleId) => `/api/roles/${roleId}/figurino-done`);
}

interface ToggleTransporteInput {
  roleId: number;
  /** `true` marca o integrante como responsável pelo veículo; `false` desmarca. */
  marcado: boolean;
}

/**
 * Marca/desmarca quem leva o carro no evento fora de SP (feature 239). Ida e volta na mesma
 * rota, como o "figurino separado": `POST` marca, `DELETE` desmarca. O teto de cachê da pessoa
 * marcada sobe a parcela de um veículo — quem recalcula é o servidor, que devolve o evento
 * inteiro atualizado (inclusive `cache_cap_efetivo`).
 */
export function useToggleTransporte(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, ToggleTransporteInput>({
    mutationFn: ({ roleId, marcado }) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}/transporte`, {
        method: marcado ? "POST" : "DELETE",
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

/** Dispensa um cargo sem talento (para de contar como pendente, sem excluir). */
export function useDismissRole(eventId: number) {
  return useRoleAction(eventId, (roleId) => `/api/roles/${roleId}/dismiss`);
}

/** Restaura um cargo dispensado. */
export function useRestoreRole(eventId: number) {
  return useRoleAction(eventId, (roleId) => `/api/roles/${roleId}/restore`);
}

interface CargoDaHome {
  roleId: number;
  eventId: number;
}

/**
 * Dispensar/restaurar direto da linha da Home (feature 308) — mesmos endpoints da página do evento
 * (só SUPERADMIN). A Home lista cargos de vários eventos, então o evento vem na chamada, e o que
 * precisa atualizar é o dashboard (a linha sai de "A escalar" e entra em "Dispensados").
 */
export function useAcaoNoCargoDaHome(acao: "dismiss" | "restore") {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, CargoDaHome>({
    mutationFn: ({ roleId }) =>
      apiFetch<EventoDetalhe>(`/api/roles/${roleId}/${acao}`, { method: "POST" }),
    onSuccess: (updated, { eventId }) => {
      queryClient.setQueryData(["event", eventId], updated);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

/**
 * O link "Avisar no WhatsApp" de um escalado de evento cancelado (feature 312, FR-026): a Home do
 * Casting e a escala da tela do cancelado mandam a MESMA mensagem — sem link do portal (o portal não
 * mostra o cancelado). A data sai "DD/MM" direto do texto do horário de parede (sem `new Date()`,
 * que desloca o fuso). `null` sem número: a tela diz "sem WhatsApp no cadastro".
 */
export function avisoDeCancelamentoNoWhatsApp(aviso: {
  whatsapp: string | null | undefined;
  nome: string;
  evento: string;
  inicio: string | null | undefined;
  personagem: string | null | undefined;
}): string | null {
  const numero = (aviso.whatsapp ?? "").replace(/\D/g, "");
  if (!numero) return null;
  const dia = aviso.inicio ? ` de ${aviso.inicio.slice(8, 10)}/${aviso.inicio.slice(5, 7)}` : "";
  const texto =
    `Oi, ${aviso.nome}! O evento "${aviso.evento}"${dia}, em que você faria ` +
    `${aviso.personagem ?? "o seu papel"}, foi cancelado. Qualquer dúvida, fale com a gente.`;
  return `https://wa.me/${numero}?text=${encodeURIComponent(texto)}`;
}
