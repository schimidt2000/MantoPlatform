import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@manto/api-client";

// ══════════════════════════════════════════════════════════════════
//  Calculadora (US2)
// ══════════════════════════════════════════════════════════════════

export type PriceTable = Record<string, number[]>;

export interface PricingSettings {
  markup: { receptivo: number[]; show: number[] };
  ator: PriceTable;
  cantor: { base: number[]; show_extra: number[]; make_extra: number[] };
  tecnico_som: number[];
  coordenador: { false: number[]; true: number[] };
  especiais: Record<string, number[] | Record<string, number[]>>;
  especiais_regras: Record<string, { transporte_especial?: number; min_coordenadores?: number }>;
  brinde_show: number;
  maquiador: {
    make_1: number;
    make_2_adicional: number;
    make_extra_adicional: number;
    make_especial: number;
  };
  transporte: {
    van_com_carretinha: number;
    van_sem_carretinha: number;
    carro_por_km: number;
    afsp_divisor: number;
    ashow_divisor: number;
    ashow_min_km: number;
  };
  acrescimo_tipos: string[];
}

export interface OrcamentoOpcoes {
  especiais: string[];
  especiais_com_show: string[];
  especiais_com_cantor: string[];
  especiais_sempre_show: string[];
  acrescimo_tipos: string[];
  acrescimo_tipo_bv: string;
  settings: PricingSettings;
}

/** Opções da calculadora (especiais, acréscimos, preços vigentes). */
export function useOrcamentoOpcoes() {
  return useQuery<OrcamentoOpcoes>({
    queryKey: ["orcamento-opcoes"],
    queryFn: () => apiFetch<OrcamentoOpcoes>("/api/orcamento/opcoes"),
  });
}

export interface Performer {
  type: "ator" | "cantor" | "especial";
  subtipo?: "cara_limpa" | "boneco" | "cantor";
  personagem?: string;
  nome?: string;
  show?: boolean;
  makeup?: boolean;
  makeup_tipo?: "comum" | "especial";
  cantor?: boolean;
  bge_subtipo?: "dinossauro" | "transformers" | "outro" | "";
  bge_outro_nome?: string;
}

export interface Acrescimo {
  tipo: string;
  descricao?: string;
  value: number;
  is_percent: boolean;
}

export interface CalcularOrcamentoInput {
  performers: Performer[];
  coordenador_qty?: number;
  fora_sp?: boolean;
  event_time?: string;
  acrescimos?: Acrescimo[];
  show_sosia_tipo?: "predefinido" | "customizado";
  nota_fiscal?: boolean;
  modo_duracao?: "horas" | "entradas";
  duracao_custom?: number;
  km_ida?: number;
  transporte_tipo?: "van" | "carro";
  num_colaboradores?: number;
  carretinha?: boolean;
  num_carros?: number;
  personalizado?: boolean;
  personalizado_criterio?: "multiplicador" | "valor_final";
  cust_mult_1h?: string;
  cust_mult_2h?: string;
  cust_mult_3h?: string;
  cust_mult_4h?: string;
  cust_valor_1h?: string;
  cust_valor_2h?: string;
  cust_valor_3h?: string;
  cust_valor_4h?: string;
  incluir_duracao?: string[];
  event_date?: string;
  client_name?: string;
  event_location?: string;
}

export interface TransportBreakdown {
  transporte: number;
  adicional_fora_sp: number;
  adicional_show: number;
  total: number;
  tarifa?: number;
}

export interface Quote {
  message: string;
  transport_breakdown: TransportBreakdown | null;
  fora_sp: boolean;
  markup_used: number[] | null;
  total_1h: number;
  total_2h: number;
  total_3h: number;
  total_4h: number;
  total_custom: number | null;
  duracao_custom: number;
  show_1h: boolean;
  show_2h: boolean;
  show_3h: boolean;
  show_4h: boolean;
  client_name: string;
  fmt_date: string;
  fmt_time: string;
  event_location: string;
  team_lines: string[];
  nota_fiscal: boolean;
  modo_duracao: string;
  personalizado: boolean;
  personalizado_criterio: string | null;
  cache_base: number[] | null;
  custom_mult: number[] | null;
}

export interface CalcularOrcamentoResult {
  quote: Quote;
  snapshot: Record<string, unknown>;
}

/** Calcula um orçamento — não persiste (feature 177, US2). */
export function useCalcularOrcamento() {
  return useMutation({
    mutationFn: (input: CalcularOrcamentoInput) =>
      apiFetch<CalcularOrcamentoResult>("/api/orcamento/calcular", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

/** Persiste um orçamento já calculado no histórico. */
export function useSalvarOrcamento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CalcularOrcamentoResult) =>
      apiFetch<{ id: number }>("/api/orcamento/salvar", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orcamento-historico"] }),
  });
}

export interface PersonagemNoDia {
  nome: string;
  eventos: string[];
}

/** Personagens já escalados em eventos na data informada (evita venda duplicada). */
export function usePersonagensNoDia(date: string) {
  return useQuery<{ date: string | null; personagens: PersonagemNoDia[] }>({
    queryKey: ["orcamento-personagens-no-dia", date],
    queryFn: () =>
      apiFetch<{ date: string | null; personagens: PersonagemNoDia[] }>(
        `/api/orcamento/personagens-no-dia?date=${date}`,
      ),
    enabled: Boolean(date),
  });
}

/** Distância (km, ida) via Google Maps, para o cálculo de transporte. */
export function useDistancia() {
  return useMutation({
    mutationFn: (endereco: string) =>
      apiFetch<{ km_ida: number }>(`/api/orcamento/distancia?endereco=${encodeURIComponent(endereco)}`),
  });
}

// ══════════════════════════════════════════════════════════════════
//  Configuração de Preços (US5)
// ══════════════════════════════════════════════════════════════════

export interface OrcamentoSettingsResponse {
  settings: PricingSettings;
  default_especiais: string[];
}

/** Configuração de preços vigente (SUPERADMIN). */
export function useOrcamentoSettings() {
  return useQuery<OrcamentoSettingsResponse>({
    queryKey: ["orcamento-settings"],
    queryFn: () => apiFetch<OrcamentoSettingsResponse>("/api/orcamento/settings"),
  });
}

/** Salva a configuração de preços (parcial ou completa). */
export function useSaveOrcamentoSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<PricingSettings>) =>
      apiFetch<{ settings: PricingSettings }>("/api/orcamento/settings", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orcamento-settings"] }),
  });
}

/** Adiciona um item especial novo à tabela de preços. */
export function useAddEspecial() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { nome: string; prices: number[] }) =>
      apiFetch<{ settings: PricingSettings }>("/api/orcamento/settings/especiais", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orcamento-settings"] }),
  });
}

/** Remove um item especial da tabela de preços. */
export function useRemoveEspecial() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      apiFetch<void>(`/api/orcamento/settings/especiais/${encodeURIComponent(nome)}`, {
        method: "DELETE",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orcamento-settings"] }),
  });
}

// ══════════════════════════════════════════════════════════════════
//  Histórico + PDF (US4)
// ══════════════════════════════════════════════════════════════════

export interface OrcamentoHistoricoEntry {
  id: number;
  created_at: string;
  client_name: string;
  event_location: string;
  event_date: string;
  total_1h: number;
  total_2h: number;
  total_3h: number;
  total_4h: number;
  has_show: boolean;
  user_name: string | null;
}

export interface OrcamentoHistoricoResponse {
  entries: OrcamentoHistoricoEntry[];
  is_superadmin: boolean;
  users: { id: number; name: string }[];
}

export interface OrcamentoHistoricoFilters {
  q?: string;
  date_from?: string;
  date_to?: string;
  min_val?: string;
  max_val?: string;
  user_id?: string;
  has_show?: string;
}

/** Histórico de orçamentos salvos — SUPERADMIN vê todos, demais só os próprios. */
export function useOrcamentoHistorico(filters: OrcamentoHistoricoFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const qs = params.toString();
  return useQuery<OrcamentoHistoricoResponse>({
    queryKey: ["orcamento-historico", qs],
    queryFn: () => apiFetch<OrcamentoHistoricoResponse>(`/api/orcamento/historico${qs ? `?${qs}` : ""}`),
  });
}

/** Detalhe congelado de um orçamento salvo. */
export function useOrcamentoDetalhe(id: number | null) {
  return useQuery<{ quote: Quote }>({
    queryKey: ["orcamento-historico-detalhe", id],
    queryFn: () => apiFetch<{ quote: Quote }>(`/api/orcamento/historico/${id}`),
    enabled: id != null,
  });
}

/** Baixa o PDF de um orçamento do histórico — dispara o download via blob. */
export function useOrcamentoPdf() {
  return useMutation({
    mutationFn: async ({ id, clientName }: { id: number; clientName: string }) => {
      const blob = await apiFetchBlob(`/api/orcamento/historico/${id}/pdf`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Orcamento_Manto_${clientName.replace(/\s+/g, "_") || "orcamento"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
  });
}

/** Envia o PDF de um orçamento do histórico por e-mail. */
export function useEnviarEmailOrcamento() {
  return useMutation({
    mutationFn: ({ id, to }: { id: number; to: string }) =>
      apiFetch<{ sent: boolean }>(`/api/orcamento/historico/${id}/enviar-email`, {
        method: "POST",
        body: JSON.stringify({ to }),
      }),
  });
}

/** Exclui um orçamento do histórico. */
export function useDeleteOrcamentoHistorico() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/orcamento/historico/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orcamento-historico"] }),
  });
}
