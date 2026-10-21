import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";
import { invalidarDestinoDeFormulario } from "./formulariosAdmin";

/** Ficha de figurino selecionável no elenco — `photo_url` alimenta a miniatura quadrada da busca. */
export interface FigurinoSheetOption {
  id: number;
  character_name: string;
  photo_url: string | null;
}

/** Talento pré-escalável — `photo_face_path` alimenta o avatar circular da busca (feature 195). */
export interface AssignableTalent {
  id: number;
  name: string;
  photo_face_path: string | null;
}

/** Opções do formulário de criação de evento (feature 152) — `GET /api/events/new/options`. */
export interface EventCreateOptions {
  figurino_sheets: FigurinoSheetOption[];
  sellers: { id: number; name: string }[];
  assignable_talents: AssignableTalent[];
  client_relation_tipos: string[];
}

export function useEventCreateOptions() {
  return useQuery<EventCreateOptions>({
    queryKey: ["event-create-options"],
    queryFn: () => apiFetch<EventCreateOptions>("/api/events/new/options"),
    staleTime: 5 * 60 * 1000,
  });
}

/** Cachê de um item do orçamento, por duração (feature 152). */
export interface OrcamentoCache {
  label: string;
  cache_1h: number;
  cache_2h: number;
  cache_3h: number;
  cache_4h: number;
  /** Régua da duração extra do orçamento (>4h) — informativo; a criação recalcula no servidor (feature 236). */
  cache_custom?: number;
  needs_makeup: boolean;
  is_singer: boolean;
  role_type: string;
}

/** Pré-preenchimento a partir de um orçamento salvo — `GET /api/events/new/prefill`. */
export interface OrcamentoPrefill {
  orcamento_id?: number;
  date?: string;
  start_time?: string;
  location?: string;
  client_name?: string;
  total_1h?: number;
  total_2h?: number;
  total_3h?: number;
  total_4h?: number;
  total_custom?: number | null;
  duracao_custom?: number | null;
  /** Feature 313 (só orçamento novo; o de antes não traz): o preço cheio, antes do desconto. */
  bruto_1h?: number;
  bruto_2h?: number;
  bruto_3h?: number;
  bruto_4h?: number;
  bruto_custom?: number | null;
  desconto_pct?: number | null;
  /** Feature 313: o preço de 5 a 24 h pela conta da calculadora, do servidor (ausente no personalizado). */
  extra_por_horas?: Record<string, { bruto: number; total: number }>;
  has_show?: boolean;
  transport_value?: number;
  acrescimo_value?: number;
  acrescimos?: unknown[];
  /** Feature 305: o que cada acréscimo somou ao preço, por duração (o BV CHEIO), do servidor. */
  acrescimos_do_orcamento?: AcrescimosDoOrcamento;
  with_invoice?: boolean;
  caches?: OrcamentoCache[];
}

/** Feature 305 — `acrescimos_do_orcamento` do prefill. Nenhuma conta de dinheiro no navegador. */
export interface AcrescimosDoOrcamento {
  personalizado: boolean;
  linhas: {
    tipo: string;
    descricao: string;
    is_bv: boolean;
    percentual: number | null;
    valores_brl: { "1": number | null; "2": number | null; "3": number | null; "4": number | null; custom: number | null };
    /** Feature 313: o que a linha vale com o desconto (a venda = o total do orçamento), do servidor. */
    valores_final?: { "1": number | null; "2": number | null; "3": number | null; "4": number | null; custom: number | null };
  }[];
  /** Feature 305 (converge): a proporção do BV é entre líquidos — a nota do orçamento e o 0,84 do
   * servidor. Opcionais: o backend antigo não manda (aí a tela compara brutos, como antes). */
  nota_do_orcamento?: boolean;
  divisor_da_nota?: number;
}

/**
 * Feature 313: o preço cheio e o final de uma duração do orçamento (o cheio vai para `sale_value_gross`, o final
 * para `sale_value`). Números do servidor: 1–4 h e, no orçamento novo, 5–24 h pelo `extra_por_horas`. Orçamento de
 * antes: o `total_custom` quando a duração bate, senão a régua de sempre (4 h ÷ 4 × horas) — só sugestão, editável;
 * sem cheio separado, o cheio é o próprio total. `null` = fora do que o orçamento novo cobre (acima de 24 h).
 */
export function precoDaDuracao(p: OrcamentoPrefill, horas: number): { bruto: number; total: number } | null {
  if (horas >= 1 && horas <= 4) {
    const total = p[`total_${horas}h` as "total_1h"] ?? 0;
    return { total, bruto: p[`bruto_${horas}h` as "bruto_1h"] ?? total };
  }
  if (p.extra_por_horas) return p.extra_por_horas[String(horas)] ?? null;
  if (p.duracao_custom === horas && p.total_custom) {
    return { total: p.total_custom, bruto: p.bruto_custom ?? p.total_custom };
  }
  const regua = (v: number) => Math.round((v / 4) * horas * 100) / 100;
  const total4 = p.total_4h ?? 0;
  return { total: regua(total4), bruto: regua(p.bruto_4h ?? total4) };
}

export function useOrcamentoPrefill(orcamentoId: number | null) {
  return useQuery<OrcamentoPrefill>({
    queryKey: ["orcamento-prefill", orcamentoId],
    queryFn: () =>
      apiFetch<OrcamentoPrefill>(`/api/events/new/prefill?orcamento_id=${orcamentoId}`),
    enabled: orcamentoId != null,
  });
}

export interface CharacterInput {
  /** Presente ao carregar um evento existente para edição (feature 184); `null` para uma linha
   * nova. Usado pelo backend para reconciliar o elenco por identidade em vez de substituir tudo. */
  role_id?: number | null;
  name: string;
  figurino_sheet_id: number | null;
  cache_value: number | null;
  needs_makeup: boolean;
  is_singer: boolean;
  talent_id: number | null;
}

export interface ObservationInput {
  obs_type: "text" | "link" | "image";
  content: string;
  label: string;
  /** Só para `obs_type === "image"` (feature 184) — enviado na fase 2, via
   * `POST /events/<id>/observations` multipart. */
  file?: File | null;
  /** Veio do formulário da cliente (feature 298) — só exibição, não vai no payload. */
  do_formulario?: boolean;
}

export interface ClientLinkInput {
  client_id: number;
  relation: string;
}

/** Comprovante de pagamento pendente de envio (feature 184) — vive só no estado local do
 * formulário até o evento existir; então é enviado via `POST /events/<id>/payments`. */
export interface PendingPaymentProof {
  file: File;
  amount: number;
}

/** Corpo de `POST /api/events` (feature 152) — sem nenhum campo de arquivo. O reembolso (feature
 * 184) deixou de ser enviado aqui — vira uma chamada separada em
 * `POST /events/<id>/reimbursements` depois que o evento existe (ver `EventCreatePage.tsx`,
 * fase 2 de anexos). Observações do tipo "image" também não entram aqui — só texto/link. */
export interface EventCreateInput {
  title: string;
  event_type: string;
  date: string;
  start: string;
  end: string;
  location: string;
  description: string;
  needs_rehearsal: boolean;
  /** `null` com "Valor a definir" (feature 299): a venda nasce vazia. */
  sale_value: number | null;
  sale_value_gross: number | null;
  /** Feature 299 — a marca "Valor a definir"; o servidor não a grava, só pula o valor. */
  valor_a_definir?: boolean;
  transport_value: number;
  acrescimo_value: number;
  with_invoice: boolean;
  is_cortesia_permuta: boolean;
  seller_id: number | null;
  sale_date: string | null;
  payment_method: string | null;
  payment_installments: number | null;
  payment_due_date: string | null;
  orcamento_history_id: number | null;
  duracao: string;
  characters: CharacterInput[];
  orc_caches: OrcamentoCache[];
  acrescimos: unknown[];
  /** Feature 305: obrigatórios quando o evento nasce com BV do orçamento (400 com `fields`). */
  bv_recipient?: string;
  bv_pix?: string;
  coordinator_talent_id: number | null;
  clients: ClientLinkInput[];
  form_response_id: number | null;
  observations: Array<Omit<ObservationInput, "obs_type" | "file"> & { obs_type: "text" | "link" }>;
}

/** Corpo de `PATCH /api/events/<id>` (feature 184) — atualização em bloco dos campos centrais.
 * Anexos (comprovantes/contrato/reembolso/observação com foto) NÃO passam por aqui — usam os
 * endpoints já existentes de `lib/eventAttachments.ts`, igual à tela de detalhe. */
export interface EventUpdateInput {
  title: string;
  event_type: string;
  date: string;
  start: string;
  end: string;
  location: string;
  description: string;
  needs_rehearsal: boolean;
  /** `null` com "Valor a definir" (feature 299): a venda nasce vazia. */
  sale_value: number | null;
  sale_value_gross: number | null;
  /** Feature 299 — a marca "Valor a definir"; o servidor não a grava, só pula o valor. */
  valor_a_definir?: boolean;
  transport_value: number;
  acrescimo_value: number;
  with_invoice: boolean;
  is_cortesia_permuta: boolean;
  seller_id: number | null;
  sale_date: string | null;
  payment_method: string | null;
  payment_installments: number | null;
  payment_due_date: string | null;
  coordinator_talent_id: number | null;
  form_response_id: number | null;
  characters: CharacterInput[];
  clients: ClientLinkInput[];
}

export interface EventCreateResult extends EventoDetalhe {
  warnings: string[];
}

/** Resposta de `PATCH /api/events/<id>` — o evento inteiro + `warnings` não-bloqueantes quando
 * a edição removeu algo automaticamente (feature 239, decisão 7: troca de tipo saindo de SHOW). */
export interface EventUpdateResult extends EventoDetalhe {
  warnings?: string[];
}

/** Cria um evento novo (feature 152). RBAC no servidor: `_CAN_CREATE` (Comercial/Superadmin). */
export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation<EventCreateResult, Error, EventCreateInput>({
    mutationFn: (body) =>
      apiFetch<EventCreateResult>("/api/events", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: (_result, body) => {
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
      // Evento novo entra em Cobranças ou em "Sem valor" (feature 299).
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      // Feature 305: o BV do orçamento nasce na criação, com a comissão sobre a venda menos ele.
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos"] });
      queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
      // Evento criado a partir de formulário (feature 298): ele sai da Home e o aviso some.
      if (body.form_response_id) invalidarDestinoDeFormulario(queryClient, body.form_response_id);
    },
  });
}

/** Atualiza os campos centrais de um evento existente (feature 184). RBAC no servidor: mesmo
 * nível de criação (Comercial/Superadmin) — o payload cobre os mesmos campos financeiros. */
export function useUpdateEvent(eventId: number) {
  const queryClient = useQueryClient();
  return useMutation<EventUpdateResult, Error, EventUpdateInput>({
    mutationFn: (body) =>
      apiFetch<EventUpdateResult>(`/api/events/${eventId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated, body) => {
      queryClient.setQueryData(["event", eventId], updated);
      queryClient.invalidateQueries({ queryKey: ["agenda"] });
      queryClient.invalidateQueries({ queryKey: ["agenda-dia"] });
      // Valor, data e título mudam as listas comerciais da Home (feature 299).
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      // Feature 305: a venda nova leva o BV a pagar junto (B10) e a comissão é sincronizada.
      queryClient.invalidateQueries({ queryKey: ["financeiro-pagamentos"] });
      queryClient.invalidateQueries({ queryKey: ["financeiro-comissoes"] });
      // Pré-contrato ligado na edição (feature 298): some da Home e da fila de Formulários.
      if (body.form_response_id) invalidarDestinoDeFormulario(queryClient, body.form_response_id);
    },
  });
}
