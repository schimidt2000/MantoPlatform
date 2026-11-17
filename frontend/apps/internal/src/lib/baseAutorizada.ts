import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Feature 350 — a base autorizada: os dois consentimentos da ficha (novidades e aniversário da
 * criança), indicação, parceiros, aniversários dos próximos 60 dias e o pós-evento único.
 *
 * RBAC é do servidor: o bloco `criancas` só vem para Comercial e Superadmin, e `flags` diz se a
 * tela mostra os botões. Todo campo novo no payload da ficha é opcional (janela de deploy).
 */

export interface TextoDeConsentimento {
  texto: string;
  versao: string;
}

export interface AceiteDeNovidades {
  ativo: boolean;
  aceite_em: string | null;
  origem: string | null;
  versao: string | null;
  retirada_em: string | null;
  retirada_origem: string | null;
}

export interface CriancaDaFicha {
  id: number;
  primeiro_nome: string;
  nascimento: string;
  aceite_em: string | null;
  origem: string;
  versao: string;
}

export interface LinhaDoConsentimento {
  tipo: "novidades" | "aniversario";
  acao: "aceite" | "retirada";
  em: string | null;
  origem: string;
  versao: string;
  texto: string;
  referencia: string | null;
  autor: string;
}

export interface Consentimentos {
  novidades: AceiteDeNovidades;
  /** Ausente para quem não vê dado de criança (Financeiro). */
  criancas?: CriancaDaFicha[];
  historico: LinhaDoConsentimento[];
  textos: { novidades: TextoDeConsentimento; aniversario: TextoDeConsentimento };
  origens: string[];
}

export interface FichaResumida {
  id: number;
  name: string;
}

export interface ParceiroResumido {
  id: number;
  nome: string;
  tipo: string;
  tipo_label: string;
  ativo: boolean;
}

export interface IndicacaoDaFicha {
  indicado_por: FichaResumida | null;
  indicacoes: FichaResumida[];
  parceiro: ParceiroResumido | null;
}

interface RespostaDeConsentimento {
  consentimentos: Consentimentos;
  pode_prospectar: boolean;
}

function useInvalidarFicha(clientId: number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["clientes-detail", clientId] });
    queryClient.invalidateQueries({ queryKey: ["clientes-linha-do-tempo", clientId] });
    // O cabeçalho da conversa mostra o aceite (feature 350): a conversa aberta relê.
    queryClient.invalidateQueries({ queryKey: ["conversas"] });
    queryClient.invalidateQueries({ queryKey: ["aniversarios"] });
  };
}

export interface MudancaDeNovidades {
  acao: "registrar" | "retirar";
  origem: string;
  referencia?: string;
}

/** Registra (POST) ou retira (DELETE) o aceite de novidades, com a origem da lista fechada. */
export function useMudarNovidades(clientId: number) {
  const invalidar = useInvalidarFicha(clientId);
  return useMutation({
    mutationFn: ({ acao, origem, referencia }: MudancaDeNovidades) =>
      apiFetch<RespostaDeConsentimento>(`/api/clientes/${clientId}/consentimentos/novidades`, {
        method: acao === "registrar" ? "POST" : "DELETE",
        body: JSON.stringify({ origem, referencia }),
      }),
    onSuccess: invalidar,
  });
}

export interface NovaCrianca {
  primeiro_nome: string;
  nascimento: string;
  aceite: boolean;
  origem: string;
}

/** Guarda o aniversário de uma criança (só com o aceite da responsável). */
export function useInserirCrianca(clientId: number) {
  const invalidar = useInvalidarFicha(clientId);
  return useMutation({
    mutationFn: (input: NovaCrianca) =>
      apiFetch<RespostaDeConsentimento>(`/api/clientes/${clientId}/criancas`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidar,
  });
}

/** Apaga nome e data da criança (o histórico guarda só a retirada). */
export function useRemoverCrianca(clientId: number) {
  const invalidar = useInvalidarFicha(clientId);
  return useMutation({
    mutationFn: (criancaId: number) =>
      apiFetch<RespostaDeConsentimento>(`/api/clientes/${clientId}/criancas/${criancaId}`, {
        method: "DELETE",
      }),
    onSuccess: invalidar,
  });
}

/** Define "Indicado por" e/ou o parceiro da ficha (só as chaves enviadas mudam). */
export function useDefinirIndicacao(clientId: number) {
  const invalidar = useInvalidarFicha(clientId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { indicado_por_id?: number | null; parceiro_id?: number | null }) =>
      apiFetch<IndicacaoDaFicha>(`/api/clientes/${clientId}/indicacao`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      invalidar();
      // A ficha de quem indicou ganha a linha em "Indicou"; a lista de parceiros, a contagem.
      queryClient.invalidateQueries({ queryKey: ["clientes-detail"] });
      queryClient.invalidateQueries({ queryKey: ["parceiros"] });
    },
  });
}

// ── Parceiros ───────────────────────────────────────────────────────────────────────────────────

export interface Parceiro {
  id: number;
  nome: string;
  tipo: string;
  tipo_label: string;
  contato: string | null;
  telefone: string | null;
  email: string | null;
  /** Texto decimal ("10.00"): a comissão declarada em %. */
  comissao_percentual: string;
  observacao: string | null;
  ativo: boolean;
  clientes: number;
}

export interface ParceirosResposta {
  items: Parceiro[];
  tipos: { valor: string; rotulo: string }[];
  flags: { pode_editar: boolean };
}

export function useParceiros(incluirInativos = false) {
  return useQuery<ParceirosResposta>({
    queryKey: ["parceiros", incluirInativos],
    queryFn: () =>
      apiFetch<ParceirosResposta>(`/api/parceiros${incluirInativos ? "?inativos=1" : ""}`),
  });
}

export interface DadosDoParceiro {
  nome: string;
  tipo: string;
  contato: string;
  telefone: string;
  email: string;
  comissao_percentual: string;
  observacao: string;
}

export function useSalvarParceiro() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dados }: { id: number | null; dados: Partial<DadosDoParceiro> & { ativo?: boolean } }) =>
      apiFetch<Parceiro>(id ? `/api/parceiros/${id}` : "/api/parceiros", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(dados),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["parceiros"] }),
  });
}

// ── Aniversários ────────────────────────────────────────────────────────────────────────────────

export interface Aniversario {
  crianca_id: number;
  primeiro_nome: string;
  data: string;
  dias: number;
  idade: number;
  cliente: { id: number; name: string; phone_display: string };
}

export function useAniversarios(dias = 60) {
  return useQuery<{ items: Aniversario[]; dias: number }>({
    queryKey: ["aniversarios", dias],
    queryFn: () => apiFetch(`/api/clientes/aniversarios?dias=${dias}`),
  });
}

// ── Pós-evento ──────────────────────────────────────────────────────────────────────────────────

export type SituacaoDoPosEvento = "pendente" | "copiado" | "conversa";

export interface ItemDoPosEvento {
  event_id: number;
  titulo: string;
  start_at: string | null;
  cliente: FichaResumida | null;
  situacao: SituacaoDoPosEvento;
  registrado_em: string | null;
  avaliacao_recebida: boolean;
}

export interface PreviaDoPosEvento {
  mensagem: string;
  link_avaliacao: string;
  fotos_url: string | null;
  situacao: SituacaoDoPosEvento;
  registrado_em: string | null;
  avaliacao_recebida: boolean;
  conversa: { pode_enviar: boolean; motivo: string | null; conversa_id: number | null };
}

export function usePosEventoLista() {
  return useQuery<{ items: ItemDoPosEvento[] }>({
    queryKey: ["pos-evento"],
    queryFn: () => apiFetch("/api/pos-evento"),
  });
}

/** A prévia: refaz a cada link de fotos (com debounce na tela). */
export function usePosEvento(eventId: number | null, fotosUrl: string) {
  const fotos = fotosUrl.trim();
  return useQuery<PreviaDoPosEvento>({
    queryKey: ["pos-evento", eventId, fotos],
    queryFn: () =>
      apiFetch(
        `/api/events/${eventId}/pos-evento${fotos ? `?fotos_url=${encodeURIComponent(fotos)}` : ""}`,
      ),
    enabled: eventId !== null,
    placeholderData: (anterior) => anterior,
    retry: false,
  });
}

export function useRegistrarPosEvento(eventId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { canal: "copiado" | "conversa"; fotos_url?: string }) =>
      apiFetch<{ situacao: SituacaoDoPosEvento; registrado_em: string; fotos_url: string | null }>(
        `/api/events/${eventId}/pos-evento`,
        { method: "POST", body: JSON.stringify(input) },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pos-evento"] });
      queryClient.invalidateQueries({ queryKey: ["conversas"] });
    },
  });
}

/** "12/03/2021" a partir de "2021-03-12", pelo texto (data-só lida como UTC voltaria um dia). */
export function dataCurta(iso: string | null): string {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "";
}
