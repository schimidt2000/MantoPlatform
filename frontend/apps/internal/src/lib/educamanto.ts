import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@manto/api-client";

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

const PACKAGES_QUERY_KEY = ["educamanto-packages"];

/** Lista de pacotes para o seletor da calculadora. */
export function useEducaMantoPackages() {
  return useQuery({
    queryKey: PACKAGES_QUERY_KEY,
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
  /** Comissão que de fato entrou na conta — pode ser menor que a digitada (teto do pacote). */
  acrescimo_efetivo: number;
  /** Teto da comissão: o valor do pacote sem transporte. */
  acrescimo_maximo: number;
  /** `true` quando o teto cortou o valor digitado — a tela precisa avisar. */
  acrescimo_capado: boolean;
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

export interface PersonagemNoDia {
  nome: string;
  eventos: string[];
}

/**
 * Personagens já escalados na data da apresentação — mesmo aviso da Calculadora de Orçamento,
 * atrás do gate do EducaManto (o endpoint de `/api/orcamento` é restrito a Comercial/Superadmin
 * e deixaria Ensaio e Revendedor sem o alerta).
 */
export function usePersonagensNoDiaEducaManto(date: string) {
  return useQuery<{ date: string | null; personagens: PersonagemNoDia[] }>({
    queryKey: ["educamanto-personagens-no-dia", date],
    queryFn: () =>
      apiFetch<{ date: string | null; personagens: PersonagemNoDia[] }>(
        `/api/educamanto/personagens-no-dia?date=${date}`,
      ),
    enabled: Boolean(date),
  });
}

/** Campos de um pacote enviados ao criar/editar (feature 175) — sem `id` (gerado pelo servidor). */
export interface PackageInput {
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
  items: Omit<EducaMantoItem, "id">[];
}

/** Cria um pacote educacional (feature 175, US2 — SuperAdmin). */
export function useCreatePackage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PackageInput) =>
      apiFetch<EducaMantoPackage>("/api/educamanto/packages", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PACKAGES_QUERY_KEY });
    },
  });
}

/** Atualiza um pacote existente, substituindo a lista de itens (feature 175, US2). */
export function useUpdatePackage(pkgId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PackageInput) =>
      apiFetch<EducaMantoPackage>(`/api/educamanto/packages/${pkgId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PACKAGES_QUERY_KEY });
    },
  });
}

/** Duplica um pacote (parâmetros + itens), prefixando o nome com "Cópia de " (feature 175). */
export function useDuplicatePackage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pkgId: number) =>
      apiFetch<EducaMantoPackage>(`/api/educamanto/packages/${pkgId}/duplicate`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PACKAGES_QUERY_KEY });
    },
  });
}

/** Exclui um pacote educacional — ação destrutiva, confirmar antes de chamar (feature 175). */
export function useDeletePackage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pkgId: number) =>
      apiFetch<void>(`/api/educamanto/packages/${pkgId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PACKAGES_QUERY_KEY });
    },
  });
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Corpo enviado para gerar um orçamento (mesmo shape do `POST /educamanto/orcamento/gerar` legado). */
export interface GerarOrcamentoInput {
  packages: { id: number; name: string; sem_nota: number; com_nota: number }[];
  d1: number;
  d2: number;
  ensemble: number;
  acrescimo: number;
  transporte?: { total: number; label: string; kmT?: number; pessoas?: number };
  client_name?: string;
  /** Distância de IDA — é a entrada real do cálculo, o `kmT` é ida e volta (só exibição). */
  km_ida?: number;
  /** Data da apresentação (ISO), usada pelo alerta de personagens já escalados no dia. */
  event_date?: string;
}

/** Gera o PDF do orçamento, salva no histórico e baixa automaticamente (feature 175, US1). */
export function useGerarOrcamento() {
  return useMutation({
    mutationFn: async (input: GerarOrcamentoInput) => {
      const blob = await apiFetchBlob("/api/educamanto/orcamento/gerar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      downloadBlob(blob, "orcamento-educamanto.pdf");
    },
  });
}

/** Reabre o PDF de um orçamento do histórico (valores congelados na geração — feature 175, US3). */
export function useOrcamentoPdf() {
  return useMutation({
    mutationFn: async (quoteId: number) => {
      const blob = await apiFetchBlob(`/api/educamanto/orcamento/${quoteId}/pdf`);
      downloadBlob(blob, `orcamento-educamanto-${quoteId}.pdf`);
    },
  });
}

/** Uma entrada do histórico de orçamentos gerados (feature 175, US3). */
export interface EducaMantoHistoricoEntry {
  id: number;
  created_at: string;
  client_name: string | null;
  packages_label: string | null;
  user_name?: string;
}

export interface EducaMantoHistoricoFiltros {
  q?: string;
  date_from?: string;
  date_to?: string;
  user_id?: string;
}

/** Snapshot bruto de um orçamento EducaManto salvo — usado por "Ver" e "Recalcular". */
export interface EducaMantoQuoteSnapshot {
  d1: number;
  d2: number;
  ensemble: number;
  acrescimo: number;
  transporte: {
    total: number;
    label: string;
    /** Ida e volta — o que o PDF mostra. NÃO use para repopular o campo de km. */
    kmT: number | null;
    /** Distância de IDA, a entrada real do cálculo. O servidor deriva de `kmT` nos snapshots antigos. */
    km_ida: number | null;
    pessoas: number | null;
  };
  client_name: string;
  event_date?: string | null;
  packages: { id: number; name: string; sem_nota: number; com_nota: number }[];
}

/** Detalhe de um orçamento salvo — mesmo dado usado para regerar o PDF, exposto em JSON. */
export function useEducaMantoQuoteDetalhe(id: number | null) {
  return useQuery<EducaMantoQuoteSnapshot>({
    queryKey: ["educamanto-historico-detalhe", id],
    queryFn: () => apiFetch<EducaMantoQuoteSnapshot>(`/api/educamanto/historico/${id}`),
    enabled: id != null,
  });
}

/** Histórico de orçamentos gerados, com busca/filtros — "Gerado por" só visível a SuperAdmin. */
export function useEducaMantoHistorico(filtros: EducaMantoHistoricoFiltros) {
  const params = new URLSearchParams();
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.date_from) params.set("date_from", filtros.date_from);
  if (filtros.date_to) params.set("date_to", filtros.date_to);
  if (filtros.user_id) params.set("user_id", filtros.user_id);
  const qs = params.toString();

  return useQuery({
    queryKey: ["educamanto-historico", filtros],
    queryFn: () =>
      apiFetch<{
        entries: EducaMantoHistoricoEntry[];
        users?: { id: number; name: string }[];
      }>(`/api/educamanto/historico${qs ? `?${qs}` : ""}`),
  });
}
