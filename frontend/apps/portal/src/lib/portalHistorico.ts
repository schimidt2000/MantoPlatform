import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { PortalRole } from "./portalAgenda";

/** Uma apresentação passada, com o cachê detalhado. */
export interface PortalHistoricoItem extends PortalRole {
  cache_value: number;
  travel_cache: number;
  cache_total: number;
  payment_status: string;
}

/** Somatórios de cachê do histórico completo. */
export interface PortalHistoricoTotals {
  paid: number;
  pending: number;
  overall: number;
  count: number;
}

export interface PortalHistorico {
  items: PortalHistoricoItem[];
  totals: PortalHistoricoTotals;
}

/** Histórico completo de apresentações com somatórios de cachê recebido/pendente. */
export function useHistorico() {
  return useQuery({
    queryKey: ["portal", "historico"],
    queryFn: () => apiFetch<PortalHistorico>("/api/portal/historico"),
  });
}
