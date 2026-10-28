import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchBlob } from "@manto/api-client";

// ══════════════════════════════════════════════════════════════════
//  Calculadora (US2)
// ══════════════════════════════════════════════════════════════════

export type PriceTable = Record<string, number[]>;

/**
 * Feature 307 — faixa de data especial da tabela de preços (ex.: 24 e 25/12). Dias em `MM-DD`
 * (valem todo ano); o markup substitui o normal; `cache` sobrescreve o cachê dos especiais
 * nomeados; `coordenador` é uma lista só (com e sem show); `piso` eleva os demais performers.
 */
export interface FaixaEspecial {
  rotulo: string;
  dias: string[];
  markup: number[];
  cache: Record<string, number[]>;
  coordenador: number[];
  piso: number[];
  nota_mensagem: string;
}

/**
 * Feature 309 — uma vaga da composição de um produto de tabela. `cache: null` = cachê pela tabela de
 * preços vigente na data do evento (teto da vaga); número = cachê fixo. `coordenador`/`maquiador`
 * têm label forçado pelo servidor ("Coordenador"/"Maquiador").
 */
export interface VagaDoProduto {
  label: string;
  tipo: "especial" | "ator" | "coordenador" | "maquiador";
  cache: number | null;
  needs_makeup: boolean;
}

/**
 * Feature 309 — produto de tabela (pacote fechado, ex.: Visita Mágica do Papai Noel): preço FIXO por
 * visita (não por duração), entra depois do markup; `por_faixa` dá o preço nas datas especiais da 307
 * (faixa sem preço = estimativa marcada); `inclui_noturno` = o +R$ 50/pessoa já está no preço.
 */
export interface ProdutoDeTabela {
  rotulo: string;
  descricao: string;
  /** 309b — "o que inclui", em itálico sob a linha do produto na mensagem e no PDF. Opcional: backend velho. */
  detalhes?: string;
  ativo: boolean;
  preco: number;
  por_faixa: Record<string, { preco: number }>;
  vagas: VagaDoProduto[];
  inclui_noturno: boolean;
}

/** Feature 309 — como estimar o produto numa faixa sem preço: Σ cachês × fator × markup. */
export interface ProdutosEstimativa {
  fator_cache: number;
  markup: number;
}

/** Feature 309 — um exemplar de produto aplicado ao orçamento (`quote.produtos`), já com o preço resolvido. */
export interface ProdutoAplicado {
  chave: string;
  rotulo: string;
  descricao: string;
  detalhes?: string;
  preco_aplicado: number;
  faixa_chave: string | null;
  estimado: boolean;
  /** Labels das vagas vendidas (personagens, coordenador, maquiador), na ordem da composição. */
  vagas: string[];
}

/** "MM-DD" (como a tabela guarda) → "DD/MM" (como o time lê) — feature 307. */
export const diaParaTela = (mmdd: string) => `${mmdd.slice(3, 5)}/${mmdd.slice(0, 2)}`;

/** "DD/MM" digitado → "MM-DD" da tabela; `null` se não for um dia. O servidor valida de novo. */
export function diaParaApi(texto: string): string | null {
  const m = /^(\d{2})\/(\d{2})$/.exec(texto.trim());
  if (!m) return null;
  const dia = Number(m[1]);
  const mes = Number(m[2]);
  if (mes < 1 || mes > 12 || dia < 1 || dia > 31) return null;
  return `${m[2]}-${m[1]}`;
}

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
    /** Caminhão de cenografia do EducaManto dentro de SP (feature 235). */
    caminhao_sp: number;
    ashow_min_km: number;
  };
  /** Custos de som/iluminação do EducaManto por combinação (feature 235, tabela única). */
  educamanto_som_luz: {
    som_luz: number;
    som: number;
    luz: number;
    nenhum: number;
  };
  acrescimo_tipos: string[];
  /**
   * Feature 307: faixas de data especial, por chave (o servidor garante ao menos `natal`).
   * Opcional no React: bundle novo pode falar com backend velho durante o deploy — ler com `?? {}`.
   */
  datas_especiais?: Record<string, FaixaEspecial>;
  /**
   * Feature 309: produtos de tabela por chave e o bloco de estimativa. Opcionais pelo mesmo motivo
   * (backend velho na janela de deploy): sem `produtos`, a calculadora não mostra o card.
   */
  produtos?: Record<string, ProdutoDeTabela>;
  produtos_estimativa?: ProdutosEstimativa;
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
  /** Feature 305 — o que o acréscimo somou ao preço em 1h..4h (o servidor grava; a tela só repassa). */
  valores_brl?: number[];
}

export interface CalcularOrcamentoInput {
  performers: Performer[];
  /** Feature 309: produtos de tabela selecionados (repetição permitida); ausente = conta de hoje. */
  produtos?: { chave: string }[];
  coordenador_qty?: number;
  fora_sp?: boolean;
  /** Só relevante com `fora_sp` — ausente/undefined equivale a "manto". */
  deslocamento_responsavel?: "manto" | "cliente";
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
  /**
   * Feature 313 — o desconto negociado: o % (modo %) OU o valor final de uma duração (modo valor). Só o campo do
   * modo ativo vai no payload; o outro a tela mostra a partir da resposta.
   */
  desconto_pct?: number;
  desconto_valor?: number;
  desconto_duracao?: DuracaoDoDesconto;
}

/** Feature 313 — a duração a que o "fechar por R$" se refere (`extra` = a duração acima de 4h). */
export type DuracaoDoDesconto = "1h" | "2h" | "3h" | "4h" | "extra";

export interface TransportBreakdown {
  transporte: number;
  adicional_fora_sp: number;
  adicional_show: number;
  total: number;
  tarifa?: number;
}

/**
 * Uma linha da memória de cálculo (`quote_ops.calculate_quote`). `valores` tem sempre 4 posições
 * — 1h, 2h, 3h e 4h. O `tipo` diz o papel da linha na conta:
 *
 * - `cache`    parcela pré-markup (cachê de cada profissional)
 * - `subtotal` soma acumulada (subtotal do cachê, valor após markup)
 * - `markup`   multiplicador aplicado — `valores` são fatores, não reais
 * - `pos`      parcela somada DEPOIS do markup (técnico, maquiador, transporte, NF, acréscimo)
 * - `produto`  preço de tabela de um produto (feature 309) — somado depois do markup, fora dele
 * - `total`    total final ao cliente
 */
export interface MemoriaLinha {
  label: string;
  detalhe: string;
  valores: number[];
  tipo: "cache" | "subtotal" | "markup" | "pos" | "produto" | "total";
}

export interface Quote {
  message: string;
  /** Ausente em orçamentos salvos antes desta feature — trate como lista vazia. */
  memoria?: MemoriaLinha[];
  transport_breakdown: TransportBreakdown | null;
  fora_sp: boolean;
  /** Ausente em orçamentos salvos antes desta feature — trate como "manto". */
  deslocamento_responsavel?: "manto" | "cliente" | null;
  markup_used: number[] | null;
  /**
   * Feature 307 — a faixa de data especial aplicada (24 e 25/12): `null` fora dela; ausente em
   * orçamentos salvos antes da feature. A nota vem junto porque o orçamento congelado não relê a tabela.
   */
  data_especial?: { chave: string; rotulo: string; markup: number[]; nota_mensagem: string } | null;
  /**
   * Feature 309 — produtos de tabela aplicados. O servidor novo manda SEMPRE as quatro chaves (vazias
   * sem produto); `produtos === undefined` quer dizer backend velho: com produto selecionado, a tela
   * trava o "Gerar Orçamento" em vez de gravar um preço sem o produto.
   */
  produtos?: ProdutoAplicado[];
  produtos_total?: number;
  coordenadores_inclusos?: number;
  /** Avisos da conta em pt-BR (Noel avulso sem produto, preço estimado, vaga sem cachê). */
  avisos?: string[];
  /**
   * Só produto no orçamento (sem avulso e sem coordenador da fórmula): UM valor, rotulado "Preço de
   * tabela". Decisão do servidor — a tela não infere pelos `show_*`. Ausente em quotes antigos.
   */
  valor_unico?: boolean;
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
  /**
   * Feature 313 — todas opcionais: ausentes em orçamento salvo antes e na janela do deploy (backend velho). A tela
   * trata ausência como "sem desconto": `bruto ?? total`, e o PIX só quando `pix_*` vier.
   */
  base_4h?: number | null;
  bruto_1h?: number;
  bruto_2h?: number;
  bruto_3h?: number;
  bruto_4h?: number;
  bruto_custom?: number | null;
  /** O % exato aplicado (o digitado ou o achado pelo valor); `null` sem desconto. */
  desconto_pct?: number | null;
  /** O % como a proposta mostra ("8,3", "10") — a fonte única do texto; a tela não recalcula. */
  desconto_pct_texto?: string | null;
  desconto_modo?: "pct" | "valor" | null;
  pix_pct?: number;
  pix_1h?: number;
  pix_2h?: number;
  pix_3h?: number;
  pix_4h?: number;
  pix_custom?: number | null;
  /** O BV a repassar a quem indicou, já com o desconto (`null` sem BV). Interno: não vai à proposta. */
  bv_1h?: number | null;
  bv_2h?: number | null;
  bv_3h?: number | null;
  bv_4h?: number | null;
  bv_custom?: number | null;
  bv_pix_1h?: number | null;
  bv_pix_2h?: number | null;
  bv_pix_3h?: number | null;
  bv_pix_4h?: number | null;
  bv_pix_custom?: number | null;
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
      // Feature 309: `avisos` (faixa órfã descartada etc.) voltam no 200 — a tela mostra sem bloquear.
      apiFetch<{ settings: PricingSettings; avisos?: string[] }>("/api/orcamento/settings", {
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
  /** feature 301 — o servidor decide quem pode excluir; a tela nunca compara ids (Princípio XIII). */
  pode_excluir: boolean;
  /** feature 273 — evento não cancelado que aponta para este orçamento ("Ver evento"). */
  event_id: number | null;
  event_title: string | null;
  /** Feature 313 — o % de desconto aplicado (o selo "−N%"); ausente/`null` sem desconto ou backend velho. */
  desconto_pct?: number | null;
}

export interface OrcamentoHistoricoResponse {
  entries: OrcamentoHistoricoEntry[];
  /** Vendedores do filtro — sempre populado desde a feature 301 (antes, só para superadmin). */
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

/**
 * Histórico de orçamentos salvos — **do time inteiro** desde a feature 301, para quem passa no
 * gate do módulo (`_require_vendas()`: COMERCIAL ou SUPERADMIN; FINANCEIRO leva 403). Não há
 * filtro por autor e a lista não nasce filtrada; `user_id` é filtro opcional disponível a
 * qualquer autorizado. A única trava de autoria que resta é o `DELETE`, e a tela a lê pela chave
 * `pode_excluir` — nunca comparando ids (Princípio XIII).
 */
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

/**
 * Estado bruto de entrada gravado junto do orçamento (`OrcamentoHistory.form_snapshot`) —
 * usado para repopular a calculadora na ação "Recalcular". Note que os campos numéricos aqui
 * vêm como `string` (é assim que o backend grava o snapshot, ver `quote_ops.calculate_quote`).
 */
export interface OrcamentoFormSnapshot {
  performers: Performer[];
  coordenador_qty: number;
  fora_sp: boolean;
  /** Ausente em snapshots salvos antes desta feature — trate como "manto". */
  deslocamento_responsavel?: "manto" | "cliente";
  km_ida: string;
  transporte_tipo: "van" | "carro";
  carretinha: boolean;
  num_carros: string;
  num_colaboradores: string;
  event_date: string;
  event_time: string;
  client_name: string;
  event_location: string;
  acrescimos: Acrescimo[];
  nota_fiscal: boolean;
  modo_duracao: "horas" | "entradas";
  duracao_custom: string;
  personalizado_ativo: boolean;
  /** Feature 309: produtos vendidos, com preço e composição congelados; ausente em snapshots antigos. */
  produtos?: {
    chave: string;
    rotulo: string;
    preco_aplicado: number;
    faixa_chave: string | null;
    estimado: boolean;
    vagas: VagaDoProduto[];
  }[];
  /** Feature 313 — o desconto como foi digitado; ausente em orçamento salvo antes (o "Recalcular" zera). */
  desconto_pct_digitado?: number | null;
  desconto_valor?: number | null;
  desconto_duracao?: DuracaoDoDesconto | null;
}

/** Detalhe congelado de um orçamento salvo, incluindo o estado bruto para "Recalcular". */
export function useOrcamentoDetalhe(id: number | null) {
  return useQuery<{ quote: Quote; form_snapshot: OrcamentoFormSnapshot }>({
    queryKey: ["orcamento-historico-detalhe", id],
    queryFn: () =>
      apiFetch<{ quote: Quote; form_snapshot: OrcamentoFormSnapshot }>(
        `/api/orcamento/historico/${id}`,
      ),
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
