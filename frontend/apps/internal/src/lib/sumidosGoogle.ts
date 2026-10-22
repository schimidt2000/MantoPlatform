import { useQuery, type QueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import { POLL_MS } from "./notificacoes";
import { useCurrentUser } from "./useAuth";

/** Um evento marcado "Sumiu do Google Agenda" na faixa do topo (feature 303). Sem dinheiro. */
export interface SumidoGoogle {
  id: number;
  title: string;
  /** ISO sem fuso, horário de parede de São Paulo; `null` = sem data. */
  start_at: string | null;
}

/** `GET /api/events/sumidos-google`. Quem não vê recebe `pode_ver: false` e a lista vazia. */
export interface FaixaSumidos {
  pode_ver: boolean;
  /** Contagem exata dos marcados — a frase da faixa usa este número, nunca `items.length`. */
  total: number;
  limit: number;
  /** Por urgência: futuros por data, depois passados do mais recente, sem data por último. */
  items: SumidoGoogle[];
  /**
   * Feature 315: os pedidos de cancelamento pendentes, na mesma ordem. Opcional: o backend de
   * antes do deploy não manda; `total`/`items` acima continuam só do sumiço.
   */
  pedidos?: { total: number; items: SumidoGoogle[] };
}

const PREFIXO = "sumidos-google";

// O id do usuário na chave: o logout só zera o cache do `/me`, e a faixa de quem saiu não pode
// aparecer para quem entrou depois na mesma aba.
function chave(userId: number | undefined) {
  return [PREFIXO, userId] as const;
}

/**
 * A faixa — montada SÓ no `AppShell`. Poll de 60 s enquanto o servidor não disser que o usuário
 * não vê (`pode_ver: false` desliga o poll sem o front decidir RBAC); nada em aba de fundo; falha
 * no poll é silêncio (sem retentativas em cascata), como o sino.
 */
export function useSumidosGoogle() {
  const { data: user } = useCurrentUser();
  return useQuery<FaixaSumidos>({
    queryKey: chave(user?.id),
    queryFn: () => apiFetch<FaixaSumidos>("/api/events/sumidos-google"),
    enabled: Boolean(user),
    refetchInterval: (query) => (query.state.data?.pode_ver === false ? false : POLL_MS),
    refetchIntervalInBackground: false,
    retry: false,
  });
}

/**
 * A faixa está na tela? Para quem precisa somar a altura dela (régua de abas do evento, âncoras da
 * Home). Observer PASSIVO da mesma chave: cada observer com `refetchInterval` tem timer próprio no
 * TanStack 5, e um segundo hook ativo dobraria os GETs por minuto.
 */
export function useFaixaSumidosVisivel(): boolean {
  const { data: user } = useCurrentUser();
  const { data } = useQuery<FaixaSumidos, Error, boolean>({
    queryKey: chave(user?.id),
    queryFn: () => apiFetch<FaixaSumidos>("/api/events/sumidos-google"),
    enabled: false,
    select: (faixa) => faixa.pode_ver && (faixa.total > 0 || (faixa.pedidos?.total ?? 0) > 0),
  });
  return data ?? false;
}

/** Recarrega a faixa depois de uma ação que marca ou desmarca evento — sem esperar o poll. */
export function invalidarSumidosGoogle(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: [PREFIXO] });
}
