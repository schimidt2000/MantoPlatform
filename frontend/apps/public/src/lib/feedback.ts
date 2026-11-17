import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FeedbackEvent {
  event_title: string;
  event_date: string | null;
  positive_tags: string[];
  attention_tags: string[];
  /** Link de avaliação no Google — CTA da tela de agradecimento quando a nota é 5. */
  google_review_url: string;
  /**
   * Feature 350: as duas caixas de autorização. Ausente quando o evento não tem ficha contratante
   * (não há onde gravar) e em backend velho.
   */
  consentimento?: ConsentimentoPublico;
}

export interface TextoDaAutorizacao {
  texto: string;
  versao: string;
}

export interface ConsentimentoPublico {
  primeiro_nome: string | null;
  recebe_novidades: boolean;
  textos: { novidades: TextoDaAutorizacao; aniversario: TextoDaAutorizacao };
}

export interface EscolhasDeConsentimento {
  novidades?: "aceitar" | "retirar" | null;
  versao_novidades?: string;
  crianca?: { primeiro_nome: string; nascimento: string; aceite: boolean } | null;
  versao_aniversario?: string;
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

/**
 * Feature 350: a cliente aceita ou retira novidades e guarda o aniversário da criança. A tela manda
 * a versão do texto que exibiu — o servidor grava exatamente esse texto como prova.
 */
export function useSalvarConsentimento(token: string) {
  const queryClient = useQueryClient();
  return useMutation<{ recebe_novidades: boolean }, Error, EscolhasDeConsentimento>({
    mutationFn: (input) =>
      apiFetch<{ recebe_novidades: boolean }>(`/api/avaliar/${token}/consentimento`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["feedback-event", token] }),
  });
}
