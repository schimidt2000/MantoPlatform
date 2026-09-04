import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";

/** Chave da consulta do talento logado. Exportada porque o `main.tsx` a limpa ao perder a sessão. */
export const ME_KEY = ["portal", "auth", "me"] as const;

/** Etapa de onboarding que o talento precisa concluir antes de usar o portal. */
export type PortalPendingStep = "change_password" | "accept_terms";

/** Talento autenticado atual (`/api/portal/auth/me`). */
export interface PortalTalent {
  id: number;
  full_name: string;
  artistic_name: string | null;
  photo_face_url: string | null;
  photo_full_url: string | null;
  must_change_password: boolean;
  terms_accepted: boolean;
  /** Etapas pendentes, na ordem em que devem ser feitas. Vazia = conta em dia. */
  pending_steps: PortalPendingStep[];
}

/**
 * Busca o talento autenticado atual. `null` quando não há sessão.
 *
 * Só o **401** vira `null`. Antes o `catch` engolia tudo, e com isso "sua sessão expirou",
 * "o servidor caiu" e "o celular está sem rede" produziam exatamente o mesmo estado — o motivo
 * de um relato de portal quebrado nunca chegar com o dado que o resolveria. Erro de rede ou de
 * servidor agora **propaga**, para a tela poder dizer a verdade e oferecer "tentar de novo"
 * em vez de mandar a pessoa para o login sem motivo.
 */
export function useCurrentTalent() {
  return useQuery<PortalTalent | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<PortalTalent>("/api/portal/auth/me");
      } catch (erro) {
        if (erro instanceof ApiRequestError && erro.status === 401) return null;
        throw erro;
      }
    },
  });
}

interface LoginCredentials {
  login: string;
  password: string;
}

/**
 * Resposta do login. Era `PortalTalent` + `must_redirect_to_classic` (fatia 176, quando troca de
 * senha e termos só existiam no portal Jinja); esse campo foi removido do backend junto com a
 * aposentadoria das telas Jinja — o talento sempre entra direto no portal React.
 */
type LoginResult = PortalTalent;

/** Mutation de login; ao suceder, popula o cache do talento atual. */
export function usePortalLogin() {
  const queryClient = useQueryClient();
  return useMutation<LoginResult, Error, LoginCredentials>({
    mutationFn: (credentials) =>
      apiFetch<LoginResult>("/api/portal/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      }),
    onSuccess: (talent) => {
      queryClient.setQueryData(ME_KEY, talent);
    },
  });
}

/** Mutation de logout; limpa o cache do talento atual. */
export function usePortalLogout() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiFetch<void>("/api/portal/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(ME_KEY, null);
    },
  });
}
