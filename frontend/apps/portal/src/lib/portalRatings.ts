import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

const PENDING_KEY = ["portal", "ratings", "pending"] as const;

const ratingKey = (eventId: number) => ["portal", "ratings", eventId] as const;

/** Categoria de sub-avaliação sem pessoa associada. */
export type RatingGeneralCategory = "figurino" | "som" | "texto";

/** Categoria de sub-avaliação dirigida a alguém do elenco/equipe. */
export type RatingPersonCategory = "artista" | "coordenacao" | "maquiagem";

/** Uma sub-avaliação já gravada. */
export interface RatingSub {
  category: string;
  subject_talent_id: number | null;
  score: number;
  comment: string | null;
}

/** Pessoa avaliável do evento. */
export interface RatingPerson {
  talent_id: number;
  name: string;
  character_name: string | null;
  photo_face_url: string | null;
  category: RatingPersonCategory;
}

/** Formulário de avaliação de um evento (`GET /api/portal/events/<id>/rate`). */
export interface RatingForm {
  event: {
    id: number;
    title: string;
    start_at: string | null;
    end_at: string | null;
    location: string | null;
  };
  is_show: boolean;
  general_categories: RatingGeneralCategory[];
  people: RatingPerson[];
  /** False quando a janela de 30 dias de edição já fechou para uma avaliação existente. */
  can_edit: boolean;
  rating: {
    score: number;
    comment: string | null;
    submitted_at: string | null;
    detail_submitted_at: string | null;
    subs: RatingSub[];
  } | null;
}

/** Eventos que o talento pode avaliar, já avaliou e ainda pode editar. */
export interface PendingRatings {
  rateable_event_ids: number[];
  rated_event_ids: number[];
  editable_event_ids: number[];
}

/** Situação das avaliações do talento — usada para destacar pendências na Agenda/Histórico. */
export function usePendingRatings() {
  return useQuery({
    queryKey: PENDING_KEY,
    queryFn: () => apiFetch<PendingRatings>("/api/portal/ratings/pending"),
  });
}

/** Formulário de avaliação de um evento específico. */
export function useRatingForm(eventId: number) {
  return useQuery({
    queryKey: ratingKey(eventId),
    queryFn: () => apiFetch<RatingForm>(`/api/portal/events/${eventId}/rate`),
    enabled: Number.isFinite(eventId),
    retry: false,
  });
}

/**
 * O snapshot pré-edição, reenviado ao backend para ele registrar a versão anterior no histórico
 * quando o conteúdo muda (feature 181). `null` numa primeira avaliação.
 */
export type RatingBaseline = { score: number; comment: string | null; subs: RatingSub[] } | null;

/** Deriva o baseline do formulário carregado, no formato que o backend compara. */
export function baselineFrom(form: RatingForm | undefined): RatingBaseline {
  if (!form?.rating) return null;
  return { score: form.rating.score, comment: form.rating.comment, subs: form.rating.subs };
}

interface SubmitRatingBody {
  eventId: number;
  score: number;
  comment: string | null;
  baseline: RatingBaseline;
}

/** Envia a nota geral do evento (etapa 1). */
export function useSubmitRating() {
  const queryClient = useQueryClient();
  return useMutation<RatingForm, Error, SubmitRatingBody>({
    mutationFn: ({ eventId, ...body }) =>
      apiFetch<RatingForm>(`/api/portal/events/${eventId}/rate`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (form, { eventId }) => {
      queryClient.setQueryData(ratingKey(eventId), form);
      queryClient.invalidateQueries({ queryKey: PENDING_KEY });
    },
  });
}

interface SubmitDetailBody {
  eventId: number;
  general: Partial<Record<RatingGeneralCategory, { score: number; comment: string | null }>>;
  people: Array<{
    category: RatingPersonCategory;
    subject_talent_id: number;
    score: number;
    comment: string | null;
  }>;
  baseline: RatingBaseline;
}

/** Envia as sub-avaliações do evento (etapa 2, opcional). */
export function useSubmitRatingDetail() {
  const queryClient = useQueryClient();
  return useMutation<RatingForm, Error, SubmitDetailBody>({
    mutationFn: ({ eventId, ...body }) =>
      apiFetch<RatingForm>(`/api/portal/events/${eventId}/rate/detail`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (form, { eventId }) => {
      queryClient.setQueryData(ratingKey(eventId), form);
      queryClient.invalidateQueries({ queryKey: PENDING_KEY });
    },
  });
}
