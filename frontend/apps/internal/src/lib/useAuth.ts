import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { AuthUser } from "./types";

const ME_KEY = ["auth", "me"] as const;

interface LoginCredentials {
  email: string;
  password: string;
}

/** Busca o usuário autenticado atual (/api/auth/me). `null` quando não há sessão. */
export function useCurrentUser() {
  return useQuery<AuthUser | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<AuthUser>("/api/auth/me");
      } catch {
        // 401 (sem sessão) não é erro de tela — significa "deslogado".
        return null;
      }
    },
  });
}

/** Mutation de login; ao suceder, popula o cache do usuário atual. */
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation<AuthUser, Error, LoginCredentials>({
    mutationFn: (credentials) =>
      apiFetch<AuthUser>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      }),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user);
    },
  });
}

/** Mutation de logout; limpa o cache do usuário atual. */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiFetch<void>("/api/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(ME_KEY, null);
    },
  });
}

/**
 * Ativa o "Ver como" (impersonação de papel — SUPERADMIN real, feature 173).
 * Invalida TODAS as queries no sucesso: qualquer dado sensível a RBAC refaz o
 * fetch sob a nova sessão.
 */
export function useImpersonate() {
  const queryClient = useQueryClient();
  return useMutation<AuthUser, Error, string>({
    mutationFn: (role) =>
      apiFetch<AuthUser>("/api/auth/impersonate", {
        method: "POST",
        body: JSON.stringify({ role }),
      }),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user);
      void queryClient.invalidateQueries();
    },
  });
}

/** Limpa o "Ver como" e volta ao papel real (idempotente no servidor). */
export function useImpersonateReset() {
  const queryClient = useQueryClient();
  return useMutation<AuthUser, Error, void>({
    mutationFn: () => apiFetch<AuthUser>("/api/auth/impersonate", { method: "DELETE" }),
    onSuccess: (user) => {
      queryClient.setQueryData(ME_KEY, user);
      void queryClient.invalidateQueries();
    },
  });
}
