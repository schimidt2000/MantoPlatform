import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface RatingComment {
  score: number;
  comment: string;
  author: string;
  author_funcao: string | null;
  event_title: string;
  event_id: number;
  event_date: string | null;
  submitted_at: string | null;
  cat_key: string;
  cat_label: string;
  subject_name: string | null;
}

export interface RankedEvent {
  id: number;
  title: string;
  start_at: string | null;
  avg: number;
  count: number;
}

export interface TrendPoint {
  label: string;
  avg: number;
  count: number;
}

export interface CategoryAverage {
  key: string;
  label: string;
  avg: number;
  count: number;
}

export interface EventOption {
  id: number;
  title: string;
  start_at: string | null;
}

export interface EventGroup {
  label: string;
  events: EventOption[];
}

export interface RatingsOverview {
  event_groups: EventGroup[];
  selected_event: EventOption | null;
  event_id: number | null;
  cat: string;
  cat_label: string;
  categories: { key: string; label: string }[];
  period: string;
  date_mode: string;
  from_raw: string;
  to_raw: string;
  recorte_label: string;
  has_filters: boolean;
  total: number;
  avg_overall: number;
  events_rated: number;
  dist: Record<string, number>;
  dist_max: number;
  by_category: CategoryAverage[];
  comments: RatingComment[];
  attention: RatingComment[];
  best_events: RankedEvent[];
  worst_events: RankedEvent[];
  trend: TrendPoint[];
  show_authors: boolean;
  fully_anonymous: boolean;
  is_superadmin: boolean;
}

export type RatingsPeriod = "all" | "7d" | "30d" | "90d" | "365d" | "custom";

export interface RatingsFilters {
  event_id?: string;
  cat?: string;
  period?: RatingsPeriod;
  from?: string;
  to?: string;
  date_mode?: "evento" | "avaliacao";
}

/** Panorama de avaliações de casting (feature 177, US6). */
export function useRatingsOverview(filters: RatingsFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const qs = params.toString();
  return useQuery<RatingsOverview>({
    queryKey: ["ratings-overview", qs],
    queryFn: () => apiFetch<RatingsOverview>(`/api/ratings${qs ? `?${qs}` : ""}`),
  });
}

/** Liga/desliga o modo anônimo total das avaliações (SUPERADMIN). */
export function useToggleAnonymousMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) =>
      apiFetch<{ fully_anonymous: boolean }>("/api/ratings/modo-anonimo", {
        method: "POST",
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ratings-overview"] }),
  });
}
