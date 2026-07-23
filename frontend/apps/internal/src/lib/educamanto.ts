import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Linha de custo dentro de um pacote EducaManto. */
export interface EducaMantoItem {
  id: number;
  name: string;
  qty: number;
  cost_1s: number;
  cost_2s: number;
  cost_1s_days: number;
  cost_2s_days: number;
  ensemble_add: number;
}

/** Pacote de precificação do EducaManto (ex.: "Uma Aventura Animal"). */
export interface EducaMantoPackage {
  id: number;
  name: string;
  margin_1s: number;
  margin_2s: number;
  margin_1s_days: number;
  margin_2s_days: number;
  discount_days: number;
  discount_pct: number;
  commission_rate: number;
  ensemble_1s: number;
  ensemble_2s: number;
  ensemble_1s_days: number;
  ensemble_2s_days: number;
  items: EducaMantoItem[];
}

/** Distância até o endereço do evento (feature 076/171). */
export function useDistanciaEducaManto() {
  return useMutation({
    mutationFn: (endereco: string) =>
      apiFetch<{ km_ida: number }>(
        `/api/educamanto/distancia?endereco=${encodeURIComponent(endereco)}`,
      ),
  });
}

/** Lista de pacotes para o seletor da calculadora. */
export function useEducaMantoPackages() {
  return useQuery({
    queryKey: ["educamanto-packages"],
    queryFn: () => apiFetch<{ packages: EducaMantoPackage[] }>("/api/educamanto/packages"),
  });
}

/** Resultado do transporte — sempre van com carretinha, já com o multiplicador de dias (171). */
export interface TransporteResultado {
  vt: number;
  afsp: number;
  valor_viagem: number;
  dias: number;
  total: number;
  label: string;
  km_total: number;
  pessoas: number;
}

/** Linha de detalhamento de um item do pacote (formato varia por cenário 1S/2S/multi-dia). */
export interface PacoteItemRow {
  name: string;
  qty: number;
  unit_cost?: number;
  raw?: number;
  sell?: number;
  raw1?: number;
  raw2?: number;
  raw_item?: number;
  sell_item?: number;
}

/** Resultado completo do cálculo de um pacote (itens, desconto, transporte, totais). */
export interface PacoteCalculado {
  scenario: string;
  item_rows: PacoteItemRow[];
  raw_cost: number;
  valor_base: number;
  desconto_aplicado: boolean;
  desconto: number;
  transporte: TransporteResultado | null;
  valor_final_sem_nota: number;
  valor_final_com_nota: number;
}

export interface CalcularPacoteInput {
  package_id: number;
  d1: number;
  d2: number;
  ensemble: number;
  acrescimo: number;
  transporte?: { km_ida: number };
}

/** Calcula o pacote (itens/desconto) + transporte já multiplicado pelos dias (feature 171). */
export function useCalcularPacote() {
  return useMutation({
    mutationFn: (input: CalcularPacoteInput) =>
      apiFetch<PacoteCalculado>("/api/educamanto/calcular", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}
