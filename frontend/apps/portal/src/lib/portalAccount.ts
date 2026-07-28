import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { PortalTalent } from "./portalAuth";

const ME_KEY = ["portal", "auth", "me"] as const;

/**
 * Hooks dos fluxos de conta do portal (feature 191): primeiro acesso, esqueci minha senha,
 * redefinição por token, troca de senha obrigatória e aceite dos termos.
 *
 * Os dois últimos exigem sessão aberta e atualizam o cache do talento atual — é assim que o
 * `RequireTalentAuth` percebe que o onboarding terminou e libera o app.
 */

interface FirstAccessResult {
  /** E-mail mascarado para onde a senha temporária foi enviada (ex.: `jo***@dominio.com`). */
  email_hint: string;
}

/** Primeiro acesso: gera senha temporária e envia por e-mail. */
export function useFirstAccess() {
  return useMutation<FirstAccessResult, Error, { login: string }>({
    mutationFn: (body) =>
      apiFetch<FirstAccessResult>("/api/portal/auth/first-access", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  });
}

/** Esqueci minha senha: dispara o link de redefinição. Responde 200 mesmo se o CPF não existe. */
export function useForgotPassword() {
  return useMutation<{ message: string }, Error, { login: string; email: string }>({
    mutationFn: (body) =>
      apiFetch<{ message: string }>("/api/portal/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  });
}

/** Verifica se um token de redefinição ainda é válido, antes de mostrar o formulário. */
export function useResetTokenCheck(token: string | undefined) {
  return useQuery({
    queryKey: ["portal", "auth", "reset-token", token],
    queryFn: () => apiFetch<{ valid: boolean }>(`/api/portal/auth/reset-password/${token}`),
    enabled: Boolean(token),
    retry: false,
  });
}

interface NewPasswordBody {
  new_password: string;
  confirm_password: string;
}

/** Redefine a senha a partir do token recebido por e-mail. */
export function useResetPassword() {
  return useMutation<{ message: string }, Error, NewPasswordBody & { token: string }>({
    mutationFn: (body) =>
      apiFetch<{ message: string }>("/api/portal/auth/reset-password", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  });
}

/** Troca a senha do talento logado; ao suceder, limpa `must_change_password` no cache. */
export function useChangePassword() {
  const queryClient = useQueryClient();
  return useMutation<PortalTalent, Error, NewPasswordBody>({
    mutationFn: (body) =>
      apiFetch<PortalTalent>("/api/portal/auth/change-password", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (talent) => {
      queryClient.setQueryData(ME_KEY, talent);
    },
  });
}

/** Registra o aceite dos termos de uso; ao suceder, libera o app no cache do talento. */
export function useAcceptTerms() {
  const queryClient = useQueryClient();
  return useMutation<PortalTalent, Error, void>({
    mutationFn: () =>
      apiFetch<PortalTalent>("/api/portal/auth/accept-terms", { method: "POST" }),
    onSuccess: (talent) => {
      queryClient.setQueryData(ME_KEY, talent);
    },
  });
}
