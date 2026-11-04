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

/** Pessoa da equipe (responsável, autor de nota, destino de transferência) — feature 328. */
export interface Pessoa {
  id: number;
  nome: string;
}

export type FiltroDaLista = "todas" | "minhas" | "sem_responsavel";
/** Feature 330: o canal da conversa e a janela de resposta (no Instagram, até 7 dias com a marca humana). */
export type Canal = "whatsapp" | "instagram";
export type Janela = "aberta" | "humana" | "fechada";
export type AcaoDoResponsavel = "assumir" | "transferir" | "devolver";

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
  /** Feature 328 (opcionais: o payload da 325 não os tinha — armadilha 21). */
  responsavel?: Pessoa | null;
  /** Falso quando o responsável perdeu o papel ou o acesso: qualquer um pode assumir. */
  responsavel_ativo?: boolean;
  /** UTC; a primeira mensagem da cliente ainda sem resposta. */
  aguardando_desde?: string | null;
  /** Feature 330: o @usuário do Instagram (sem a arroba) e a janela de resposta. */
  usuario?: string | null;
  janela?: Janela;
  /** Feature 333: a ficha (ou a falta dela) foi escolhida à mão; a ligação automática não age. */
  ficha_manual?: boolean;
}

export interface Nota {
  id: number;
  texto: string;
  autor: Pessoa | null;
  momento: string | null;
}

export interface RespostaRapida {
  id: number;
  titulo: string;
  atalho: string | null;
  texto: string;
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
  /** Feature 330: o link de story, publicação ou reels que a cliente mandou pelo Instagram. */
  link?: string | null;
}

export interface ListaDeConversas {
  configurado: boolean;
  envio_travado: boolean;
  poll_segundos?: number;
  canais_ligados?: Canal[];
  conversas: ConversaResumo[];
  proximo: string | null;
}

export interface ConversaAbertaResposta {
  conversa: ConversaResumo;
  mensagens: Mensagem[];
  tem_mais: boolean;
  notas?: Nota[];
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

function parametrosDaLista(busca: string, filtro: FiltroDaLista, canal: Canal | null): URLSearchParams {
  const params = new URLSearchParams();
  if (busca) params.set("busca", busca);
  if (filtro !== "todas") params.set("filtro", filtro);
  if (canal) params.set("canal", canal);
  return params;
}

export function useConversas(busca: string, filtro: FiltroDaLista = "todas", canal: Canal | null = null) {
  return useQuery<ListaDeConversas>({
    queryKey: [...CHAVE, "lista", busca, filtro, canal],
    queryFn: () => {
      const params = parametrosDaLista(busca, filtro, canal).toString();
      return apiFetch<ListaDeConversas>(`/api/conversas${params ? `?${params}` : ""}`);
    },
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
export function useConversasAnteriores(
  busca: string,
  filtro: FiltroDaLista,
  canal: Canal | null,
  cursorInicial: string | null,
) {
  return useInfiniteQuery({
    queryKey: [...CHAVE, "lista-anteriores", busca, filtro, canal, cursorInicial],
    queryFn: ({ pageParam }) => {
      const params = parametrosDaLista(busca, filtro, canal);
      params.set("antes", pageParam);
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

// ── Equipe na caixa (feature 328) ────────────────────────────────────────────────────────────────

/** Quem pode receber uma conversa transferida (Comercial e Superadmin ativos). */
export function useEquipe(ativo: boolean) {
  return useQuery<{ equipe: Pessoa[] }>({
    queryKey: [...CHAVE, "equipe"],
    queryFn: () => apiFetch<{ equipe: Pessoa[] }>("/api/conversas/equipe"),
    enabled: ativo,
    staleTime: 5 * 60_000,
  });
}

export interface MudancaDeResponsavel {
  acao: AcaoDoResponsavel;
  responsavel_id?: number;
}

/** Assumir, transferir ou devolver. Atualiza a lista (filtros "Minhas"/"Sem responsável") e a conversa. */
export function useDefinirResponsavel(conversaId: number) {
  const atualizar = useAtualizarAposEnvio(conversaId);
  return useMutation({
    mutationFn: (corpo: MudancaDeResponsavel) =>
      apiFetch<{ conversa: ConversaResumo }>(`/api/conversas/${conversaId}/responsavel`, {
        method: "POST",
        body: JSON.stringify(corpo),
      }),
    onSettled: atualizar,
  });
}

export function useGravarNota(conversaId: number) {
  const atualizar = useAtualizarAposEnvio(conversaId);
  return useMutation({
    mutationFn: (texto: string) =>
      apiFetch<{ nota: Nota }>(`/api/conversas/${conversaId}/notas`, {
        method: "POST",
        body: JSON.stringify({ texto }),
      }),
    onSuccess: atualizar,
  });
}

const CHAVE_DAS_RESPOSTAS = [...CHAVE, "respostas-rapidas"] as const;

export function useRespostasRapidas(ativo = true) {
  return useQuery<{ respostas: RespostaRapida[] }>({
    queryKey: CHAVE_DAS_RESPOSTAS,
    queryFn: () => apiFetch<{ respostas: RespostaRapida[] }>("/api/conversas/respostas-rapidas"),
    enabled: ativo,
    staleTime: 60_000,
  });
}

export interface DadosDaResposta {
  titulo: string;
  atalho: string | null;
  texto: string;
}

function useAtualizarRespostas() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: CHAVE_DAS_RESPOSTAS });
}

export function useSalvarResposta() {
  const atualizar = useAtualizarRespostas();
  return useMutation({
    mutationFn: ({ id, ...dados }: DadosDaResposta & { id: number | null }) =>
      apiFetch<{ resposta: RespostaRapida }>(
        id === null ? "/api/conversas/respostas-rapidas" : `/api/conversas/respostas-rapidas/${id}`,
        { method: id === null ? "POST" : "PATCH", body: JSON.stringify(dados) },
      ),
    onSuccess: atualizar,
  });
}

export function useExcluirResposta() {
  const atualizar = useAtualizarRespostas();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/conversas/respostas-rapidas/${id}`, { method: "DELETE" }),
    onSuccess: atualizar,
  });
}

/**
 * Troca `{nome}` pelo primeiro nome do contato (FR-011). Sem nome, o marcador sai junto com a
 * vírgula e o espaço que sobrariam: "Olá, {nome}! Segue" vira "Olá! Segue".
 */
export function aplicarNome(texto: string, nomeDoContato: string | null | undefined): string {
  const primeiro = (nomeDoContato ?? "").trim().split(/\s+/)[0] ?? "";
  // Telefone não é nome: "+55 11 9…" não vira "Olá, +55!".
  const nome = /\p{L}/u.test(primeiro) ? primeiro : "";
  if (nome) return texto.replace(/\{nome\}/g, nome);
  // Só a vizinhança do marcador: "Olá, {nome}!" → "Olá!"; "{nome}, tudo bem?" → "Tudo bem?";
  // "Oi {nome}!" → "Oi!". O resto do texto não muda.
  const semNome = texto
    .replace(/\{nome\}\s*,\s*/g, "")
    .replace(/,\s*\{nome\}/g, "")
    .replace(/\s*\{nome\}/g, "");
  const comecavaComNome = /^\s*\{nome\}/.test(texto);
  return comecavaComNome ? semNome.replace(/^\s*(\p{Ll})/u, (_, letra: string) => letra.toUpperCase()) : semNome;
}

/** O limite do texto no Instagram é de 1.000 BYTES em UTF-8 (acentos e emojis contam mais). */
export const TEXTO_MAXIMO_NO_INSTAGRAM_BYTES = 1000;
export const TEXTO_LONGO_NO_INSTAGRAM =
  "A mensagem passa do limite do Instagram. Encurte o texto (acentos e emojis contam mais).";

export function passaDoLimiteDoInstagram(texto: string): boolean {
  return new TextEncoder().encode(texto).length > TEXTO_MAXIMO_NO_INSTAGRAM_BYTES;
}

/** O nome que entra no `{nome}` das respostas rápidas: no Instagram, só o nome de verdade do perfil
 * ou da ficha — nunca o "Contato do Instagram" nem o @usuário (feature 330). */
export function nomeParaResposta(conversa: ConversaResumo): string | null {
  if (conversa.canal === "instagram") return conversa.cliente?.nome ?? conversa.nome_perfil ?? null;
  return conversa.nome;
}

/** O que aparece no lugar do telefone: o @usuário no Instagram, o telefone no WhatsApp. */
export function contatoLegivel(conversa: ConversaResumo): string | null {
  if (conversa.canal === "instagram") return conversa.usuario ? `@${conversa.usuario}` : null;
  return conversa.telefone_legivel;
}

/** Tela de toque (celular): lá o Enter quebra a linha, porque o teclado não tem Shift. */
export function ehToque(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches === true;
}

/** Há quanto tempo a cliente espera, para a lista: "há 20 min", "há 2 h". Urgente a partir de 15 min. */
export function tempoDeEspera(iso: string | null | undefined, agora: number): { texto: string; urgente: boolean } | null {
  if (!iso) return null;
  const minutos = Math.max(0, Math.floor((agora - new Date(iso).getTime()) / 60_000));
  const texto = minutos < 60 ? `há ${minutos} min` : `há ${Math.floor(minutos / 60)} h`;
  return { texto, urgente: minutos >= 15 };
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

// ── Feature 333: orçamento, ficha e formulário pela conversa ────────────────────────────────────

/** A ficha escolhida para a conversa: uma existente ou uma nova (nome e telefone). */
export type EscolhaDaFicha = { client_id: number; nome: string } | { nome: string; telefone: string };

export interface EnvioDoOrcamentoInput {
  conversaId: number;
  orcamento_id: number;
  chave_envio: string;
  /** Só quando a conversa não tem ficha e a ligação automática não serve (Instagram, ficha removida). */
  cliente?: EscolhaDaFicha;
  /** Só o PDF (o reenvio do PDF que a Meta recusou, sem mandar a mensagem de novo). */
  somente_pdf?: boolean;
}

export interface EnvioDoOrcamentoResposta {
  envio: { id: number; orcamento_id: number; conversa_id: number; quando: string | null };
  mensagens: Mensagem[];
  conversa: ConversaResumo;
}

function corpoDaFicha(escolha: EscolhaDaFicha): Record<string, unknown> {
  return "client_id" in escolha
    ? { client_id: escolha.client_id }
    : { nome: escolha.nome, telefone: escolha.telefone };
}

function useAtualizarAposCostura() {
  const queryClient = useQueryClient();
  return (conversaId: number) => {
    void queryClient.invalidateQueries({ queryKey: [...CHAVE, "aberta", conversaId] });
    void queryClient.invalidateQueries({ queryKey: [...CHAVE, "lista"] });
    void queryClient.invalidateQueries({ queryKey: ["orcamento-historico"] });
    void queryClient.invalidateQueries({ queryKey: ["orcamento-historico-detalhe"] });
    // O texto do formulário leva o nome da ficha: trocou a ficha, troca o texto.
    void queryClient.invalidateQueries({ queryKey: [...CHAVE, "formularios", conversaId] });
  };
}

/** A mensagem pronta e o PDF do orçamento pela conversa (FR-003). A chave é da tentativa, não do clique. */
export function useEnviarOrcamento() {
  const atualizar = useAtualizarAposCostura();
  return useMutation({
    mutationFn: ({ conversaId, cliente, ...corpo }: EnvioDoOrcamentoInput) =>
      apiFetch<EnvioDoOrcamentoResposta>(`/api/conversas/${conversaId}/orcamento`, {
        method: "POST",
        body: JSON.stringify(cliente ? { ...corpo, cliente: corpoDaFicha(cliente) } : corpo),
      }),
    onSettled: (_resposta, _erro, variaveis) => atualizar(variaveis.conversaId),
  });
}

/** Ligar, trocar ou criar a ficha da conversa à mão (FR-009). */
export function useLigarFicha(conversaId: number) {
  const atualizar = useAtualizarAposCostura();
  return useMutation({
    mutationFn: (escolha: EscolhaDaFicha) =>
      apiFetch<{ conversa: ConversaResumo; reaproveitada: boolean }>(`/api/conversas/${conversaId}/ficha`, {
        method: "POST",
        body: JSON.stringify(corpoDaFicha(escolha)),
      }),
    onSettled: () => atualizar(conversaId),
  });
}

/** "Remover vínculo": a ficha continua na base; a conversa fica sem ela. */
export function useRemoverFicha(conversaId: number) {
  const atualizar = useAtualizarAposCostura();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ conversa: ConversaResumo }>(`/api/conversas/${conversaId}/ficha`, { method: "DELETE" }),
    onSettled: () => atualizar(conversaId),
  });
}

export interface FormularioDaConversa {
  tipo: string;
  titulo: string;
  link: string;
  texto: string;
}

/** Os formulários públicos com o texto pronto para esta conversa (FR-010). */
export function useFormulariosDaConversa(conversaId: number, ativo: boolean) {
  return useQuery({
    queryKey: [...CHAVE, "formularios", conversaId],
    queryFn: () =>
      apiFetch<{ formularios: FormularioDaConversa[] }>(`/api/conversas/${conversaId}/formularios`),
    enabled: ativo,
    staleTime: 5 * 60_000,
  });
}

/**
 * A conversa que precisa da ficha escolhida pelo vendedor no envio do orçamento: sem ficha e sem o
 * telefone para a ligação automática (Instagram), ou com a ficha removida à mão (research R3).
 */
export function precisaEscolherFicha(conversa: ConversaResumo): boolean {
  if (conversa.cliente) return false;
  return conversa.canal === "instagram" || Boolean(conversa.ficha_manual) || !conversa.telefone;
}
