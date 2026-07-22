import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FeedbackEvent {
  event_title: string;
  event_date: string | null;
  positive_tags: string[];
  attention_tags: string[];
}

export interface FeedbackSubmitInput {
  client_name: string;
  score: number;
  tags: string[];
  comment: string;
}

/** Dados do evento associado ao token — 404 se o link não existir. */
export function useFeedbackEvent(token: string) {
  return useQuery<FeedbackEvent>({
    queryKey: ["feedback-event", token],
    queryFn: () => apiFetch<FeedbackEvent>(`/api/avaliar/${token}`),
    retry: false,
  });
}

/** Envia a avaliação — `contracts/feedback-endpoints.md`. */
export function useSubmitFeedback(token: string) {
  return useMutation<{ ok: boolean }, Error, FeedbackSubmitInput>({
    mutationFn: (input) =>
      apiFetch<{ ok: boolean }>(`/api/avaliar/${token}`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}
