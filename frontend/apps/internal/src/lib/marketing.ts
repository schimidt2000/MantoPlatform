import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Módulo de Gestão de Marketing e Frequência (feature 204) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/marketing/*`: as duas telas (`/marketing/painel` e
 * `/marketing/metas`) e o Dialog de edição consomem daqui, nenhuma monta `fetch` por conta
 * própria (Princípio I).
 */

/** Colunas do Kanban, na ordem do fluxo de produção. */
export type MarketingStatus = "ideia" | "producao" | "revisao" | "pronto" | "agendado" | "publicado";

export const MARKETING_STATUSES: MarketingStatus[] = [
  "ideia",
  "producao",
  "revisao",
  "pronto",
  "agendado",
  "publicado",
];

export const MARKETING_STATUS_LABELS: Record<MarketingStatus, string> = {
  ideia: "Ideia",
  producao: "Produção",
  revisao: "Revisão",
  pronto: "Pronto",
  agendado: "Agendado",
  publicado: "Publicado",
};

/** Tom do `Badge`/coluna de cada status — paleta do design system, zero cor hardcoded. */
export const MARKETING_STATUS_TONES: Record<
  MarketingStatus,
  "neutral" | "gold" | "blue" | "accent" | "green"
> = {
  ideia: "neutral",
  producao: "gold",
  revisao: "blue",
  pronto: "green",
  agendado: "accent",
  publicado: "green",
};

/** Emoji de cada coluna — leitura de relance do Kanban, sem depender só da cor. */
export const MARKETING_STATUS_ICONS: Record<MarketingStatus, string> = {
  ideia: "💡",
  producao: "🎬",
  revisao: "👀",
  pronto: "✅",
  agendado: "📅",
  publicado: "🚀",
};

/** Situação do espaço de revisão vinculado, derivada dos materiais dentro dele. */
export type ReviewSpaceStatus = "sem_material" | "em_revisao" | "precisa_ajustes" | "aprovado";

export const REVIEW_SPACE_STATUS_LABELS: Record<ReviewSpaceStatus, string> = {
  sem_material: "Sem material",
  em_revisao: "Em revisão",
  precisa_ajustes: "Precisa de ajustes",
  aprovado: "Aprovado",
};

export const REVIEW_SPACE_STATUS_TONES: Record<
  ReviewSpaceStatus,
  "neutral" | "blue" | "red" | "green"
> = {
  sem_material: "neutral",
  em_revisao: "blue",
  precisa_ajustes: "red",
  aprovado: "green",
};

/** Tema do catálogo vinculado (subset: o suficiente para a miniatura quadrada). */
export interface MarketingCatalogItemRef {
  id: number;
  name: string;
  /** Capa do Tema; passar por `assetUrl()` antes de exibir. */
  cover_url: string | null;
  is_active: boolean;
  /** Feature 345 — opcionais: backend e bundle ficam em versões diferentes durante o deploy. */
  licenca_origem?: LicencaOrigem;
  liberado_anuncio?: LiberadoAnuncio;
}

export interface MarketingAssigneeRef {
  id: number;
  name: string;
  /** Foto de perfil; passar por `assetUrl()` antes de exibir. */
  photo_url: string | null;
}

export interface MarketingReviewSpaceRef {
  id: number;
  title: string;
  asset_count: number;
  approved_count: number;
  status: ReviewSpaceStatus;
}

export interface MarketingPost {
  id: number;
  title: string;
  status: MarketingStatus;
  /** `YYYY-MM-DD` ou `null`. */
  deadline_date: string | null;
  publish_date: string | null;
  platform: string | null;
  drive_folder_url: string | null;
  /** Link do post publicado — chave do cruzamento com as métricas do auditor (feature 256). */
  permalink: string | null;
  notes: string | null;
  assignee_id: number | null;
  assignee: MarketingAssigneeRef | null;
  catalog_item_ids: number[];
  catalog_items: MarketingCatalogItemRef[];
  review_space_id: number | null;
  review_space: MarketingReviewSpaceRef | null;
  // Feature 345 — o card vira pedido de criativo. Tudo opcional (`docs/00` §6 item 21).
  tipo?: MarketingPostTipo;
  frente?: string | null;
  formato?: string | null;
  briefing_objetivo?: string | null;
  briefing_mostrar?: string | null;
  briefing_letreiro?: string | null;
  origem?: "pessoa" | "rotina";
  /** Feature 351: o ângulo da peça (agrupa o funil por conceito). */
  conceito?: string | null;
  anuncios?: MarketingPostAnuncio[];
  resultado?: MarketingPostResultado | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MarketingPostsResponse {
  items: MarketingPost[];
  statuses: MarketingStatus[];
  plataformas: string[];
  /** Feature 345: slug → nome. */
  frentes?: Record<string, string>;
  formatos?: Record<string, string>;
}

// ── Feature 345: painel de comando ──────────────────────────────────────────

export type MarketingPostTipo = "post" | "anuncio";
export type LicencaOrigem = "autoral" | "licenciado" | "nao_classificado";
export type LiberadoAnuncio = "sim" | "nao" | "nao_decidido";

export const LICENCA_ORIGEM_LABELS: Record<LicencaOrigem, string> = {
  autoral: "Autoral",
  licenciado: "Licenciado",
  nao_classificado: "Não classificado",
};

export const LIBERADO_LABELS: Record<LiberadoAnuncio, string> = {
  sim: "Liberado",
  nao: "Não liberado",
  nao_decidido: "Não decidido",
};

/**
 * Anúncio ligado ao card. Feature 351: `no_ar` = gastou num dos últimos dias com leitura da plataforma
 * (`null` = sem leitura); `ultimo_gasto_em` = o último dia com gasto.
 */
export interface MarketingPostAnuncio {
  platform: string;
  ad_id: string;
  no_ar?: boolean | null;
  ultimo_gasto_em?: string | null;
}

/** Resultado somado dos anúncios ligados ao card (dinheiro em string decimal). */
export interface MarketingPostResultado {
  spend: string;
  conversations: number;
  impressions: number;
  clicks: number;
  custo_conversa: string | null;
  // Feature 351 — o que a peça trouxe de verdade (CRM e venda atribuída). Opcionais.
  custo_conversa_real?: string | null;
  conversas_reais?: number;
  orcamentos?: number;
  eventos?: number;
  vendas?: number;
  faturamento?: string;
  anuncios_no_ar?: number;
  ultima_leitura?: string | null;
}

export type FrenteEstado = "ok" | "acima_do_teto" | "sem_venda" | "sem_gasto";

export interface DesempenhoFrente {
  slug: string;
  nome: string;
  gasto: string;
  conversas: number;
  cadastros: number;
  vendas: number;
  vendas_cliente_novo: number;
  faturamento: string;
  custo_venda: string | null;
  teto: string | null;
  estado: FrenteEstado;
  // Feature 351 — venda atribuída ao lado do misto, e o mês corrente contra a meta. Opcionais.
  vendas_atribuidas?: number;
  faturamento_atribuido?: string;
  custo_venda_atribuida?: string | null;
  custo_venda_atribuida_desconto?: string | null;
  estado_atribuido?: FrenteEstado;
  mes_corrente?: FrenteMesCorrente;
}

/** O mês corrente de uma frente: vendas (todas) e gasto até hoje contra a meta e a verba do mês. */
export interface FrenteMesCorrente {
  mes: number;
  meta_vendas: number | null;
  verba: string | null;
  foco: string | null;
  vendas: number;
  gasto: string;
}

/** A regra da atribuição declarada na tela (feature 351). */
export interface AtribuicaoRegra {
  janela_dias: number;
  /** Fração em string decimal ("0.50"). */
  incrementalidade: string;
  desde: string;
  /** O período começa antes de `desde`: a atribuição cobre só parte dele. */
  parcial: boolean;
}

export interface DesempenhoAtribuicao extends AtribuicaoRegra {
  sem_frente: { vendas: number; faturamento: string };
}

export interface CampanhaSemFrente {
  platform: string;
  campaign_id: string;
  campaign_name: string;
  gasto: string;
}

export interface PlataformaSituacao {
  platform: string;
  ultima_data: string | null;
  situacao: "ok" | "atrasada" | "sem_conexao";
}

export interface FrentesConfig {
  frentes: {
    slug: string;
    nome: string;
    teto: string | null;
    teto_padrao: string | null;
    base_teto: string;
    teto_editado: boolean;
    /** Feature 351: padrão do mês (o calendário vence mês a mês). */
    meta_vendas_mes?: number | null;
    verba_mes?: string | null;
  }[];
  responsaveis: { foto: MarketingAssigneeRef | null; video: MarketingAssigneeRef | null };
  pode_editar: boolean;
}

export interface TemaLicenca {
  id: number;
  name: string;
  cover_url: string | null;
  is_active: boolean;
  licenca_origem: LicencaOrigem;
  liberado_anuncio: LiberadoAnuncio;
  licenca_sugestao: "autoral" | "licenciado" | null;
  licenca_sugestao_motivo: string | null;
  licenca_por: MarketingAssigneeRef | null;
  licenca_em: string | null;
}

export interface TemasLicencaResponse {
  items: TemaLicenca[];
  contagem: Record<LicencaOrigem, number>;
  com_sugestao: number;
  pode_liberar_licenciado: boolean;
  /** Feature 351: paginação no servidor (50 por página). */
  total?: number;
  pagina?: number;
  paginas?: number;
  por_pagina?: number;
}

export type PropostaSituacao = "pendente" | "aprovada" | "recusada" | "expirada" | "executada" | "falhou";

export interface Proposta {
  id: number;
  tipo: "ativar" | "pausar" | "verba" | "publico";
  platform: string;
  alvo_tipo: "campanha" | "conjunto" | "anuncio";
  alvo_id: string;
  alvo_nome: string | null;
  valor_antes: string | null;
  valor_depois: string | null;
  custo_dia_estimado: string | null;
  motivo: string;
  evidencia: string | null;
  post_id: number | null;
  post_titulo: string | null;
  situacao: PropostaSituacao;
  criada_em: string | null;
  decidida_por: MarketingAssigneeRef | null;
  decidida_em: string | null;
  decisao_obs: string | null;
  executada_em: string | null;
  resultado_execucao: string | null;
  expira_em: string | null;
  // Feature 351 — número, frente, teto e impacto no mês. Opcionais.
  frente?: string | null;
  frente_nome?: string | null;
  valor_antes_num?: string | null;
  valor_depois_num?: string | null;
  impacto_mensal?: string | null;
  teto?: string | null;
  verba_mes?: string | null;
}

export interface PropostasResponse {
  items: Proposta[];
  pendentes: number;
  pode_decidir: boolean;
  /** Feature 351: soma do impacto das aprovadas e executadas decididas no mês. */
  impacto_aprovado_mes?: string;
}

export type DiarioVeredito = "funcionou" | "nao_funcionou" | "inconclusivo";

export interface DiarioEntrada {
  id: number;
  titulo: string;
  motivo: string;
  evidencia: string | null;
  resultado_esperado: string | null;
  reavaliar_em: string;
  resultado_observado: string | null;
  veredito: DiarioVeredito | null;
  avaliado_em: string | null;
  origem: "proposta" | "pessoa" | "rotina";
  proposta_id: number | null;
  autor: MarketingAssigneeRef | null;
  criado_em: string | null;
  a_reavaliar: boolean;
  /** Feature 351: o teste estruturado, calculado no servidor (`null` = entrada só de texto). */
  teste?: DiarioTeste | null;
}

export type MetricaDoTeste = "conversas" | "custo_conversa" | "gasto" | "cliques" | "cadastros";
export type AlvoTipo = "campanha" | "conjunto" | "anuncio";

export const METRICA_LABELS: Record<MetricaDoTeste, string> = {
  conversas: "Conversas",
  custo_conversa: "Custo por conversa",
  gasto: "Gasto",
  cliques: "Cliques",
  cadastros: "Cadastros",
};

export const ALVO_LABELS: Record<AlvoTipo, string> = {
  campanha: "Campanha",
  conjunto: "Conjunto",
  anuncio: "Anúncio",
};

/** Valores em string decimal (4 casas); `null` = sem leitura no intervalo. */
export interface DiarioTeste {
  alvo: { platform: string; tipo: AlvoTipo; id: string; nome: string | null };
  metrica: MetricaDoTeste;
  mudou_em: string;
  janela_dias: number;
  linha_base: string | null;
  antes: { de: string; ate: string; valor: string | null };
  depois: { de: string; ate: string; valor: string | null };
  variacao: number | null;
  completo: boolean;
  controle: { tipo: AlvoTipo; id: string; nome: string | null; antes: string | null; depois: string | null; variacao: number | null } | null;
  efeito_liquido: number | null;
}

export interface DiarioResponse {
  items: DiarioEntrada[];
  a_reavaliar: number;
}

/** Meta de frequência com a saúde já calculada pelo servidor. */
export interface MarketingGoal {
  id: number;
  name: string;
  target_interval_days: number;
  catalog_item_id: number | null;
  catalog_item: MarketingCatalogItemRef | null;
  created_at: string | null;
  /** Data (`YYYY-MM-DD`) do post publicado mais recente do assunto. */
  last_posted_date: string | null;
  last_post_id: number | null;
  /** `last_posted_date + target_interval_days` — quando o próximo post é devido. */
  next_due_date: string | null;
  days_since_last_post: number | null;
  /** Dias de atraso além do intervalo alvo (0 quando em dia). */
  days_late: number | null;
  never_posted: boolean;
  status: "on_track" | "delayed";
}

export interface MarketingGoalsResponse {
  items: MarketingGoal[];
  delayed_count: number;
}

export interface MarketingOptionsResponse {
  temas: MarketingCatalogItemRef[];
  usuarios: MarketingAssigneeRef[];
  plataformas: string[];
}

/**
 * Formata uma data pura `YYYY-MM-DD` em pt-BR.
 *
 * Não usa `new Date(iso)`: o JS interpreta string **só de data** como UTC e, no fuso de São Paulo
 * (UTC−3), isso exibiria o dia anterior. Mesma razão do `formatDeadline` de `impressoes3d.ts` —
 * mas aqui o módulo é outro e o dado também; extrair um utilitário compartilhado é candidato a
 * uma limpeza futura em `@manto/ui`.
 */
export function formatMarketingDate(value: string | null): string {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return "—";
  return `${day}/${month}/${year}`;
}

/**
 * Dias restantes até a data — negativo = atrasado, `null` sem data. Compara só a parte de data
 * (meia-noite local), para "hoje" nunca virar "atrasado".
 */
export function daysUntil(value: string | null): number | null {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  const target = new Date(year, month - 1, day).getTime();
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  return Math.round((target - start) / 86_400_000);
}

const POSTS_KEY = ["marketing-posts"] as const;
const GOALS_KEY = ["marketing-goals"] as const;
const OPTIONS_KEY = ["marketing-opcoes"] as const;

export function useMarketingPosts() {
  return useQuery<MarketingPostsResponse>({
    queryKey: POSTS_KEY,
    queryFn: () => apiFetch<MarketingPostsResponse>("/api/marketing/posts"),
  });
}

/**
 * Metas de frequência. `staleTime` zero de propósito: o status derivado depende da data de hoje
 * e do último post publicado, então uma volta do Kanban deve refletir aqui na hora.
 */
export function useMarketingGoals() {
  return useQuery<MarketingGoalsResponse>({
    queryKey: GOALS_KEY,
    queryFn: () => apiFetch<MarketingGoalsResponse>("/api/marketing/goals"),
  });
}

/** Temas do catálogo e usuários para os `Combobox` (Princípio X.1/X.2). */
export function useMarketingOptions(enabled = true) {
  return useQuery<MarketingOptionsResponse>({
    queryKey: OPTIONS_KEY,
    queryFn: () => apiFetch<MarketingOptionsResponse>("/api/marketing/opcoes"),
    enabled,
  });
}

export interface SaveMarketingPostInput {
  title?: string;
  status?: MarketingStatus;
  /** `null` limpa o campo; omitido mantém o valor atual (o PATCH é parcial). */
  deadline_date?: string | null;
  publish_date?: string | null;
  platform?: string | null;
  drive_folder_url?: string | null;
  notes?: string | null;
  assignee_id?: number | null;
  catalog_item_ids?: number[];
  permalink?: string | null;
  tipo?: MarketingPostTipo;
  frente?: string | null;
  formato?: string | null;
  briefing_objetivo?: string | null;
  briefing_mostrar?: string | null;
  briefing_letreiro?: string | null;
  conceito?: string | null;
}

/**
 * Invalida tudo que mostra postagens: o painel e as metas (mover um card para "publicado" muda a
 * saúde da meta na hora). Fonte única para as mutações abaixo não divergirem.
 */
function useInvalidatePosts() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: POSTS_KEY });
    void queryClient.invalidateQueries({ queryKey: GOALS_KEY });
  };
}

export function useCreateMarketingPost() {
  const invalidate = useInvalidatePosts();
  return useMutation({
    mutationFn: (input: SaveMarketingPostInput) =>
      apiFetch<MarketingPost>("/api/marketing/posts", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateMarketingPost() {
  const invalidate = useInvalidatePosts();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: SaveMarketingPostInput }) =>
      apiFetch<MarketingPost>(`/api/marketing/posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

/**
 * Troca a coluna do card com **atualização otimista**.
 *
 * O card precisa começar a se mover no clique, não quando a API responde — é a animação de
 * `layoutId` que comunica a causa e o efeito (Princípio IX). O cache é revertido em caso de erro
 * (`onError`) e reconciliado com o servidor no fim (`onSettled`).
 */
export function useMoveMarketingPost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: MarketingStatus }) =>
      apiFetch<MarketingPost>(`/api/marketing/posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: POSTS_KEY });
      const previous = queryClient.getQueryData<MarketingPostsResponse>(POSTS_KEY);
      if (previous) {
        queryClient.setQueryData<MarketingPostsResponse>(POSTS_KEY, {
          ...previous,
          items: previous.items.map((post) => (post.id === id ? { ...post, status } : post)),
        });
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(POSTS_KEY, context.previous);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: POSTS_KEY });
      void queryClient.invalidateQueries({ queryKey: GOALS_KEY });
    },
  });
}

export function useDeleteMarketingPost() {
  const invalidate = useInvalidatePosts();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/marketing/posts/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

/** Cria o espaço de Revisão de Mídia do post e devolve o id para navegar até `/revisao/:id`. */
export function useCreateReviewSpace() {
  const invalidate = useInvalidatePosts();
  return useMutation({
    mutationFn: (postId: number) =>
      apiFetch<{ review_space_id: number; post: MarketingPost }>(
        `/api/marketing/posts/${postId}/create-review`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export interface SaveMarketingGoalInput {
  name?: string;
  target_interval_days?: number;
  catalog_item_id?: number | null;
}

function useInvalidateGoals() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: GOALS_KEY });
  };
}

export function useCreateMarketingGoal() {
  const invalidate = useInvalidateGoals();
  return useMutation({
    mutationFn: (input: SaveMarketingGoalInput) =>
      apiFetch<MarketingGoal>("/api/marketing/goals", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateMarketingGoal() {
  const invalidate = useInvalidateGoals();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: SaveMarketingGoalInput }) =>
      apiFetch<MarketingGoal>(`/api/marketing/goals/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useDeleteMarketingGoal() {
  const invalidate = useInvalidateGoals();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/marketing/goals/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

// ── Desempenho (feature 256 — auditor de marketing) ─────────────────────────

/** Manchete da tela: leads por campanha (decisão do dono) ou alcance quando não há atribuição. */
export interface DesempenhoHeadline {
  kind: "leads" | "alcance";
  value: number;
  cost_per_lead: string | null;
  fallback_reason: string | null;
}

export interface DesempenhoWeek {
  week_start: string;
  reach: number;
  followers: number | null;
  /** Decimal em string — formatar com `formatBRL(Number(...))`. */
  spend: string;
  clicks: number;
  leads: number;
  events: number;
  posts_published: number;
}

export interface DesempenhoCampaign {
  platform: string;
  campaign_name: string;
  spend: string;
  impressions: number;
  clicks: number;
  cpc: string | null;
  leads: number;
  cost_per_lead: string | null;
  events: number;
  cost_per_event: string | null;
  /** Feature 334: fichas que já estavam na base e voltaram por anúncio da campanha no período. */
  returns?: number;
  /** Os eventos criados depois desses retornos. */
  return_events?: number;
  currency: string;
}

export type DesempenhoLinkMethod = "permalink" | "date" | "none";

export interface DesempenhoPost {
  platform: string;
  platform_post_id: string;
  permalink: string | null;
  published_at: string | null;
  post_type: string | null;
  caption: string | null;
  snapshot_date: string;
  reach: number | null;
  impressions: number | null;
  likes: number | null;
  comments: number | null;
  saves: number | null;
  shares: number | null;
  views: number | null;
  marketing_post: { id: number; title: string } | null;
  link_method: DesempenhoLinkMethod;
}

export interface DesempenhoGoal {
  id: number;
  name: string;
  target_interval_days: number;
  status: "on_track" | "delayed";
  days_late?: number | null;
  never_posted?: boolean;
  last_posted_date?: string | null;
}

export interface DesempenhoCac {
  month: string;
  spend: string;
  new_clients: number;
  /** Feature 351: os clientes novos que vieram de anúncio — o divisor do custo. */
  new_clients_ads?: number;
  value: string | null;
}

export interface DesempenhoRun {
  run_id: string;
  mode: "prod" | "local";
  executed_at: string;
  window: [string, string];
  files_accepted: number;
  files_rejected: number;
  report_sent: boolean;
  rejected_files: { filename: string; reason: string | null }[];
}

export interface DesempenhoResponse {
  period: { start: string; end: string; weeks: number | null };
  headline: DesempenhoHeadline;
  weekly: DesempenhoWeek[];
  campaigns: DesempenhoCampaign[];
  posts: DesempenhoPost[];
  goals: DesempenhoGoal[];
  cac: DesempenhoCac;
  runs: DesempenhoRun[];
  /** Nenhuma rodada ainda — a tela mostra as instruções de exportação. */
  empty: boolean;
  /** Feature 345 — opcionais (deploy com backend e bundle em versões diferentes). */
  frentes?: DesempenhoFrente[];
  sem_frente?: CampanhaSemFrente[];
  plataformas?: PlataformaSituacao[];
  frente_opcoes?: { slug: string; nome: string }[];
  /** Feature 351 — a regra da atribuição e as vendas atribuídas a campanha sem frente. */
  atribuicao?: DesempenhoAtribuicao;
}

export type DesempenhoWeeks = 4 | 12 | 26;
export type DesempenhoParams = { weeks: DesempenhoWeeks } | { start: string; end: string };

function desempenhoQuery(params: DesempenhoParams): string {
  const qs = new URLSearchParams();
  if ("weeks" in params) qs.set("weeks", String(params.weeks));
  else {
    qs.set("start", params.start);
    qs.set("end", params.end);
  }
  return qs.toString();
}

/**
 * Histórico do auditor de marketing. `keepPreviousData` segura a tela enquanto o período novo
 * carrega — trocar de 12 para 4 semanas não pode piscar os gráficos.
 */
export function useMarketingDesempenho(params: DesempenhoParams) {
  return useQuery<DesempenhoResponse>({
    queryKey: ["marketing", "desempenho", params],
    queryFn: () => apiFetch<DesempenhoResponse>(`/api/marketing/desempenho?${desempenhoQuery(params)}`),
    placeholderData: keepPreviousData,
  });
}

// ── Feature 345: frentes, licença, propostas e diário ───────────────────────

const FRENTES_KEY = ["marketing", "frentes"] as const;
const TEMAS_LICENCA_KEY = ["marketing", "temas-licenca"] as const;
const PROPOSTAS_KEY = ["marketing", "propostas"] as const;
const DIARIO_KEY = ["marketing", "diario"] as const;

/** Tetos de custo por venda e responsáveis por criativo. */
export function useFrentesConfig(enabled = true) {
  return useQuery<FrentesConfig>({
    queryKey: FRENTES_KEY,
    queryFn: () => apiFetch<FrentesConfig>("/api/marketing/frentes"),
    enabled,
  });
}

export interface SalvarFrentesInput {
  /** slug → teto em string decimal; `null` volta ao padrão calculado. */
  tetos?: Record<string, string | null>;
  /** Feature 351: meta de vendas e verba do mês por frente; `null` limpa. */
  metas?: Record<string, number | null>;
  verbas?: Record<string, string | null>;
  resp_foto_id?: number | null;
  resp_video_id?: number | null;
}

export function useSalvarFrentes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SalvarFrentesInput) =>
      apiFetch<FrentesConfig>("/api/marketing/frentes", { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: (data) => {
      queryClient.setQueryData(FRENTES_KEY, data);
      // O teto muda o estado de cada frente no Desempenho.
      void queryClient.invalidateQueries({ queryKey: ["marketing", "desempenho"] });
    },
  });
}

/** Corrige (ou desfaz, com `frente: null`) a frente de uma campanha. */
export function useCorrigirFrente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { platform: string; campaign_id: string; frente: string | null }) =>
      apiFetch<{ ok: boolean }>("/api/marketing/campanhas/frente", { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["marketing", "desempenho"] }),
  });
}

export interface TemasLicencaFiltros {
  q?: string;
  origem?: LicencaOrigem | "";
  liberado?: LiberadoAnuncio | "";
  sugestao?: boolean;
  pagina?: number;
}

export function useTemasLicenca(filtros: TemasLicencaFiltros) {
  const qs = new URLSearchParams();
  if (filtros.q) qs.set("q", filtros.q);
  if (filtros.origem) qs.set("origem", filtros.origem);
  if (filtros.liberado) qs.set("liberado", filtros.liberado);
  if (filtros.sugestao) qs.set("sugestao", "1");
  if (filtros.pagina && filtros.pagina > 1) qs.set("pagina", String(filtros.pagina));
  return useQuery<TemasLicencaResponse>({
    queryKey: [...TEMAS_LICENCA_KEY, filtros],
    queryFn: () => apiFetch<TemasLicencaResponse>(`/api/marketing/temas-licenca?${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
}

function useInvalidateTemas() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: TEMAS_LICENCA_KEY });
    // As opções do diálogo do card levam a licença de cada tema.
    void queryClient.invalidateQueries({ queryKey: OPTIONS_KEY });
  };
}

export function useConfirmarSugestoes() {
  const invalidate = useInvalidateTemas();
  return useMutation({
    mutationFn: (ids: number[]) =>
      apiFetch<{ confirmados: number }>("/api/marketing/temas-licenca/confirmar", {
        method: "POST",
        body: JSON.stringify({ ids }),
      }),
    onSuccess: invalidate,
  });
}

export function useMarcarLicenca() {
  const invalidate = useInvalidateTemas();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: { licenca_origem?: LicencaOrigem; liberado_anuncio?: LiberadoAnuncio } }) =>
      apiFetch<TemaLicenca>(`/api/marketing/temas-licenca/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  });
}

export function usePropostas() {
  return useQuery<PropostasResponse>({
    queryKey: PROPOSTAS_KEY,
    queryFn: () => apiFetch<PropostasResponse>("/api/marketing/propostas"),
  });
}

export function useDecidirProposta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decisao, obs }: { id: number; decisao: "aprovar" | "recusar"; obs?: string }) =>
      apiFetch<Proposta>(`/api/marketing/propostas/${id}/decidir`, {
        method: "POST",
        body: JSON.stringify({ decisao, obs }),
      }),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: PROPOSTAS_KEY }),
  });
}

export function useDiario() {
  return useQuery<DiarioResponse>({
    queryKey: DIARIO_KEY,
    queryFn: () => apiFetch<DiarioResponse>("/api/marketing/diario"),
  });
}

export interface NovaEntradaDiario {
  titulo: string;
  motivo: string;
  evidencia?: string;
  resultado_esperado?: string;
  reavaliar_em?: string;
  // Feature 351 — o teste estruturado (opcional).
  alvo_platform?: string;
  alvo_tipo?: AlvoTipo;
  alvo_id?: string;
  alvo_nome?: string;
  metrica?: MetricaDoTeste;
  mudou_em?: string;
  janela_dias?: number;
  controle_tipo?: AlvoTipo;
  controle_id?: string;
  controle_nome?: string;
}

export function useCriarEntradaDiario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NovaEntradaDiario) =>
      apiFetch<DiarioEntrada>("/api/marketing/diario", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: DIARIO_KEY }),
  });
}

// ── Feature 351: venda atribuída, funil com custo e calendário do ano ───────

export type DivisaoAtribuicao = "frente" | "anuncio" | "peca" | "conceito";

export const DIVISAO_ATRIBUICAO_LABELS: Record<DivisaoAtribuicao, string> = {
  frente: "Frente",
  anuncio: "Anúncio",
  peca: "Peça",
  conceito: "Conceito",
};

export interface AtribuicaoVenda {
  event_id: number;
  titulo: string;
  sale_date: string;
  /** `null` para quem não é Superadmin (o servidor decide). */
  valor: string | null;
  frente_venda: string;
  frente: string | null;
  frente_nome: string | null;
  contato: {
    fonte: "conversa" | "ficha" | "utm";
    em: string;
    platform: string | null;
    campanha: string | null;
    anuncio_id: string | null;
    anuncio: string | null;
  };
}

export interface FunilComCustoGrupo {
  chave: string;
  rotulo: string;
  quantidades: Record<"chegou" | "orcamento" | "formulario" | "evento" | "pagou" | "avaliou", number>;
  conversao: number | null;
  gasto: string | null;
  custo_conversa: string | null;
  custo_orcamento: string | null;
  custo_evento: string | null;
}

export interface AtribuicaoResponse {
  periodo: { start: string; end: string };
  regra: AtribuicaoRegra;
  vendas: AtribuicaoVenda[];
  vendas_total: number;
  /** `aviso` = o funil recusou o período (mais de um ano); a lista de vendas vem assim mesmo. */
  funil: { dividir: DivisaoAtribuicao; total: number; grupos: FunilComCustoGrupo[]; aviso?: string };
  pode_ver_valor: boolean;
}

/** Vendas atribuídas e funil com custo do mesmo período do Desempenho. */
export function useAtribuicao(params: DesempenhoParams, dividir: DivisaoAtribuicao) {
  return useQuery<AtribuicaoResponse>({
    queryKey: ["marketing", "atribuicao", params, dividir],
    queryFn: () =>
      apiFetch<AtribuicaoResponse>(`/api/marketing/atribuicao?${desempenhoQuery(params)}&dividir=${dividir}`),
    placeholderData: keepPreviousData,
  });
}

export interface CalendarioMes {
  mes: number;
  meta_vendas: number | null;
  verba: string | null;
  foco: string | null;
}

export interface CalendarioFrente {
  slug: string;
  nome: string;
  meta_vendas_mes: number | null;
  verba_mes: string | null;
  meses: CalendarioMes[];
}

export interface CalendarioResponse {
  frentes: CalendarioFrente[];
  mes_corrente: number;
  pode_editar: boolean;
}

const CALENDARIO_KEY = ["marketing", "calendario"] as const;

export function useCalendario(enabled = true) {
  return useQuery<CalendarioResponse>({
    queryKey: CALENDARIO_KEY,
    queryFn: () => apiFetch<CalendarioResponse>("/api/marketing/calendario"),
    enabled,
  });
}

export function useSalvarCalendario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { frente: string; meses: CalendarioMes[] }) =>
      apiFetch<CalendarioResponse>("/api/marketing/calendario", { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: (data) => {
      queryClient.setQueryData(CALENDARIO_KEY, data);
      // A meta e a verba do mês aparecem no card de cada frente.
      void queryClient.invalidateQueries({ queryKey: ["marketing", "desempenho"] });
    },
  });
}

export const NOMES_DOS_MESES = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
] as const;
