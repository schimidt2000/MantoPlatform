import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";

/**
 * Conferência de personagens do catálogo (feature 360).
 *
 * A leitura das fotos propôs o tipo de cada item e os personagens que aparecem; aqui a Superadmin
 * confere. Nada deste módulo altera o catálogo: as rotas só registram decisões
 * (`app/admin/catalog_conferencia_ops.py`).
 */

export type TipoDoItem = "tema" | "dupla" | "avulso" | "generico";
export type SituacaoDoItem = "a_conferir" | "conferido" | "sem_leitura";
export type DecisaoDoPersonagem = "criar" | "nao_criar";

export const TIPOS_DO_ITEM: TipoDoItem[] = ["tema", "dupla", "avulso", "generico"];
export const ROTULO_DO_TIPO: Record<TipoDoItem, string> = {
  tema: "Tema",
  dupla: "Dupla",
  avulso: "Avulso",
  generico: "Genérico",
};
export const ROTULO_DA_SITUACAO: Record<SituacaoDoItem, string> = {
  a_conferir: "A conferir",
  conferido: "Conferido",
  sem_leitura: "Sem leitura",
};
/** Tipos em que o elenco proposto vale; nos outros ele fica guardado, sem valer. */
export const TIPOS_COM_ELENCO: TipoDoItem[] = ["tema", "dupla"];

/**
 * "24/11 às 15h10" a partir do carimbo da API, que já vem em horário de São Paulo, sem fuso.
 * Recorte de texto, nunca `new Date(iso)`: o construtor leria como UTC e deslocaria 3 horas.
 */
export function quandoConferiu(iso: string): string {
  const [data, hora = ""] = iso.split("T");
  const [, mes, dia] = data.split("-");
  const [horas, minutos] = hora.split(":");
  return horas ? `${dia}/${mes} às ${horas}h${minutos}` : `${dia}/${mes}`;
}

export interface FichaDaConferencia {
  id: number;
  nome: string;
  foto_url: string | null;
}

export interface FotoDoPersonagem {
  url: string;
  largura: number | null;
  altura: number | null;
  /** `[x, y, largura, altura]` em % da foto original. */
  recorte: number[];
}

export interface PersonagemProposto {
  id: number;
  origem: "leitura" | "manual";
  nome: string;
  /** O que a leitura propôs; `null` em personagem acrescentado à mão. */
  nome_lido: string | null;
  /** `null` = sem foto utilizável (a leitura não achou, ou a foto saiu da galeria). */
  foto: FotoDoPersonagem | null;
  ficha: FichaDaConferencia | null;
  ficha_sugerida: FichaDaConferencia | null;
  aviso: string | null;
  sem_foto_lido: boolean;
  sem_foto: boolean;
  decisao: DecisaoDoPersonagem;
  observacao: string | null;
}

export interface ConferenciaDoItem {
  tipo: TipoDoItem;
  tipo_lido: TipoDoItem;
  nota: string | null;
  acao: string | null;
  grupo: string | null;
  lote: string | null;
  ficha: FichaDaConferencia | null;
  ficha_sugerida: FichaDaConferencia | null;
  observacao: string | null;
  conferido_em: string | null;
  conferido_por: string | null;
  personagens: PersonagemProposto[];
}

export interface ItemDaFila {
  id: number;
  nome: string;
  capa_url: string | null;
  situacao: SituacaoDoItem;
  /** `null` em item sem leitura. */
  tipo: TipoDoItem | null;
  tipo_lido: TipoDoItem | null;
  personagens: number;
  conferido_em: string | null;
  conferido_por: string | null;
}

export interface ContadoresDaFila {
  fila: number;
  a_conferir: number;
  conferidos: number;
  sem_leitura: number;
  por_tipo: Record<TipoDoItem, { total: number; conferidos: number }>;
}

export interface FilaDaConferencia {
  contadores: ContadoresDaFila;
  /** Quantos itens do arquivo da leitura ainda não foram carregados (mostra "Carregar leitura"). */
  leitura?: { itens_no_arquivo: number; a_carregar: number };
  itens: ItemDaFila[];
}

export interface DetalheDaConferencia {
  item: {
    id: number;
    nome: string;
    categorias: string[];
    fotos: { id: number; url: string }[];
  };
  na_fila: boolean;
  situacao: SituacaoDoItem;
  conferencia: ConferenciaDoItem | null;
  anterior_id: number | null;
  proximo_id: number | null;
}

export interface RespostaDaDecisao {
  conferencia: ConferenciaDoItem;
  situacao: SituacaoDoItem;
}

export interface ResumoDaCarga {
  itens_novos: number;
  personagens_novos: number;
  ja_existiam: number;
  ignorados: { id: number | null; nome: string | null; motivo: string }[];
}

export interface FiltrosDaFila {
  tipo?: string;
  situacao?: string;
  q?: string;
}

const BASE = "/api/admin/catalogo/conferencia";
const CHAVE = "catalogo-conferencia";

function consulta(filtros: FiltrosDaFila): string {
  const params = new URLSearchParams();
  if (filtros.tipo) params.set("tipo", filtros.tipo);
  if (filtros.situacao) params.set("situacao", filtros.situacao);
  if (filtros.q) params.set("q", filtros.q);
  const texto = params.toString();
  return texto ? `?${texto}` : "";
}

/** Fila da conferência. Os contadores são sempre os da fila inteira, não os do filtro. */
export function useFilaDaConferencia(filtros: FiltrosDaFila) {
  return useQuery<FilaDaConferencia>({
    queryKey: [CHAVE, "fila", filtros],
    queryFn: () => apiFetch<FilaDaConferencia>(`${BASE}${consulta(filtros)}`),
    // Cada letra da busca é uma chave nova: segura a lista anterior para a tela não piscar.
    placeholderData: keepPreviousData,
  });
}

/** Um item da conferência. `tipo` e `q` só servem para o "próximo" seguir o filtro da fila. */
export function useItemDaConferencia(itemId: number | undefined, filtros: FiltrosDaFila) {
  const vizinhos = { tipo: filtros.tipo, q: filtros.q };
  return useQuery<DetalheDaConferencia>({
    queryKey: [CHAVE, "item", itemId, vizinhos],
    queryFn: () => apiFetch<DetalheDaConferencia>(`${BASE}/${itemId}${consulta(vizinhos)}`),
    enabled: itemId !== undefined,
  });
}

export function useCarregarLeitura() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<ResumoDaCarga>(`${BASE}/carregar`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

/**
 * Depois de uma decisão: grava a conferência devolvida no cache do item (sem nova ida ao servidor,
 * para o cartão não piscar) e invalida a fila, cujos contadores podem ter mudado.
 */
function useAposDecisao(itemId: number) {
  const queryClient = useQueryClient();
  return (resposta: RespostaDaDecisao) => {
    queryClient.setQueriesData<DetalheDaConferencia>({ queryKey: [CHAVE, "item", itemId] }, (atual) =>
      atual ? { ...atual, conferencia: resposta.conferencia, situacao: resposta.situacao } : atual,
    );
    queryClient.invalidateQueries({ queryKey: [CHAVE, "fila"] });
  };
}

/**
 * Recusa por estado (409: outra pessoa conferiu ou reabriu o item enquanto esta tela estava aberta)
 * ou item que sumiu (404): relê o item, para a tela mostrar como ele está agora. Erro de validação
 * (400) fica só no campo.
 */
function useAoFalhar(itemId: number) {
  const queryClient = useQueryClient();
  return (erro: unknown) => {
    if (erro instanceof ApiRequestError && (erro.status === 409 || erro.status === 404)) {
      queryClient.invalidateQueries({ queryKey: [CHAVE, "item", itemId] });
      queryClient.invalidateQueries({ queryKey: [CHAVE, "fila"] });
    }
  };
}

/** Mensagem de um erro de decisão para mostrar na tela. */
export function mensagemDoErro(erro: unknown): string | null {
  if (!erro) return null;
  if (erro instanceof ApiRequestError) return erro.message;
  return "Não foi possível salvar. Tente novamente.";
}

/** Mensagem de validação de um campo, quando a API apontou o campo. */
export function erroDoCampo(erro: unknown, campo: string): string | null {
  return erro instanceof ApiRequestError ? (erro.fields?.[campo] ?? null) : null;
}

export interface CamposDoItem {
  tipo?: TipoDoItem;
  ficha_id?: number | null;
  observacao?: string;
}

export function useAlterarItem(itemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: (campos: CamposDoItem) =>
      apiFetch<RespostaDaDecisao>(`${BASE}/${itemId}`, { method: "PATCH", body: JSON.stringify(campos) }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}

export function useConferirItem(itemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: () => apiFetch<RespostaDaDecisao>(`${BASE}/${itemId}/conferir`, { method: "POST" }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}

export function useReabrirItem(itemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: () => apiFetch<RespostaDaDecisao>(`${BASE}/${itemId}/reabrir`, { method: "POST" }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}

export function useAcrescentarPersonagem(itemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: (campos: { nome: string; ficha_id?: number | null }) =>
      apiFetch<RespostaDaDecisao>(`${BASE}/${itemId}/personagens`, {
        method: "POST",
        body: JSON.stringify(campos),
      }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}

export interface CamposDoPersonagem {
  nome?: string;
  ficha_id?: number | null;
  decisao?: DecisaoDoPersonagem;
  sem_foto?: boolean;
  observacao?: string;
}

export function useAlterarPersonagem(itemId: number, personagemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: (campos: CamposDoPersonagem) =>
      apiFetch<RespostaDaDecisao>(`${BASE}/personagens/${personagemId}`, {
        method: "PATCH",
        body: JSON.stringify(campos),
      }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}

export function useExcluirPersonagem(itemId: number, personagemId: number) {
  const aposDecisao = useAposDecisao(itemId);
  const aoFalhar = useAoFalhar(itemId);
  return useMutation({
    mutationFn: () =>
      apiFetch<RespostaDaDecisao>(`${BASE}/personagens/${personagemId}`, { method: "DELETE" }),
    onSuccess: aposDecisao,
    onError: aoFalhar,
  });
}
