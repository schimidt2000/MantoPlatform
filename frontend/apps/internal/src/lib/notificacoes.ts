import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import { formatRelativeDay, formatShortDate } from "@manto/ui";

/**
 * Notificações internas (feature 272) — hooks da caixa do usuário.
 *
 * As chaves são todas filhas de `["notificacoes"]` de propósito: invalidar o prefixo pega
 * contagem e listas de uma vez (a armadilha de docs/04 §8 é prefixo que não é pai).
 */

export type Severidade = "info" | "urgent";

export interface Notificacao {
  id: number;
  kind: string;
  severity: Severidade;
  title: string;
  body: string | null;
  /** Caminho RELATIVO da SPA interna (`/formularios?resposta=12`) — nunca URL absoluta. */
  link_path: string | null;
  entity_type: string | null;
  entity_id: number | null;
  /** ISO naive São Paulo, como `start_at` dos eventos — recorte a string, não passe por `Date`. */
  created_at: string;
  read_at: string | null;
}

export interface PaginaNotificacoes {
  items: Notificacao[];
  /** Cursor da próxima página (`antes_de`), ou `null` quando acabou. */
  next_before: number | null;
  unread_count: number;
}

interface NaoLidas {
  unread_count: number;
}

const NAO_LIDAS_KEY = ["notificacoes", "nao-lidas"] as const;
const LISTA_KEY = ["notificacoes", "lista"] as const;

/** Intervalo do polling da contagem. 60 s é "imediato" para um lead respondido em horas. */
export const POLL_MS = 60_000;

/**
 * Contagem de não lidas — o endpoint do polling.
 *
 * Exceções deliberadas ao `createQueryClient` (staleTime 30 s, focus off): é o único dado do app
 * que nasce de gente de fora (cliente pública, talento no portal), então invalidação explícita não
 * alcança — daí `refetchInterval` e `refetchOnWindowFocus`. `refetchIntervalInBackground: false`:
 * aba esquecida não gasta requisição. `retry: false`: falha no poll é silêncio (o badge some), não
 * três tentativas em cascata.
 */
export function useNaoLidas(enabled = true) {
  return useQuery<NaoLidas>({
    queryKey: NAO_LIDAS_KEY,
    queryFn: () => apiFetch<NaoLidas>("/api/notificacoes/nao-lidas"),
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: false,
    enabled,
  });
}

/** Lista paginada por keyset (`antes_de`). `staleTime: 0`: cada abertura do painel busca fresco. */
export function useNotificacoes(somenteNaoLidas: boolean, enabled = true) {
  return useInfiniteQuery({
    queryKey: [...LISTA_KEY, { somenteNaoLidas }],
    queryFn: ({ pageParam }) =>
      apiFetch<PaginaNotificacoes>(
        `/api/notificacoes?limite=30${somenteNaoLidas ? "&somente_nao_lidas=1" : ""}${
          pageParam ? `&antes_de=${pageParam}` : ""
        }`,
      ),
    initialPageParam: null as number | null,
    getNextPageParam: (ultima) => ultima.next_before,
    staleTime: 0,
    enabled,
  });
}

interface RespostaLida {
  id: number;
  read_at: string | null;
  unread_count: number;
}

/**
 * Marca uma notificação como lida. Otimista na contagem: o badge cai no clique, antes do POST
 * voltar — o destino é o que importa e o poll seguinte reconcilia. Erro devolve a contagem ao
 * servidor (invalidação), sem mensagem: o usuário já está na tela de destino.
 */
export function useMarcarLida() {
  const queryClient = useQueryClient();
  return useMutation<RespostaLida, Error, number>({
    mutationFn: (id) => apiFetch<RespostaLida>(`/api/notificacoes/${id}/lida`, { method: "POST" }),
    onMutate: () => {
      queryClient.setQueryData<NaoLidas>(NAO_LIDAS_KEY, (atual) =>
        atual ? { unread_count: Math.max(0, atual.unread_count - 1) } : atual,
      );
    },
    onSuccess: (resposta) => {
      queryClient.setQueryData<NaoLidas>(NAO_LIDAS_KEY, { unread_count: resposta.unread_count });
      void queryClient.invalidateQueries({ queryKey: LISTA_KEY });
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: NAO_LIDAS_KEY });
    },
  });
}

interface RespostaTodasLidas {
  marcadas: number;
  unread_count: number;
}

/**
 * "Marcar todas como lidas" — sempre com teto (`ate_id` = maior id na tela): uma notificação que
 * chegou depois de a lista ser desenhada continua não lida.
 */
export function useMarcarTodasLidas() {
  const queryClient = useQueryClient();
  return useMutation<RespostaTodasLidas, Error, number>({
    mutationFn: (ateId) =>
      apiFetch<RespostaTodasLidas>("/api/notificacoes/lidas", {
        method: "POST",
        body: JSON.stringify({ ate_id: ateId }),
      }),
    onSuccess: (resposta) => {
      queryClient.setQueryData<NaoLidas>(NAO_LIDAS_KEY, { unread_count: resposta.unread_count });
      void queryClient.invalidateQueries({ queryKey: LISTA_KEY });
    },
  });
}

export interface GrupoDoDia {
  rotulo: string;
  itens: Notificacao[];
}

/** "Hoje" / "Ontem" / data curta — organiza sem esconder (decisão 16 da spec). */
export function rotuloDoDia(iso: string): string {
  const relativo = formatRelativeDay(iso);
  if (relativo === "hoje") return "Hoje";
  if (relativo === "ontem") return "Ontem";
  return formatShortDate(iso);
}

/** Agrupa mantendo a ordem (mais recente primeiro). */
export function agruparPorDia(itens: Notificacao[]): GrupoDoDia[] {
  const grupos: GrupoDoDia[] = [];
  for (const item of itens) {
    const rotulo = rotuloDoDia(item.created_at);
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.rotulo === rotulo) ultimo.itens.push(item);
    else grupos.push({ rotulo, itens: [item] });
  }
  return grupos;
}
