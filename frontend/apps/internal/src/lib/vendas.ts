import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { LojaVirtualResumo, PeriodFilter } from "./financeiro";

/** Situação do contrato do evento — derivada de `EventContract` no servidor (feature 196). */
export type ContractStatus = "assinado" | "pendente" | "sem_contrato";

/** Situação de recebimento — mesma régua do Painel Financeiro (fonte única em `vendas_ops`). */
export type SalePaymentStatus =
  | "permuta"
  | "sem_valor"
  | "pago_total"
  | "parcial"
  | "pendente";

/** Uma venda fechada no período (feature 196). Sem custo/lucro — isso é do Financeiro. */
export interface VendaFechada {
  event_id: number;
  title: string;
  /** Rótulo do grupo comercial quando o evento é o principal de um grupo. */
  group_label: string | null;
  client_name: string | null;
  /** Data do evento (`start_at`). */
  event_date: string | null;
  /** Data em que a venda foi fechada (`sale_date`), quando preenchida. */
  sale_date: string | null;
  /** Eixo do período: `sale_date` ou, na falta dela, a data do evento. */
  closing_date: string | null;
  sale_value: number;
  /** Preço de tabela antes do desconto — `null` quando não houve desconto registrado. */
  sale_value_gross: number | null;
  seller_id: number | null;
  seller_name: string | null;
  contract_status: ContractStatus;
  contract_status_label: string;
  payment_status: SalePaymentStatus;
  payment_status_label: string;
  comissao: number;
  is_permuta: boolean;
}

/** KPIs comerciais do período — somados no servidor sobre o escopo do usuário logado. */
export interface VendasKpis {
  total_vendido: number;
  ticket_medio: number;
  eventos_fechados: number;
  comissao_prevista: number;
  desconto_concedido: number;
}

export interface VendedorOption {
  id: number;
  name: string;
}

export interface DashboardComercial {
  period: PeriodFilter;
  period_label: string;
  start: string;
  end: string;
  /** Gestor (Financeiro/Superadmin): vê a empresa toda e pode filtrar por vendedor. */
  can_filter_seller: boolean;
  seller_id: number | null;
  /** "Empresa toda" ou "Minhas vendas" — quem decide é o servidor. */
  scope_label: string;
  kpis: VendasKpis;
  eventos: VendaFechada[];
  /** Só chega para gestor. */
  sellers?: VendedorOption[];
  /**
   * Consolidado da Loja de Interações Virtuais (feature 205, FR-054/FR-055).
   *
   * Só chega para gestor. Vendedor comum não recebe: essas vendas se fecham sozinhas, sem
   * vendedor, e apareceriam como meta que ninguém bateu no funil de quem vende de verdade.
   */
  loja_virtual?: LojaVirtualResumo;
  /** Reflete o opt-in explícito do gestor (FR-055) — por padrão `false`. */
  incluir_loja_virtual?: boolean;
}

export interface DashboardComercialParams {
  period: PeriodFilter;
  sellerId: number | null;
  /**
   * Opt-in do gestor para trazer a Loja Virtual para dentro do funil (FR-055). O servidor ignora
   * o parâmetro para vendedor comum — a decisão de escopo nunca é do cliente.
   */
  incluirLojaVirtual?: boolean;
}

/**
 * Dashboard Comercial (feature 196) — Comercial/Financeiro/Superadmin ou resp. EducaManto.
 *
 * O `sellerId` é uma preferência: o servidor ignora o parâmetro para quem não é gestor e
 * devolve sempre as próprias vendas.
 */
export function useDashboardComercial({
  period,
  sellerId,
  incluirLojaVirtual = false,
}: DashboardComercialParams) {
  const params = new URLSearchParams({ period });
  if (sellerId !== null) params.set("seller_id", String(sellerId));
  if (incluirLojaVirtual) params.set("incluir_loja_virtual", "1");
  return useQuery<DashboardComercial>({
    queryKey: ["vendas-dashboard", period, sellerId, incluirLojaVirtual],
    queryFn: () => apiFetch<DashboardComercial>(`/api/vendas/pipeline?${params.toString()}`),
  });
}
