import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";

/**
 * Conversas (feature 325) — WhatsApp dentro da Plataforma.
 *
 * Contrato em `specs/325-crm-whatsapp-fundacao/contracts/api.md`. Os horários vêm com `+00:00`
 * (UTC explícito), diferente de `start_at` dos eventos (parede de São Paulo, sem fuso): aqui
 * `new Date(iso)` está CERTO, e a formatação fixa o fuso de São Paulo (`horaDaMensagem`).
 *
 * A tela não tem websocket (o proxy Node não passa upgrade): lista e conversa aberta se atualizam
 * por consulta periódica curta, só com a aba visível. O intervalo vem do servidor (`poll_segundos`).
 */

export type Direcao = "recebida" | "enviada";
export type Situacao = "recebida" | "pendente" | "enviada" | "entregue" | "lida" | "falhou";
export type Origem = "contato" | "plataforma" | "celular" | "outro";
export type TipoMensagem =
  | "texto"
  | "imagem"
  | "audio"
  | "video"
  | "documento"
  | "figurinha"
  | "localizacao"
  | "contato"
  | "reacao"
  | "interativa"
  | "modelo"
  | "outro";

export interface ClienteDaConversa {
  id: number;
  nome: string;
}

export interface ConversaResumo {
  id: number;
  canal: string;
  nome: string;
  nome_perfil: string | null;
  telefone: string | null;
  telefone_legivel: string | null;
  cliente: ClienteDaConversa | null;
  ultima_previa: string | null;
  ultima_mensagem_em: string | null;
  nao_lidas: number;
  janela_aberta: boolean;
  janela_fecha_em: string | null;
}

export interface MidiaDaMensagem {
  id: number;
  estado: "pendente" | "guardada" | "falhou";
  mime: string | null;
  tamanho: number | null;
  nome: string | null;
  url: string | null;
}

export interface Mensagem {
  id: number;
  direcao: Direcao;
  tipo: TipoMensagem;
  texto: string | null;
  momento: string | null;
  situacao: Situacao;
  autor: { id: number; nome: string } | null;
  origem: Origem;
  modelo_nome: string | null;
  erro: { codigo: number | null; motivo: string } | null;
  midia: MidiaDaMensagem | null;
}

export interface ListaDeConversas {
  configurado: boolean;
  envio_travado: boolean;
  poll_segundos?: number;
  conversas: ConversaResumo[];
  proximo: string | null;
}

export interface ConversaAbertaResposta {
  conversa: ConversaResumo;
  mensagens: Mensagem[];
  tem_mais: boolean;
}

export interface ModeloAprovado {
  nome: string;
  idioma: string;
  categoria: string | null;
  texto: string;
  variaveis: number;
  nomes_das_variaveis: string[];
}

const CHAVE = ["conversas"] as const;
const POLL_PADRAO_S = 5;

/** Intervalo da lista (o servidor manda) e da conversa aberta (um pouco mais curto). */
export function intervaloDaLista(lista: ListaDeConversas | undefined): number {
  return Math.max(2, lista?.poll_segundos ?? POLL_PADRAO_S) * 1000;
}

export function useConversas(busca: string) {
  return useQuery<ListaDeConversas>({
    queryKey: [...CHAVE, "lista", busca],
    queryFn: () =>
      apiFetch<ListaDeConversas>(`/api/conversas${busca ? `?busca=${encodeURIComponent(busca)}` : ""}`),
    refetchInterval: (query) => intervaloDaLista(query.state.data),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    placeholderData: (anterior) => anterior,
  });
}

export function useConversa(id: number | null, intervaloMs: number) {
  return useQuery<ConversaAbertaResposta>({
    queryKey: [...CHAVE, "aberta", id],
    queryFn: () => apiFetch<ConversaAbertaResposta>(`/api/conversas/${id}`),
    enabled: id !== null,
    refetchInterval: Math.max(2000, intervaloMs - 1000),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

/**
 * Mensagens anteriores (rolar para cima) — página por cursor `antes=<id>`.
 *
 * O cursor inicial é FIXADO no clique em "Carregar anteriores" (`cursorInicial`), não a primeira
 * mensagem do momento: com ela na chave, cada mensagem nova trocava a chave e jogava fora as páginas
 * já carregadas. O servidor ordena por `(momento, id)`, então não há buraco nem repetição.
 */
export function useMensagensAnteriores(id: number | null, cursorInicial: number | null) {
  return useInfiniteQuery({
    queryKey: [...CHAVE, "anteriores", id, cursorInicial],
    queryFn: ({ pageParam }) =>
      apiFetch<ConversaAbertaResposta>(`/api/conversas/${id}?antes=${pageParam}`),
    initialPageParam: cursorInicial ?? 0,
    getNextPageParam: (ultima) => (ultima.tem_mais ? ultima.mensagens[0]?.id : undefined),
    enabled: id !== null && cursorInicial !== null,
  });
}

/** Conversas mais antigas que a primeira página (sem polling: só o topo da lista muda sozinho). */
export function useConversasAnteriores(busca: string, cursorInicial: string | null) {
  return useInfiniteQuery({
    queryKey: [...CHAVE, "lista-anteriores", busca, cursorInicial],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ antes: pageParam });
      if (busca) params.set("busca", busca);
      return apiFetch<ListaDeConversas>(`/api/conversas?${params.toString()}`);
    },
    initialPageParam: cursorInicial ?? "",
    getNextPageParam: (ultima) => ultima.proximo ?? undefined,
    enabled: cursorInicial !== null,
  });
}

export function useModelos(ativo: boolean) {
  return useQuery<{ modelos: ModeloAprovado[] }>({
    queryKey: [...CHAVE, "modelos"],
    queryFn: () => apiFetch<{ modelos: ModeloAprovado[] }>("/api/conversas/modelos"),
    enabled: ativo,
    staleTime: 60_000,
    retry: false,
  });
}

/** Uma chave nova por tentativa: o mesmo clique repetido não manda duas vezes (FR-018). */
export function novaChaveDeEnvio(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

function useAtualizarAposEnvio(conversaId: number) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: [...CHAVE, "aberta", conversaId] });
    void queryClient.invalidateQueries({ queryKey: [...CHAVE, "lista"] });
  };
}

export interface EnvioDeTexto {
  texto: string;
  chave_envio: string;
}

function mensagemOtimista(texto: string): Mensagem {
  return {
    id: -Date.now(),
    direcao: "enviada",
    tipo: "texto",
    texto,
    momento: new Date().toISOString(),
    situacao: "pendente",
    autor: null,
    origem: "plataforma",
    modelo_nome: null,
    erro: null,
    midia: null,
  };
}

/**
 * Texto com envio otimista: a mensagem aparece na hora com o relógio (`pendente`) — a resposta da
 * Meta pode levar até 30 s — e é trocada pela gravada quando o servidor responde. No erro, some.
 */
export function useEnviarTexto(conversaId: number) {
  const queryClient = useQueryClient();
  const atualizar = useAtualizarAposEnvio(conversaId);
  const chave = [...CHAVE, "aberta", conversaId];
  return useMutation({
    mutationFn: (corpo: EnvioDeTexto) =>
      apiFetch<{ mensagem: Mensagem }>(`/api/conversas/${conversaId}/mensagens`, {
        method: "POST",
        body: JSON.stringify(corpo),
      }),
    onMutate: async (corpo) => {
      await queryClient.cancelQueries({ queryKey: chave });
      const anterior = queryClient.getQueryData<ConversaAbertaResposta>(chave);
      if (anterior) {
        queryClient.setQueryData<ConversaAbertaResposta>(chave, {
          ...anterior,
          mensagens: [...anterior.mensagens, mensagemOtimista(corpo.texto)],
        });
      }
      return { anterior };
    },
    onError: (_erro, _corpo, contexto) => {
      if (contexto?.anterior) queryClient.setQueryData(chave, contexto.anterior);
    },
    onSettled: atualizar,
  });
}

export interface EnvioDeArquivo {
  arquivo: File;
  legenda: string;
  chave_envio: string;
}

export function useEnviarArquivo(conversaId: number) {
  const atualizar = useAtualizarAposEnvio(conversaId);
  return useMutation({
    mutationFn: ({ arquivo, legenda, chave_envio }: EnvioDeArquivo) => {
      const form = new FormData();
      form.append("arquivo", arquivo);
      form.append("chave_envio", chave_envio);
      if (legenda) form.append("legenda", legenda);
      return apiFetch<{ mensagem: Mensagem }>(`/api/conversas/${conversaId}/mensagens`, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: atualizar,
  });
}

export interface EnvioDeModelo {
  nome: string;
  idioma: string;
  variaveis: string[];
  chave_envio: string;
}

export function useEnviarModelo(conversaId: number) {
  const atualizar = useAtualizarAposEnvio(conversaId);
  return useMutation({
    mutationFn: (corpo: EnvioDeModelo) =>
      apiFetch<{ mensagem: Mensagem }>(`/api/conversas/${conversaId}/modelo`, {
        method: "POST",
        body: JSON.stringify(corpo),
      }),
    onSuccess: atualizar,
  });
}

export function useMarcarLida() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversaId: number) =>
      apiFetch<void>(`/api/conversas/${conversaId}/lida`, { method: "POST", body: "{}" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: [...CHAVE, "lista"] }),
  });
}

/** O `codigo` da recusa (`janela_fechada`, `envio_travado`, `nao_configurado`) — nunca a mensagem. */
export function codigoDaRecusa(erro: unknown): string | null {
  if (!(erro instanceof ApiRequestError)) return null;
  const codigo = erro.details.codigo;
  return typeof codigo === "string" ? codigo : null;
}

export function mensagemDoErro(erro: unknown, reserva: string): string {
  return erro instanceof ApiRequestError && erro.message ? erro.message : reserva;
}

const FORMATO_HORA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  hour: "2-digit",
  minute: "2-digit",
});
const FORMATO_DIA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
});
const FORMATO_DATA_LONGA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  weekday: "long",
  day: "numeric",
  month: "long",
});

function diaEmSaoPaulo(data: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(data);
}

/** "14:32" no dia de hoje; "29/10" nos outros dias — horário de São Paulo. */
export function horaNaLista(iso: string | null): string {
  if (!iso) return "";
  const data = new Date(iso);
  return diaEmSaoPaulo(data) === diaEmSaoPaulo(new Date()) ? FORMATO_HORA.format(data) : FORMATO_DIA.format(data);
}

/** "14:32" — horário de São Paulo. */
export function horaDaMensagem(iso: string | null): string {
  return iso ? FORMATO_HORA.format(new Date(iso)) : "";
}

/** Chave do dia (AAAA-MM-DD em São Paulo) para separar as mensagens por dia. */
export function diaDaMensagem(iso: string | null): string {
  return iso ? diaEmSaoPaulo(new Date(iso)) : "";
}

/** "Hoje", "Ontem" ou "quinta-feira, 29 de outubro". */
export function rotuloDoDia(iso: string | null): string {
  if (!iso) return "";
  const dia = diaDaMensagem(iso);
  const hoje = diaEmSaoPaulo(new Date());
  const ontem = diaEmSaoPaulo(new Date(Date.now() - 86_400_000));
  if (dia === hoje) return "Hoje";
  if (dia === ontem) return "Ontem";
  return FORMATO_DATA_LONGA.format(new Date(iso));
}
