import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface RhDashboard {
  can_manage_users: boolean;
}

/** Painel de RH (feature 166) — só acessível com a permissão `rh.view`. */
export function useRhDashboard() {
  return useQuery<RhDashboard>({
    queryKey: ["rh-dashboard"],
    queryFn: () => apiFetch<RhDashboard>("/api/rh/dashboard"),
  });
}
