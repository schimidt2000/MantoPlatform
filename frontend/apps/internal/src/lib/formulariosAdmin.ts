import {
  type QueryClient,
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";
import { invalidarNotificacoes } from "./notificacoes";
import type { MotivoEncerramento, SugestaoDeEvento } from "./types";

export interface FormResponseSummary {
  id: number;
  form_type: "comum" | "corporativo";
  form_type_label: string;
  contact_name: string;
  contact_phone_display: string;
  event_date: string | null;
  client_id: number | null;
  /** Nome do cliente vinculado — vem já na listagem, alimenta o badge "Cliente: <nome>". */
  client_name: string | null;
  event_id: number | null;
  event_link_source: string | null;
  event_link_ambiguous: boolean;
  event_link_locked: boolean;
  created_at: string;
  // Feature 298 — opcionais: servidor e site sobem separados e ficam ~1 min em versões diferentes.
  /** Destino do formulário, calculado no servidor com a mesma regra das contagens. */
  destino?: Destino;
  /** "Festa" ou "Corporativo". */
  tipo_rotulo?: string;
  /** 'manual' | 'auto_phone' | 'evento' (veio do evento ligado). */
  client_link_source?: string | null;
  closed_reason?: string | null;
  closed_reason_label?: string | null;
  closed_note?: string | null;
  closed_by_name?: string | null;
  closed_at?: string | null;
}

export interface FormResponseDetail extends FormResponseSummary {
  data_sections: { secao: string; campos: [string, string, string][] }[];
  event_title: string | null;
}

/** Destino de um formulário — as partições que somam o total (feature 298). */
export type Destino = "sem_destino" | "com_evento" | "encerrados" | "historico";

/** Filtros aceitos pelo backend (`formularios_ops.STATUS_FILTERS`); vazio = todas. */
export type StatusFilter = "" | Destino;

/** Contadores dos cartões, também servidos na Home — todos opcionais pelo mesmo motivo acima. */
export interface StatusCounts {
  total?: number;
  sem_destino?: number;
  com_evento?: number;
  encerrados?: number;
  historico?: number;
  /** Dia do corte (AAAA-MM-DD, São Paulo): o que chegou antes é histórico. */
  corte?: string;
}

interface ListaRespostas {
  responses: FormResponseSummary[];
  counts: StatusCounts;
  /** `true` quando o filtro tem mais que as 200 respostas mostradas. */
  truncado?: boolean;
}

/** Lista as respostas de formulário mais recentes + contadores dos cartões por destino. */
export function useFormResponses(filtro: StatusFilter = "") {
  return useQuery<ListaRespostas>({
    queryKey: ["formularios-respostas", filtro],
    queryFn: () =>
      apiFetch<ListaRespostas>(
        `/api/formularios/respostas${filtro ? `?filtro=${filtro}` : ""}`,
      ),
    // Trocar de cartão não pisca a tela: mantém lista+contadores anteriores até chegar o novo.
    placeholderData: keepPreviousData,
  });
}

/** Busca respostas por nome/telefone. */
export function useSearchFormResponses(q: string) {
  return useQuery<{ responses: FormResponseSummary[] }>({
    queryKey: ["formularios-respostas-search", q],
    queryFn: () =>
      apiFetch<{ responses: FormResponseSummary[] }>(
        `/api/formularios/respostas/search?q=${encodeURIComponent(q)}`,
      ),
    enabled: q.trim().length >= 2,
  });
}

/** O que o detalhe pode oferecer — o servidor recusa o resto do mesmo jeito (feature 298). */
export interface FlagsDoFormulario {
  pode_encerrar?: boolean;
  pode_reabrir?: boolean;
  pode_criar_evento?: boolean;
}

export interface DetalheResposta {
  response: FormResponseDetail;
  suggested_client: { id: number; name: string } | null;
  can_edit_structure: boolean;
  /** Opcionais (feature 298): servidor e site sobem separados. */
  motivos_encerramento?: MotivoEncerramento[];
  /** Evento da cliente a até 3 dias — só quando o formulário está sem destino. */
  sugestao?: SugestaoDeEvento | null;
  flags?: FlagsDoFormulario;
}

/** Detalhe completo de uma resposta + sugestão de cliente. */
export function useFormResponseDetail(id: number | null) {
  return useQuery<DetalheResposta>({
    queryKey: ["formularios-resposta-detalhe", id],
    queryFn: () => apiFetch<DetalheResposta>(`/api/formularios/respostas/${id}`),
    enabled: id != null,
  });
}

/**
 * Recarrega tudo que mostra o destino de um formulário (feature 298): detalhe, lista, busca,
 * Home, métricas de cliente e o sino — ligar ou encerrar apaga o aviso para todos.
 *
 * A chave da Home é ["dashboard", periodo]: invalidar o prefixo pega todos os períodos. Sem isso,
 * o `staleTime` de 30 s com `refetchOnWindowFocus: false` deixa a linha resolvida NA TELA, e uma
 * lista que não acompanha a ação parece que a ação não salvou. A busca tem chave própria
 * (`formularios-respostas-search` não é filha de `formularios-respostas`).
 */
export function invalidarDestinoDeFormulario(queryClient: QueryClient, id?: number) {
  void queryClient.invalidateQueries({
    queryKey: id != null ? ["formularios-resposta-detalhe", id] : ["formularios-resposta-detalhe"],
  });
  void queryClient.invalidateQueries({ queryKey: ["formularios-respostas"] });
  void queryClient.invalidateQueries({ queryKey: ["formularios-respostas-search"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  // A ficha da cliente pode ter acabado de ganhar/perder uma festa no histórico, e o gráfico
  // de origem muda quando a associação cria uma cliente nova.
  void queryClient.invalidateQueries({ queryKey: ["clientes-metricas"] });
  invalidarNotificacoes(queryClient);
}

function invalidateResponse(queryClient: QueryClient, id: number) {
  invalidarDestinoDeFormulario(queryClient, id);
}

/** Mensagem da API em pt-BR, ou o texto de reserva quando a falha não veio do servidor. */
export function mensagemDaApi(erro: unknown, reserva: string): string {
  return erro instanceof ApiRequestError && erro.message ? erro.message : reserva;
}

/** Associa a resposta a um cliente existente ou cria um a partir dos dados dela. */
export function useAssociateClient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (clientId?: number) =>
      apiFetch<{ client_id: number; client_name: string }>(`/api/formularios/respostas/${id}/associar`, {
        method: "POST",
        body: JSON.stringify({ client_id: clientId }),
      }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Remove a associação da resposta com o cliente. */
export function useDissociateClient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/formularios/respostas/${id}/desassociar`, { method: "POST" }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Cliente do formulário que não é nenhuma das clientes do evento (feature 298, FR-015). */
export interface DivergenciaCliente {
  formulario: { id: number | null; nome: string | null };
  evento: { id: number | null; nome: string | null };
}

/** Resposta de ligar formulário a evento — opcional campo a campo (servidor e site sobem separados). */
export interface ResultadoVinculo {
  response?: FormResponseSummary;
  divergencia_cliente?: DivergenciaCliente | null;
  event_id?: number;
  event_title?: string;
}

/** Vincula manualmente a resposta a um evento da agenda (409 se ela já tem evento — feature 298). */
export function useLinkEvent(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) =>
      apiFetch<ResultadoVinculo>(`/api/formularios/respostas/${id}/vincular-evento`, {
        method: "POST",
        body: JSON.stringify({ event_id: eventId }),
      }),
    // `onSettled`: o 409 também recarrega — o formulário ganhou destino em outro lugar.
    onSettled: () => invalidateResponse(queryClient, id),
  });
}

/**
 * Encerra com motivo (feature 298). O id vai nas variáveis: uma instância serve à lista inteira
 * da Home, sem hook por linha.
 */
export function useEncerrarFormulario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motivo, frase }: { id: number; motivo: string; frase?: string }) =>
      apiFetch<{ response?: FormResponseSummary }>(`/api/formularios/respostas/${id}/encerrar`, {
        method: "POST",
        body: JSON.stringify({ motivo, frase: frase ?? "" }),
      }),
    onSettled: (_data, erro, { id }) => {
      // 400 é campo inválido: nada mudou no servidor. 409/422 recarregam — o destino mudou.
      if (erro instanceof ApiRequestError && erro.status === 400) return;
      invalidarDestinoDeFormulario(queryClient, id);
    },
  });
}

/**
 * "Este é o que vale" (feature 298): mantém o formulário e encerra como "Repetido" os outros sem
 * destino do mesmo telefone. Recarrega todos os detalhes — os encerrados também mudaram.
 */
export function useManterEntreRepetidos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ response?: FormResponseSummary; encerrados?: number[] }>(
        `/api/formularios/respostas/${id}/manter-entre-repetidos`,
        { method: "POST" },
      ),
    onSettled: () => invalidarDestinoDeFormulario(queryClient),
  });
}

/** "Parece ser este evento, é?" → "Ligar" (feature 298). Pode voltar `divergencia_cliente`. */
export function useConfirmarSugestao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, eventId }: { id: number; eventId: number }) =>
      apiFetch<ResultadoVinculo>(`/api/formularios/respostas/${id}/sugestao/${eventId}/confirmar`, {
        method: "POST",
      }),
    onSettled: (_data, _erro, { id }) => invalidarDestinoDeFormulario(queryClient, id),
  });
}

/** "Não é este" (feature 298): definitivo — a sugestão não volta para este formulário. */
export function useDescartarSugestao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, eventId }: { id: number; eventId: number }) =>
      apiFetch<{ ok?: boolean }>(`/api/formularios/respostas/${id}/sugestao/${eventId}/descartar`, {
        method: "POST",
      }),
    onSettled: (_data, _erro, { id }) => invalidarDestinoDeFormulario(queryClient, id),
  });
}

/** Desfaz o encerramento (feature 298). 409 quando outra pessoa já reabriu. */
export function useReabrirFormulario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ response?: FormResponseSummary }>(`/api/formularios/respostas/${id}/reabrir`, {
        method: "POST",
      }),
    onSettled: (_data, _erro, id) => invalidarDestinoDeFormulario(queryClient, id),
  });
}

/** Desfaz o vínculo de evento (automático ou manual). */
export function useUnlinkEvent(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/formularios/respostas/${id}/desvincular-evento`, { method: "POST" }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Exclui uma resposta (SUPERADMIN). */
export function useDeleteFormResponse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/formularios/respostas/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["formularios-respostas"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

// ══════════════════════════════════════════════════════════════════
//  Editor de estrutura dos formulários (SUPERADMIN)
// ══════════════════════════════════════════════════════════════════

export interface FormFieldDefinition {
  id: number;
  section_name: string;
  field_key: string;
  field_type: string;
  label: string;
  help_text: string | null;
  placeholder: string | null;
  required: boolean;
  options: string | null;
  order: number;
  is_system: boolean;
}

/** Definição de campos de um formulário (`comum`/`corporativo`). */
export function useFormFieldDefinitions(formType: "comum" | "corporativo") {
  return useQuery<{ fields: FormFieldDefinition[] }>({
    queryKey: ["formularios-editor", formType],
    queryFn: () => apiFetch<{ fields: FormFieldDefinition[] }>(`/api/formularios/editor/${formType}`),
  });
}

function invalidateEditor(queryClient: ReturnType<typeof useQueryClient>, formType: string) {
  queryClient.invalidateQueries({ queryKey: ["formularios-editor", formType] });
}

/** Tipos de campo aceitos pelo backend (`FormFieldDefinition.FIELD_TYPES`). */
export const FIELD_TYPES = [
  { value: "texto_curto", label: "Texto curto" },
  { value: "texto_longo", label: "Texto longo" },
  { value: "selecao", label: "Seleção (lista de opções)" },
  { value: "data", label: "Data" },
  { value: "hora", label: "Hora" },
  { value: "telefone", label: "Telefone" },
  { value: "email", label: "E-mail" },
  { value: "cpf", label: "CPF" },
  { value: "cnpj", label: "CNPJ" },
  { value: "cep", label: "CEP" },
  { value: "sim_nao", label: "Sim/Não" },
] as const;

/**
 * Converte o `options` do backend (string JSON `list[str]`) no texto do editor — uma opção
 * por linha, que é o formato que `create_field`/`update_field` esperam de volta.
 */
export function optionsToText(options: string | null): string {
  if (!options) return "";
  try {
    const parsed: unknown = JSON.parse(options);
    return Array.isArray(parsed) ? parsed.join("\n") : "";
  } catch {
    return "";
  }
}

export interface CreateFieldInput {
  label: string;
  section_name: string;
  field_type: string;
  help_text?: string;
  placeholder?: string;
  required?: boolean;
  options?: string;
}

/**
 * Corpo do PATCH de um campo. `update_field` no backend **substitui** todos estes atributos:
 * omitir `help_text`/`placeholder`/`required` os apaga. Por isso o payload é sempre completo
 * (menos `field_type`/`section_name`, que são imutáveis após a criação).
 */
export type UpdateFieldInput = {
  id: number;
  label: string;
  help_text?: string;
  placeholder?: string;
  required: boolean;
  options?: string;
};

/** Adiciona um campo personalizado ao fim de uma seção. */
export function useCreateField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateFieldInput) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/${formType}/campo`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo (payload completo). */
export function useUpdateField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: UpdateFieldInput) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/campo/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Reordena um campo dentro da própria seção. */
export function useMoveField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, direction }: { id: number; direction: "up" | "down" }) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/campo/${id}/mover`, {
        method: "POST",
        body: JSON.stringify({ direction }),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Remove um campo personalizado (campos de sistema são protegidos). */
export function useDeleteField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/formularios/editor/campo/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}
