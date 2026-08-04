import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Módulo de Gestão de Marketing e Frequência (feature 204) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/marketing/*`: as duas telas (`/marketing/painel` e
 * `/marketing/metas`) e o Dialog de edição consomem daqui, nenhuma monta `fetch` por conta
 * própria (Princípio I).
 */

/** Colunas do Kanban, na ordem do fluxo de produção. */
export type MarketingStatus = "ideia" | "producao" | "revisao" | "agendado" | "publicado";

export const MARKETING_STATUSES: MarketingStatus[] = [
  "ideia",
  "producao",
  "revisao",
  "agendado",
  "publicado",
];

export const MARKETING_STATUS_LABELS: Record<MarketingStatus, string> = {
  ideia: "Ideia",
  producao: "Produção",
  revisao: "Revisão",
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
  agendado: "accent",
  publicado: "green",
};

/** Emoji de cada coluna — leitura de relance do Kanban, sem depender só da cor. */
export const MARKETING_STATUS_ICONS: Record<MarketingStatus, string> = {
  ideia: "💡",
  producao: "🎬",
  revisao: "👀",
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
  notes: string | null;
  assignee_id: number | null;
  assignee: MarketingAssigneeRef | null;
  catalog_item_ids: number[];
  catalog_items: MarketingCatalogItemRef[];
  review_space_id: number | null;
  review_space: MarketingReviewSpaceRef | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MarketingPostsResponse {
  items: MarketingPost[];
  statuses: MarketingStatus[];
  plataformas: string[];
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
