import { QueryClient } from "@tanstack/react-query";
import { ApiRequestError } from "./client";

/**
 * Cria a instância do QueryClient compartilhada pelos apps.
 *
 * Não tenta refazer requisições que falharam por erro do cliente (401/403/404) — só faz
 * sentido repetir falhas transitórias de rede/servidor.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (error instanceof ApiRequestError && error.status < 500) {
            return false;
          }
          return failureCount < 2;
        },
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
    },
  });
}
