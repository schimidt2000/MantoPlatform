import { QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiRequestError } from "./client";

export interface OpcoesQueryClient {
  /**
   * Chamado quando QUALQUER consulta responde 401 — a sessão caiu no meio do uso.
   *
   * Sem isto, cada tela descobre a perda sozinha e mostra o próprio recado de erro, enquanto o
   * resto do app segue desenhando dados do cache: no portal isso produzia a tela em que o
   * cabeçalho mostra o nome do artista e o conteúdo diz "não foi possível carregar" — o estado
   * que ninguém conseguia diagnosticar, porque parece um erro de servidor e é sessão expirada.
   */
  aoPerderSessao?: () => void;
}

/**
 * Cria a instância do QueryClient compartilhada pelos apps.
 *
 * Não tenta refazer requisições que falharam por erro do cliente (401/403/404) — só faz
 * sentido repetir falhas transitórias de rede/servidor.
 */
export function createQueryClient(opcoes: OpcoesQueryClient = {}): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (erro) => {
        if (erro instanceof ApiRequestError && erro.status === 401) {
          opcoes.aoPerderSessao?.();
        }
      },
    }),
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
