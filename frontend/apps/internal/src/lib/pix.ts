import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * PIX recebido lido do aviso do banco e ligado à venda (feature 318). Contrato:
 * `specs/318-pix-recebido-por-email/contracts/api-318.md`. O servidor decide quem vê o quê: o
 * repasse da InfinitePay e o "Desfazer" só chegam a Financeiro/Superadmin (`flags`).
 */

export interface SugestaoVenda {
  event_id: number;
  event_ids: number[];
  titulo: string;
  data: string | null;
  cliente: string | null;
  vendedor: string | null;
  saldo: string | null;
  motivos: string[];
}

export interface SugestaoRepasse {
  event_ids: number[];
  vendas: { event_id: number; titulo: string; data: string | null; cliente: string | null }[];
  soma: string | null;
  taxa: string | null;
  motivos: string[];
}

export interface PixRecebido {
  id: number;
  valor: string | null;
  pagador: string | null;
  conta: string | null;
  recebido_em: string;
  autenticado: boolean;
  estado: string;
  tipo_sugestao: "venda" | "repasse_infinitepay" | null;
  sugestoes: (SugestaoVenda | SugestaoRepasse)[];
  pagamento: { id: number; event_id: number; titulo: string | null; valor: string | null } | null;
  decidido_por: string | null;
  decidido_em: string | null;
  motivo: string | null;
}

export interface ListaPix {
  itens: PixRecebido[];
  contagem_conferir: number;
  flags: {
    pode_desfazer: boolean;
    pode_repasse: boolean;
    pode_resumo: boolean;
    pode_configurar: boolean;
  };
}

export interface SaudePix {
  ativo: boolean;
  ativo_desde: string | null;
  ultima_leitura: string | null;
  lidos_7d: number;
  nao_entendidos_7d: number;
  conta_nao_cadastrada_7d: number;
  contas_vistas_7d: string[];
  ultimo_erro: string | null;
  alerta: "parada" | "erro" | null;
}

export interface ResumoPorConta {
  meses: string[];
  contas: { conta: string; por_mes: Record<string, string> }[];
  sem_conta: Record<string, string>;
}

export interface ConfigPix {
  ativo: boolean;
  ativo_desde: string | null;
  pagadores_proprios: string[];
  contas: { id: number; apelido: string; numero_conta: string | null; ativa: boolean }[];
}

export type AbaPix = "conferir" | "ligados";

/** A sugestão é de repasse quando o PIX inteiro é repasse da InfinitePay (o formato muda junto). */
export function eRepasse(
  sugestao: SugestaoVenda | SugestaoRepasse,
  pix: PixRecebido,
): sugestao is SugestaoRepasse {
  return pix.tipo_sugestao === "repasse_infinitepay" && "vendas" in sugestao;
}

export function usePixLista(aba: AbaPix) {
  return useQuery({
    queryKey: ["pix", "lista", aba],
    queryFn: () => apiFetch<ListaPix>(`/api/pix?aba=${aba}`),
  });
}

export function usePixSaude() {
  return useQuery({
    queryKey: ["pix", "saude"],
    queryFn: () => apiFetch<SaudePix>("/api/pix/saude"),
    refetchInterval: 5 * 60 * 1000,
  });
}

export function usePixResumo(habilitado: boolean) {
  return useQuery({
    queryKey: ["pix", "resumo"],
    queryFn: () => apiFetch<ResumoPorConta>("/api/pix/resumo-por-conta?meses=6"),
    enabled: habilitado,
  });
}

export function usePixConfig(habilitado: boolean) {
  return useQuery({
    queryKey: ["pix", "config"],
    queryFn: () => apiFetch<ConfigPix>("/api/pix/config"),
    enabled: habilitado,
  });
}

/** Uma resposta muda a fila, o saldo da venda (Home, evento) e o sino. */
function invalidarPix(queryClient: QueryClient, eventIds: number[] = []) {
  queryClient.invalidateQueries({ queryKey: ["pix"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
  for (const id of eventIds) queryClient.invalidateQueries({ queryKey: ["event", id] });
}

function useRespostaPix<TVars extends { pixId: number }>(
  caminho: string,
  corpo: (vars: TVars) => unknown,
  eventosAfetados: (vars: TVars) => number[] = () => [],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: TVars) =>
      apiFetch<{ pix: PixRecebido }>(`/api/pix/${vars.pixId}/${caminho}`, {
        method: "POST",
        body: JSON.stringify(corpo(vars) ?? {}),
      }),
    onSettled: (_d, _e, vars) => invalidarPix(queryClient, eventosAfetados(vars)),
  });
}

/** "É esta" / "Outra venda…" (uma venda) ou, no repasse, as 1–3 vendas marcadas. */
export function useConfirmarPix() {
  return useRespostaPix<{ pixId: number; eventIds: number[] }>(
    "confirmar",
    ({ eventIds }) => ({ event_ids: eventIds }),
    ({ eventIds }) => eventIds,
  );
}

/** "Não é esta": a venda sai das sugestões deste PIX. */
export function useDescartarPix() {
  return useRespostaPix<{ pixId: number; eventId: number }>("descartar", ({ eventId }) => ({
    event_id: eventId,
  }));
}

/** "Não é de venda": o PIX sai da fila e não volta. */
export function useNaoEVendaPix() {
  return useRespostaPix<{ pixId: number }>("nao-e-venda", () => ({}));
}

/** "Desfazer" (Financeiro/Superadmin): a ligação sai; o PIX volta para conferir. */
export function useDesfazerPix() {
  return useRespostaPix<{ pixId: number; eventId?: number }>(
    "desfazer",
    () => ({}),
    ({ eventId }) => (eventId ? [eventId] : []),
  );
}

export function useSalvarConfigPix() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (corpo: Partial<Omit<ConfigPix, "ativo_desde" | "contas">> & {
      contas?: { id: number; numero_conta?: string | null; ativa?: boolean }[];
    }) => apiFetch<ConfigPix>("/api/pix/config", { method: "PATCH", body: JSON.stringify(corpo) }),
    onSuccess: (dados) => {
      queryClient.setQueryData(["pix", "config"], dados);
      queryClient.invalidateQueries({ queryKey: ["pix", "saude"] });
    },
  });
}
