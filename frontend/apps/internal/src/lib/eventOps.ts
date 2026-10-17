import { useEffect, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";
import type { EventoDetalhe, ModoDevolucao, RegimeCancelamento, ResumoCancelado } from "./agenda";
import { invalidarFinanceiro } from "./financeiro";
import { invalidarNotificacoes } from "./notificacoes";
import { invalidarSumidosGoogle } from "./sumidosGoogle";

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
 * com o estado retornado. Sem gate de papel no servidor. Desde a 303 o "Sincronizar" pode retirar
 * a marca "Sumiu do Google Agenda" de um evento que voltou — a faixa e o sino caem no clique, sem
 * esperar o poll de 60 s.
 */
export function useSyncEvent(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, void>({
    mutationFn: () => apiFetch<EventoDetalhe>(`/api/events/${eventId}/sync`, { method: "POST" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
      invalidarSumidosGoogle(queryClient);
      invalidarNotificacoes(queryClient);
    },
  });
}

/**
 * Exclui o evento (feature 151). RBAC no servidor: `_CAN_DELETE` (Comercial/Superadmin); um evento
 * líder de grupo é recusado (409). Ao suceder, remove o cache do evento e invalida a agenda e a
 * Home (feature 299: o evento excluído sai de "Cobranças" e "Sem valor" sem esperar o cache); a
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
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      // Feature 306: o marcado excluído sai da lista de sumidos sem esperar o poll.
      invalidarSumidosGoogle(queryClient);
    },
  });
}

// ── Excluir / cancelar / solicitar exclusão (feature 224) ────────────────────

/**
 * Os 18 `codigo` das recusas do cancelamento e das correções do cancelado (feature 306,
 * data-model §6.2). O verify confere que esta união e `CODIGOS_RECUSA_DO_CANCELAMENTO` têm os
 * mesmos membros.
 */
export type CodigoRecusaCancelamento =
  | "cancelado"
  | "ja_cancelado"
  | "ensaio"
  | "grupo_mudou"
  | "sem_outro_dia_vivo"
  | "cache_pago"
  | "devolucao_pendente"
  | "max_devolucao_mudou"
  | "tente_de_novo"
  | "nao_cancelado"
  | "regime_sem_retido"
  | "abaixo_do_piso"
  | "acima_do_teto"
  | "pago_abaixo_do_devolvido"
  | "bv_nao_esta_a_pagar"
  | "valor_mudou"
  | "devolucao_travada"
  | "estado_mudou";

/** O `codigo` de uma recusa da API, quando há. */
export function codigoDaRecusa(error: unknown): string | undefined {
  return error instanceof ApiRequestError ? (error.details.codigo as string | undefined) : undefined;
}

/** Uma escalação do evento (vaga × dia), como o resumo de impacto a descreve. */
export interface ImpactoElenco {
  character_name: string;
  talent_name: string | null;
  cache_value: number;
  payment_status: string;
  // Feature 306 — opcionais (backend antigo).
  role_id?: number;
  day_event_id?: number;
  talent_pix_informado?: boolean;
  /** Só com `show_financeiro`. */
  talent_pix?: string | null;
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
  // ── Feature 306 — todas opcionais: sem `regime`, o diálogo trava o envio ("O sistema está
  // atualizando"), porque o backend antigo recusaria o corpo novo. ──
  /** O que o ato daria (no principal: o do "todos"). */
  regime?: Exclude<RegimeCancelamento, "legado">;
  sumiu_do_google?: boolean;
  /** Pago do GRUPO; `total_recebido` continua o do próprio evento. */
  pago?: number;
  /** Devoluções aprovadas do grupo. */
  ja_devolvido?: number;
  /** Pago − já devolvido: o que "Tudo" devolve. */
  max_devolucao?: number;
  com_nota?: boolean;
  /** A alíquota de Configurações, só referência do imposto. */
  imposto_aliquota?: number;
  bvs?: {
    acrescimo_id: number;
    recebedor: string | null;
    cheio: number;
    pago: boolean;
    falta_recebedor: boolean;
    falta_pix: boolean;
  }[];
  comissao?: {
    beneficiario: { id: number; nome: string } | null;
    cheia: number;
    /** Pago + no banco. */
    paga: number;
    a_pagar: number;
  };
  /** Fuso de SP; negativo = "o evento foi há N dias". */
  faltam_dias?: number | null;
  comprovantes_sem_valor?: number;
  /** Total de cachê pago; > 0 → o diálogo explica e não oferece cancelar. */
  cache_pago?: number;
}

/** O efeito da prévia (`GET …/impacto-exclusao?devolucao=`) — a mesma conta da execução. */
export interface EfeitoCancelamento {
  devolucao: number;
  retido: number | null;
  comissao_cheia: number;
  comissao_retido: number | null;
  bv_retido: number;
  bvs?: { acrescimo_id: number; bv_retido: number }[];
  ja_liquidada: number;
  /** A linha (±) no primeiro repasse aberto; `null` = só a comissão a pagar muda. */
  ajuste: number | null;
  /** `AAAA-MM`. */
  ciclo: string | null;
  /** `AAAA-MM-05`. */
  repasse_em: string | null;
  devolucao_minima?: number;
  imposto_referencia: number | null;
}

function useDebounced<T>(valor: T, ms: number): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = window.setTimeout(() => setAtrasado(valor), ms);
    return () => window.clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}

/**
 * A prévia do cancelamento (feature 306, FR-011): o servidor faz a conta que o ato fará, sem
 * gravar. Espera 400 ms de digitação parada e mantém o último efeito na tela enquanto busca o
 * próximo (`keepPreviousData`), para os números não piscarem. O valor vai com ponto decimal.
 */
export function usePreviaCancelamento(
  eventId: number,
  devolucao: number | null,
  enabled: boolean,
  opcoes: { vendaNova?: number | null; alcance?: string | null } = {},
) {
  const valor = useDebounced(devolucao, 400);
  const vendaNova = useDebounced(opcoes.vendaNova ?? null, 400);
  const alcance = opcoes.alcance ?? null;
  return useQuery<{ efeito: EfeitoCancelamento }>({
    queryKey: ["evento-previa-cancelamento", eventId, valor, vendaNova, alcance],
    queryFn: () => {
      const params = new URLSearchParams({ devolucao: (valor ?? 0).toFixed(2) });
      if (vendaNova != null) params.set("venda_nova", vendaNova.toFixed(2));
      return apiFetch<{ efeito: EfeitoCancelamento }>(
        `/api/events/${eventId}/impacto-exclusao?${params.toString()}`,
      );
    },
    enabled: enabled && valor != null && Number.isFinite(valor) && valor >= 0,
    placeholderData: keepPreviousData,
    staleTime: 0,
    retry: false,
  });
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

/** O corpo de `POST …/cancelar` (feature 306, contracts §1). */
export interface CancelarEventoInput {
  motivo: string;
  /** Obrigatória na venda; ignorada na Loja Virtual. */
  devolucao?: {
    modo: ModoDevolucao;
    /** Parte: o valor; Tudo: o `max_devolucao` que a tela recebeu (só leitura). */
    valor?: number;
    nome?: string;
    pix?: string;
    observacao?: string;
  };
  /** Obrigatório (≥ 0) com nota; enviado sem nota → 400. */
  imposto_retido?: number;
  /** Completa o BV a pagar que está sem recebedor ou PIX. */
  bvs?: { acrescimo_id: number; recebedor: string; pix: string }[];
}

export interface CancelarEventoResult {
  ok: true;
  resumo?: ResumoCancelado | null;
  /** Google (falha ou trava de ambiente), sem o texto cru do erro. */
  aviso?: string | null;
  google_removido?: boolean;
  gasto_id?: number | null;
}

/** As chaves que um ato ou uma correção do cancelado muda (contracts §22). */
function invalidarDoCancelamento(queryClient: ReturnType<typeof useQueryClient>, eventId: number) {
  queryClient.invalidateQueries({ queryKey: ["event"] });
  queryClient.invalidateQueries({ queryKey: ["evento-impacto-exclusao", eventId] });
  queryClient.invalidateQueries({ queryKey: ["agenda"] });
  queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
  queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
  // Venda cancelada sai de Cobranças e de "Sem valor" (feature 299).
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["vendas-dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["admin-desempenho"] });
  queryClient.invalidateQueries({ queryKey: ["gastos-extras"] });
  invalidarFinanceiro(queryClient);
}

/**
 * Cancela o evento (feature 306): congela a venda, devolve à cliente (Tudo, Parte ou Nada), leva a
 * comissão e o BV ao retido e tira o evento do Google Agenda. O registro **não** é apagado.
 */
export function useCancelarEvento(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<CancelarEventoResult, ApiRequestError, CancelarEventoInput>({
    mutationFn: (input) =>
      apiFetch<CancelarEventoResult>(`/api/events/${eventId}/cancelar`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      invalidarDoCancelamento(queryClient, eventId);
      invalidarSumidosGoogle(queryClient);
      invalidarNotificacoes(queryClient);
    },
  });
}

export interface AlterarDevolucaoInput {
  /** O NOVO TOTAL devolvido (na venda, do grupo). */
  devolucao_total: number;
  nome?: string;
  pix?: string;
  observacao?: string;
  /** Só na venda com nota. */
  imposto_retido?: number;
}

/** "Alterar devolução" do cancelado (feature 306, contracts §3). Só o Superadmin. */
export function useAlterarDevolucao(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<{ ok: true; resumo: ResumoCancelado | null }, ApiRequestError, AlterarDevolucaoInput>({
    mutationFn: (input) =>
      apiFetch<{ ok: true; resumo: ResumoCancelado | null }>(`/api/events/${eventId}/devolucao`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["gastos-extras"] });
      queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
      invalidarFinanceiro(queryClient);
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

/** Os `codigo` de erro de `POST /api/events/<id>/devolver-ao-google` (feature 303). */
export type CodigoDevolverAoGoogle =
  | "cancelado"
  | "nao_marcado"
  | "venda_virtual"
  | "sem_data"
  | "google_travado"
  | "google_inconclusivo"
  | "google_desconectado"
  | "google_recusou";

/**
 * Devolve ao Google Agenda o evento marcado "Sumiu do Google Agenda" (feature 303). RBAC no
 * servidor: só Superadmin. O hook só mexe no cache — fechar o diálogo e anunciar o resultado
 * ficam nos callbacks do `mutate`, no `EventHeader`, porque o banner desmonta no sucesso.
 *
 * O erro é `ApiRequestError` (o `codigo` vem em `details.codigo`); falha de rede não é.
 */
export function useDevolverAoGoogle(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, ApiRequestError, void>({
    mutationFn: () =>
      apiFetch<EventoDetalhe>(`/api/events/${eventId}/devolver-ao-google`, { method: "POST" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-search"] });
      invalidarNotificacoes(queryClient);
      invalidarSumidosGoogle(queryClient);
    },
    onError: (error) => {
      // Erro de ESTADO (outro clique já devolveu, alguém cancelou): a tela está velha — recarrega
      // o evento e a faixa; o componente fecha o diálogo.
      const codigo = error instanceof ApiRequestError ? error.details.codigo : undefined;
      if (codigo === "nao_marcado" || codigo === "cancelado") {
        queryClient.invalidateQueries({ queryKey: ["event", eventId] });
        invalidarSumidosGoogle(queryClient);
      }
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
  /** Mantido por um ciclo; o `resumo` traz todas as devoluções. */
  devolucao: {
    id: number;
    amount: number;
    payee_name: string;
    payment_status: string;
  } | null;
  /** Feature 306 — opcional (backend antigo). */
  resumo?: ResumoCancelado | null;
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
  /** Feature 305 — a linha que veio do GET; o servidor herda status e PIX só da linha de mesmo id. */
  id?: number;
  tipo: string;
  /** Ausente = mantém a descrição gravada; `""` = apaga. */
  descricao?: string | null;
  is_percent?: boolean;
  value: number | string;
  bv_recipient?: string | null;
  bv_pix?: string | null;
  /** Feature 305 (converge): o R$ do BV a pagar que o editor abriu — se a venda o mudou depois
   * (outra aba, outra pessoa), o servidor recusa em vez de desfazer a proporção. */
  valor_visto?: number | null;
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
  // Parcela muda o vencimento da cobrança na Home (feature 299).
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  // Feature 306: no cancelado, o BV corrigido refaz a comissão e o BV do retido no painel.
  queryClient.invalidateQueries({ queryKey: ["cancelamentos"] });
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
    onSuccess: (atualizado) => {
      // Feature 305: o PUT devolve o detalhe novo — gravado já, o editor fecha mostrando os ids
      // novos (o PUT recria as linhas) e sem o alerta "Lançar o BV"; esperar o refetch abria uma
      // janela em que reabrir dava o falso "a venda mudou" e travava o Salvar.
      queryClient.setQueryData(["event", eventId], atualizado);
      invalidarComercial(queryClient, eventId);
      // Feature 305: salvar os acréscimos mexe no BV da Planilha e na comissão na mesma requisição.
      void queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos"] });
      void queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
    },
    // A recusa "o BV mudou desde que o editor abriu" pede o detalhe novo: com ele, o aviso do editor
    // ("a venda mudou… cancele e abra de novo") acende.
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ["event", eventId] });
    },
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
