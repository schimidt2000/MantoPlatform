import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Item do pipeline de vendas (feature 156). */
export interface VendasPipelineItem {
  event_id: number;
  title: string;
  group_label: string | null;
  location: string | null;
  sale_date: string | null;
  sale_value: number;
  custo: number;
  comissao: number;
  with_invoice: boolean;
  lucro?: number;
}

export interface VendasPipeline {
  items: VendasPipelineItem[];
  is_financeiro: boolean;
}

/** Pipeline de vendas (feature 156) — Comercial/Financeiro/Superadmin ou resp. EducaManto. */
export function useVendasPipeline() {
  return useQuery<VendasPipeline>({
    queryKey: ["vendas-pipeline"],
    queryFn: () => apiFetch<VendasPipeline>("/api/vendas/pipeline"),
  });
}
