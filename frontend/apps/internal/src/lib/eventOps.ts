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

// ── Coleções comerciais: acréscimos, notas fiscais e parcelas (feature 253) ──
//
// Até aqui as três só podiam ser editadas pelo formulário Jinja. Acréscimos e parcelas usam PUT
// com a lista inteira (o corpo é a verdade, não um delta); notas fiscais têm CRUD por id, porque
// cada uma carrega um anexo que sobe por multipart.

export interface AcrescimoInput {
  tipo: string;
  descricao?: string | null;
  is_percent?: boolean;
  value: number | string;
  bv_recipient?: string | null;
  bv_pix?: string | null;
}

export interface ParcelaInput {
  due_date: string;
  amount: number | string;
}

/** Invalida o detalhe do evento e o que depende do dinheiro dele. */
function invalidarComercial(queryClient: ReturnType<typeof useQueryClient>, eventId: number) {
  queryClient.invalidateQueries({ queryKey: ["event", eventId] });
  queryClient.invalidateQueries({ queryKey: ["vendas-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["financeiro-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos"] });
  // Acréscimo muda a BASE da comissão (o BV sai dela), então a linha a pagar é recalculada.
  queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
}

/**
 * Substitui os acréscimos do evento (features 099/100). RBAC no servidor:
 * Comercial/Financeiro/Superadmin — acréscimo mexe na base da comissão e o BV é repasse a terceiro.
 *
 * A lista enviada é a verdade: mandar `[]` apaga todos. O servidor congela acréscimo percentual em
 * reais sobre a venda do momento, e preserva o status de pagamento de um BV já pago.
 */
export function useSetAcrescimos(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, AcrescimoInput[]>({
    mutationFn: (items) =>
      apiFetch(`/api/events/${eventId}/acrescimos`, {
        method: "PUT",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () => invalidarComercial(queryClient, eventId),
  });
}

/** Substitui o cronograma de parcelas (feature 065). Parcela sem data ou sem valor é ignorada. */
export function useSetParcelas(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, ParcelaInput[]>({
    mutationFn: (items) =>
      apiFetch(`/api/events/${eventId}/parcelas`, {
        method: "PUT",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () => invalidarComercial(queryClient, eventId),
  });
}

/**
 * Edita uma nota fiscal (feature 251). `multipart`, porque a nota carrega anexo.
 *
 * Enviar arquivo **emite** a nota; não enviar preserva o anexo atual — é edição de valor ou data,
 * não remoção do anexo.
 */
export function useUpdateNotaFiscal(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, { id: number; amount?: string; issue_date?: string; file?: File }>({
    mutationFn: ({ id, amount, issue_date, file }) => {
      const form = new FormData();
      // Número puro, nunca o formato BRL: `_decimal_from_form` no servidor não entende vírgula.
      if (amount !== undefined) form.append("amount", amount);
      if (issue_date !== undefined) form.append("issue_date", issue_date);
      if (file) form.append("file", file);
      return apiFetch(`/api/events/${eventId}/invoices/${id}`, { method: "PATCH", body: form });
    },
    onSuccess: () => invalidarComercial(queryClient, eventId),
  });
}

/** Remove uma nota fiscal (feature 251). O arquivo em disco NÃO é apagado — documento contábil. */
export function useDeleteNotaFiscal(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, number>({
    mutationFn: (invoiceId) =>
      apiFetch(`/api/events/${eventId}/invoices/${invoiceId}`, { method: "DELETE" }),
    onSuccess: () => invalidarComercial(queryClient, eventId),
  });
}

// ── Agrupar / desagrupar eventos (feature 246) ───────────────────────────────

/** Um evento que pode entrar no grupo, como devolvido por `/grupo/candidatos`. */
export interface CandidatoGrupo {
  id: number;
  title: string;
  start_at: string | null;
  event_type: string;
  /** `true` = tem valor de venda, e vai PERDÊ-LO ao virar satélite. */
  has_sale: boolean;
  /** Preenchido = não pode ser agrupado; o texto explica por quê. */
  blocked_reason: string | null;
}

export interface AgruparInput {
  leader_event_id: number;
  target_event_ids: number[];
  group_name?: string;
  /** Só `true` depois que a pessoa viu a lista do que será apagado. */
  confirm_clear_financials?: boolean;
}

/** Um evento que perde a venda ao ser agrupado — vem no 409 de confirmação. */
export interface EventoComVenda {
  id: number;
  title: string;
  sale_value: string;
}

/**
 * Candidatos a satélite, buscados no SERVIDOR (mínimo 2 caracteres).
 *
 * A busca é do servidor de propósito: a tela antiga carregava os 354 eventos de uma vez no HTML
 * e filtrava no navegador. `enabled` evita a chamada enquanto o diálogo está fechado.
 */
export function useCandidatosGrupo(eventId: number, q: string, enabled: boolean) {
  return useQuery<{ items: CandidatoGrupo[]; min_chars: number }>({
    queryKey: ["grupo-candidatos", eventId, q],
    queryFn: () =>
      apiFetch<{ items: CandidatoGrupo[]; min_chars: number }>(
        `/api/events/${eventId}/grupo/candidatos?q=${encodeURIComponent(q)}`,
      ),
    enabled: enabled && q.trim().length >= 2,
    staleTime: 0,
  });
}

/**
 * Invalida tudo que um agrupamento suja. Compartilhado pelas quatro mutações do grupo.
 *
 * As chaves vão SEM id de propósito: a operação toca dois ou mais eventos e o hook só conhece o
 * id de um deles — `invalidateQueries` casa por prefixo. Corrigir só o evento aberto deixaria o
 * outro lado do grupo com número velho na tela.
 */
function invalidarGrupo(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["event"] });
  queryClient.invalidateQueries({ queryKey: ["agenda"] });
  queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
  queryClient.invalidateQueries({ queryKey: ["agenda-search"] });
  // A venda do satélite migra para o grupo e a comissão a pagar dele é cancelada.
  queryClient.invalidateQueries({ queryKey: ["vendas-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
  queryClient.invalidateQueries({ queryKey: ["financeiro-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  // `is_group_leader` muda, e é ele que trava/destrava o botão de excluir.
  queryClient.invalidateQueries({ queryKey: ["evento-impacto-exclusao"] });
}

/**
 * Agrupa eventos sob um principal (feature 246). RBAC no servidor: Comercial/Financeiro/Superadmin.
 *
 * Sem `confirm_clear_financials`, o servidor responde 409 com a lista de eventos que perderiam a
 * venda — é isso que o diálogo usa para mostrar nomes e valores antes de confirmar. A resposta
 * traz `leader_id`: quem agrupa pode eleger OUTRO evento como principal, e aí a página em que a
 * pessoa está acabou de virar satélite.
 */
export function useAgruparEventos(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe & { leader_id: number }, Error, AgruparInput>({
    mutationFn: (input) =>
      apiFetch(`/api/events/${eventId}/grupo`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidarGrupo(queryClient),
  });
}

/**
 * Solta ESTE evento do grupo (feature 246) — só faz sentido em satélite.
 *
 * Não restaura os campos comerciais: eles foram apagados no agrupamento. A cópia do que havia
 * ficou no histórico do evento.
 */
export function useDesagruparEvento(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, void>({
    mutationFn: () => apiFetch(`/api/events/${eventId}/grupo`, { method: "DELETE" }),
    onSuccess: () => invalidarGrupo(queryClient),
  });
}

/**
 * Tira um satélite a partir da tela do PRINCIPAL (feature 246).
 *
 * Existe para não ser preciso abrir cada satélite: o maior grupo do sistema tem 13. E é o que
 * destrava cancelar um evento principal, que o sistema recusa enquanto houver satélites.
 */
export function useRemoverSatelite(leaderId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, number>({
    mutationFn: (satelliteId) =>
      apiFetch(`/api/events/${leaderId}/grupo/satelites/${satelliteId}`, { method: "DELETE" }),
    onSuccess: () => invalidarGrupo(queryClient),
  });
}

/** Nomeia, renomeia ou limpa o nome do grupo (feature 246) — sempre no principal. */
export function useRenomearGrupo(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, string | null>({
    mutationFn: (groupName) =>
      apiFetch(`/api/events/${eventId}/grupo`, {
        method: "PATCH",
        body: JSON.stringify({ group_name: groupName }),
      }),
    onSuccess: () => invalidarGrupo(queryClient),
  });
}
