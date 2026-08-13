import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@manto/api-client";

// ─────────────────────────────────────────────────────────────────────────────
// Feature 235: EducaManto por responsabilidades. Os pacotes por nível morreram —
// o cadastro é por MUSICAL e o orçamento marca cada bloco (som/iluminação/
// alimentação/cenário) como "manto" ou "contratante". Todo cálculo é do servidor;
// o breakdown de custos só vem na resposta de SUPERADMIN.
// ─────────────────────────────────────────────────────────────────────────────

export type Responsavel = "manto" | "contratante";

export type ResponsabilidadeChave = "som" | "iluminacao" | "alimentacao" | "cenario";

export type Responsabilidades = Record<ResponsabilidadeChave, Responsavel>;

export const RESPONSABILIDADES_PADRAO: Responsabilidades = {
  som: "manto",
  iluminacao: "manto",
  alimentacao: "manto",
  cenario: "manto",
};

/** Linha de custo sempre inclusa de um musical (elenco, produção, gráfica…). */
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

/** Payload básico de um musical — SEM custos (é o que a calculadora recebe). */
export interface EducaMantoMusicalBasico {
  id: number;
  name: string;
  num_personagens: number;
  num_producao: number;
  num_ensaios: number;
}

/** Musical completo (custos/margens/itens) — só chega para SUPERADMIN. */
export interface EducaMantoMusical extends EducaMantoMusicalBasico {
  margin_1s: number;
  margin_2s: number;
  margin_1s_days: number;
  margin_2s_days: number;
  discount_days: number;
  discount_pct: number;
  ensemble_1s: number;
  ensemble_2s: number;
  ensemble_1s_days: number;
  ensemble_2s_days: number;
  custo_som_1s: number;
  custo_som_2s: number;
  custo_som_1s_days: number;
  custo_som_2s_days: number;
  custo_iluminacao_1s: number;
  custo_iluminacao_2s: number;
  custo_iluminacao_1s_days: number;
  custo_iluminacao_2s_days: number;
  custo_cenario_1s: number;
  custo_cenario_2s: number;
  custo_cenario_1s_days: number;
  custo_cenario_2s_days: number;
  custo_alimentacao_1s: number;
  custo_alimentacao_2s: number;
  custo_catering_ensaio_pp: number;
  custo_ajuda_ensaio_pp: number;
  items: EducaMantoItem[];
}

const MUSICALS_QUERY_KEY = ["educamanto-musicals"];

/** Lista de musicais para o seletor da calculadora (payload básico, sem custos). */
export function useMusicals() {
  return useQuery({
    queryKey: MUSICALS_QUERY_KEY,
    queryFn: () =>
      apiFetch<{ musicals: EducaMantoMusicalBasico[]; pode_gerir: boolean }>(
        "/api/educamanto/musicals",
      ),
  });
}

/** Lista de gestão (tela de musicais): custos/margens só vêm para SUPERADMIN. */
export function useMusicalsGestao() {
  return useQuery({
    queryKey: [...MUSICALS_QUERY_KEY, "gestao"],
    queryFn: () =>
      apiFetch<{
        musicals: (EducaMantoMusicalBasico | EducaMantoMusical)[];
        pode_gerir: boolean;
      }>("/api/educamanto/musicals?gestao=1"),
  });
}

/** Musical completo para o formulário de edição — SÓ superadmin. */
export function useMusicalDetalhe(id: number | null) {
  return useQuery<EducaMantoMusical>({
    queryKey: [...MUSICALS_QUERY_KEY, "detalhe", id],
    queryFn: () => apiFetch<EducaMantoMusical>(`/api/educamanto/musicals/${id}`),
    enabled: id != null,
  });
}

/** Rótulos e tooltips das responsabilidades — fonte única no backend (`pdf_textos.py`). */
export function useEducaMantoTextos() {
  return useQuery({
    queryKey: ["educamanto-textos"],
    queryFn: () =>
      apiFetch<{
        ordem: ResponsabilidadeChave[];
        responsabilidades: Record<ResponsabilidadeChave, { label: string; tooltip: string }>;
      }>("/api/educamanto/textos"),
    staleTime: Infinity,
  });
}

/** Distância até o endereço do evento. */
export function useDistanciaEducaManto() {
  return useMutation({
    mutationFn: (endereco: string) =>
      apiFetch<{ km_ida: number }>(
        `/api/educamanto/distancia?endereco=${encodeURIComponent(endereco)}`,
      ),
  });
}

/** Transporte da configuração: caminhão dentro de SP ou 2 vans fora de SP (feature 235). */
export interface TransporteInfo {
  modo: "caminhao_sp" | "vans_fora_sp";
  total: number;
  /** Custo do caminhão (já dentro da base) — só na resposta de superadmin. */
  caminhao?: number;
  valor_viagem: number;
  dias: number;
  km_total: number;
  pessoas: number;
}

export interface ConfigItemRow {
  name: string;
  qty: number;
  raw: number;
  sell: number;
}

/** Breakdown interno — presente APENAS na resposta de SUPERADMIN. */
export interface ConfigBreakdown {
  item_rows: ConfigItemRow[];
  blocos: Partial<Record<string, number>>;
  raw_cost: number;
  valor_base: number;
  desconto: number;
  liquido: number;
  contratacao_memoria: unknown[];
}

/** Total combinado (EducaManto + contratação Manto) de uma duração. */
export interface TotalCombinado {
  sem_nota: number;
  com_nota: number;
  a_vista_sem: number;
  a_vista_com: number;
}

/** Resultado do cálculo de uma configuração (uma página do orçamento). */
export interface ConfigCalculada {
  scenario: string;
  headcount: number;
  headcount_ensaio: number;
  tecnicos: string[];
  transporte: TransporteInfo | null;
  valor_final_sem_nota: number;
  valor_final_com_nota: number;
  a_vista_sem_nota: number;
  a_vista_com_nota: number;
  /** Comissão que de fato entrou — pode ser menor que a digitada (teto da configuração). */
  acrescimo_efetivo: number;
  /** Teto da comissão: o valor da configuração sem transporte. */
  acrescimo_maximo: number;
  /** `true` quando o teto cortou o valor digitado — a tela precisa avisar. */
  acrescimo_capado: boolean;
  desconto_aplicado: boolean;
  combinados: Record<string, TotalCombinado>;
  breakdown?: ConfigBreakdown;
}

/** Entradas da contratação Manto embutida (payload da calculadora de eventos + durações). */
export interface ContratacaoMantoInput {
  duracoes: string[];
  payload: Record<string, unknown>;
}

/** Entradas de UMA configuração — é isso (e só isso) que o servidor aceita. */
export interface ConfigInput {
  musical_id: number;
  d1: number;
  d2: number;
  ensemble: number;
  responsabilidades: Responsabilidades;
  fora_sp: boolean;
  km_ida?: number | null;
  acrescimo: number;
  contratacao_manto?: ContratacaoMantoInput | null;
}

/** Calcula uma configuração no servidor (nada é persistido). */
export function useCalcularConfig() {
  return useMutation({
    mutationFn: (input: ConfigInput) =>
      apiFetch<ConfigCalculada>("/api/educamanto/calcular", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export interface PersonagemNoDia {
  nome: string;
  eventos: string[];
}

/** Personagens já escalados na data da apresentação — evita vender o mesmo em dobro. */
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

/** Campos de um musical enviados ao criar/editar — sem `id` (gerado pelo servidor). */
export interface MusicalInput {
  name: string;
  num_personagens: number;
  num_producao: number;
  num_ensaios: number;
  margin_1s: number;
  margin_2s: number;
  margin_1s_days: number;
  margin_2s_days: number;
  discount_days: number;
  discount_pct: number;
  ensemble_1s: number;
  ensemble_2s: number;
  ensemble_1s_days: number;
  ensemble_2s_days: number;
  custo_som_1s: number;
  custo_som_2s: number;
  custo_som_1s_days: number;
  custo_som_2s_days: number;
  custo_iluminacao_1s: number;
  custo_iluminacao_2s: number;
  custo_iluminacao_1s_days: number;
  custo_iluminacao_2s_days: number;
  custo_cenario_1s: number;
  custo_cenario_2s: number;
  custo_cenario_1s_days: number;
  custo_cenario_2s_days: number;
  custo_alimentacao_1s: number;
  custo_alimentacao_2s: number;
  custo_catering_ensaio_pp: number;
  custo_ajuda_ensaio_pp: number;
  items: Omit<EducaMantoItem, "id">[];
}

/** Cria um musical (SuperAdmin). */
export function useCreateMusical() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MusicalInput) =>
      apiFetch<EducaMantoMusical>("/api/educamanto/musicals", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MUSICALS_QUERY_KEY });
    },
  });
}

/** Atualiza um musical, substituindo a lista de itens (SuperAdmin). */
export function useUpdateMusical(musicalId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MusicalInput) =>
      apiFetch<EducaMantoMusical>(`/api/educamanto/musicals/${musicalId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MUSICALS_QUERY_KEY });
    },
  });
}

/** Duplica um musical, prefixando o nome com "Cópia de " (SuperAdmin). */
export function useDuplicateMusical() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (musicalId: number) =>
      apiFetch<EducaMantoMusical>(`/api/educamanto/musicals/${musicalId}/duplicate`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MUSICALS_QUERY_KEY });
    },
  });
}

/** Exclui um musical — ação destrutiva, confirmar antes de chamar (SuperAdmin). */
export function useDeleteMusical() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (musicalId: number) =>
      apiFetch<void>(`/api/educamanto/musicals/${musicalId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MUSICALS_QUERY_KEY });
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

/** Corpo do `POST /api/educamanto/orcamento/gerar` — só ENTRADAS; o servidor recalcula tudo. */
export interface GerarOrcamentoInput {
  configs: ConfigInput[];
  client_name?: string;
  event_date?: string;
  /** Texto livre do vendedor (até 2.000 caracteres) — sai formatado no PDF. */
  observacao?: string;
}

/** Gera o PDF (uma página por configuração), salva no histórico e baixa automaticamente. */
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

/** Reabre o PDF de um orçamento do histórico (valores congelados na geração). */
export function useOrcamentoPdf() {
  return useMutation({
    mutationFn: async (quoteId: number) => {
      const blob = await apiFetchBlob(`/api/educamanto/orcamento/${quoteId}/pdf`);
      downloadBlob(blob, `orcamento-educamanto-${quoteId}.pdf`);
    },
  });
}

/** Uma entrada do histórico de orçamentos gerados. */
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

/** Snapshot v1 (LEGADO, pré-feature 235) — formato de pacotes por nível. */
export interface SnapshotV1 {
  version?: undefined;
  d1: number;
  d2: number;
  ensemble: number;
  acrescimo: number;
  transporte: {
    total: number;
    label: string;
    /** Ida e volta — o que o PDF mostra. NÃO use para repopular o campo de km. */
    kmT: number | null;
    /** Distância de IDA, a entrada real do cálculo (derivada de kmT nos antigos). */
    km_ida: number | null;
    pessoas: number | null;
  } | null;
  client_name: string;
  event_date?: string | null;
  packages: { id: number; name: string; sem_nota: number; com_nota: number }[];
}

/** Configuração congelada de um snapshot v2 (entradas + resultado do servidor). */
export interface SnapshotV2Config {
  musical_id: number;
  musical_name: string;
  num_personagens: number;
  num_producao: number;
  num_ensaios: number;
  d1: number;
  d2: number;
  ensemble: number;
  responsabilidades: Responsabilidades;
  fora_sp: boolean;
  km_ida: number | null;
  acrescimo: number;
  contratacao_manto: {
    inputs: Record<string, unknown>;
    duracoes: string[];
    totais: Record<string, number>;
    team_lines: string[];
  } | null;
  resultado: {
    scenario: string;
    headcount: number;
    headcount_ensaio: number;
    tecnicos: string[];
    transporte: TransporteInfo | null;
    sem_nota: number;
    com_nota: number;
    a_vista_sem_nota: number;
    a_vista_com_nota: number;
    acrescimo_efetivo: number;
    desconto_aplicado: boolean;
    combinados: Record<string, TotalCombinado>;
  };
}

/** Snapshot v2 (feature 235) — multi-configuração, recalculado no servidor. */
export interface SnapshotV2 {
  version: 2;
  client_name: string;
  event_date: string | null;
  observacao: string;
  configs: SnapshotV2Config[];
}

export type EducaMantoQuoteSnapshot = SnapshotV1 | SnapshotV2;

export function isSnapshotV2(snap: EducaMantoQuoteSnapshot): snap is SnapshotV2 {
  return (snap as SnapshotV2).version === 2;
}

/** Detalhe de um orçamento salvo — mesmo dado usado para regerar o PDF, exposto em JSON. */
export function useEducaMantoQuoteDetalhe(id: number | null) {
  return useQuery<EducaMantoQuoteSnapshot>({
    queryKey: ["educamanto-historico-detalhe", id],
    queryFn: () => apiFetch<EducaMantoQuoteSnapshot>(`/api/educamanto/historico/${id}`),
    enabled: id != null,
  });
}

/** Histórico de orçamentos gerados, com busca/filtros — "Gerado por" só p/ SuperAdmin. */
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
