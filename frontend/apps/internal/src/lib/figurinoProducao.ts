import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Produção de Figurinos (feature 225) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato de `/api/figurino/producoes/*`. As duas telas (fila e detalhe) e o
 * painel da home consomem daqui; nenhuma monta `fetch` por conta própria.
 */

/** Ciclo de vida do pedido, na ordem em que a oficina o percorre. */
export type ProducaoStatus =
  | "solicitado"
  | "aprovado"
  | "em_producao"
  | "pronto"
  | "cancelado";

export const PRODUCAO_STATUS_LABELS: Record<ProducaoStatus, string> = {
  solicitado: "Solicitado",
  aprovado: "Aprovado",
  em_producao: "Em produção",
  pronto: "Pronto",
  cancelado: "Cancelado",
};

/** Tom do `Badge` por situação — paleta do design system, sem cor solta. */
export const PRODUCAO_STATUS_TONES: Record<
  ProducaoStatus,
  "neutral" | "gold" | "blue" | "green" | "red"
> = {
  solicitado: "neutral",
  aprovado: "gold",
  em_producao: "blue",
  pronto: "green",
  cancelado: "red",
};

/** Situações em que o pedido ainda dá trabalho a alguém. */
export const PRODUCAO_STATUS_ABERTOS: ProducaoStatus[] = [
  "solicitado",
  "aprovado",
  "em_producao",
];

/**
 * O que a oficina está fazendo com a peça: `producao` cria o que não existe, `manutencao` mexe
 * no que já existe (conserto de defeito, ajuste para uma data, adaptação).
 *
 * A diferença muda o fluxo: manutenção **não passa por aprovação**, porque a maior parte não tem
 * compra nenhuma — é trabalho manual. Quem manda nas transições é o servidor (`transicoes`).
 */
export type ProducaoKind = "producao" | "manutencao";

export const PRODUCAO_KIND_LABELS: Record<ProducaoKind, string> = {
  producao: "Produção",
  manutencao: "Manutenção",
};

/** A peça pode ir para o próximo evento assim como está, ou não? Só vale em `manutencao`. */
export type ProducaoSeveridade = "impede_uso" | "pode_esperar";

export const PRODUCAO_SEV_LABELS: Record<ProducaoSeveridade, string> = {
  impede_uso: "Não pode ir para evento",
  pode_esperar: "Dá para usar assim",
};

export type AnexoKind = "foto" | "orcamento";

export interface ProducaoAnexo {
  id: number;
  kind: AnexoKind;
  /** URL do arquivo; passar por `assetUrl()` antes de usar. */
  url: string;
  original_name: string | null;
  caption: string | null;
  /** Só em `kind: "orcamento"`. */
  supplier_name: string | null;
  /** Só em `kind: "orcamento"`. */
  amount: number | null;
  uploaded_by: string | null;
  created_at: string | null;
}

export interface ProducaoLog {
  id: number;
  actor_name: string;
  actor_role: string | null;
  message: string;
  /** Quando a linha do histórico carrega uma foto do andamento. */
  photo_url: string | null;
  status_from: string | null;
  status_to: string | null;
  created_at: string | null;
}

export interface ProducaoGasto {
  id: number;
  description: string;
  amount: number;
  status: string;
  expense_date: string | null;
  receipt_url: string | null;
}

export interface Producao {
  id: number;
  title: string;
  description: string | null;
  status: ProducaoStatus;
  status_label: string;
  kind: ProducaoKind;
  kind_label: string;
  severity: ProducaoSeveridade | null;
  severity_label: string | null;
  /** Manutenção aberta que impede a peça de ir para evento — o aviso vermelho. */
  impede_uso: boolean;
  quantity: number;
  event_id: number | null;
  event_title: string | null;
  event_start_at: string | null;
  figurino_sheet_id: number | null;
  figurino_sheet_name: string | null;
  figurino_sheet_photo: string | null;
  requested_by: string | null;
  responsible_id: number | null;
  responsible_name: string | null;
  approved_by: string | null;
  approved_at: string | null;
  due_date: string | null;
  /** O prazo que vale: o informado, ou a data do evento quando ninguém informou. */
  prazo_efetivo: string | null;
  dias_para_prazo: number | null;
  is_late: boolean;
  is_open: boolean;
  estimated_cost: number | null;
  /** Soma dos gastos extras **aprovados** vinculados — mesmo recorte da DRE. */
  total_gasto: number;
  gastos_count: number;
  cancellation_reason: string | null;
  done_at: string | null;
  google_event_id: string | null;
  created_at: string | null;
  /** Só no detalhe. */
  anexos?: ProducaoAnexo[];
  logs?: ProducaoLog[];
  gastos?: ProducaoGasto[];
}

export interface ProducaoFlags {
  can_execute: boolean;
  can_approve: boolean;
  can_create: boolean;
}

export interface ProducaoListResponse {
  items: Producao[];
  status_labels: Record<string, string>;
  status_abertos: string[];
  flags: ProducaoFlags;
}

export interface ProducaoDetailResponse {
  producao: Producao;
  flags: ProducaoFlags;
  /** Para onde este pedido pode ir a partir daqui — o backend é quem manda. */
  transicoes: ProducaoStatus[];
  status_labels: Record<string, string>;
}

export interface GastoVinculavel {
  id: number;
  description: string;
  amount: number;
  status: string;
  expense_date: string | null;
  event_title: string | null;
  ja_vinculado: boolean;
}

export interface ResponsavelOption {
  id: number;
  name: string;
  email: string | null;
  tem_email: boolean;
}

export interface ProducaoFiltros {
  status?: ProducaoStatus | "";
  tipo?: ProducaoKind | "";
  abertos?: boolean;
  responsavel?: number | null;
  evento?: number | null;
  ficha?: number | null;
  busca?: string;
}

/** Resposta das mutações: o pedido atualizado e, quando houve, o aviso do Google Agenda. */
interface MutationResponse {
  producao: Producao;
  warning?: string;
}

const KEY = "figurino-producoes";

export const producaoKeys = {
  list: (f: ProducaoFiltros) => [KEY, "list", f] as const,
  detail: (id: number) => [KEY, "detail", id] as const,
  gastosVinculaveis: (id: number) => [KEY, "gastos-vinculaveis", id] as const,
  responsaveis: () => [KEY, "responsaveis"] as const,
};

function buildQuery(f: ProducaoFiltros): string {
  const p = new URLSearchParams();
  if (f.status) p.set("status", f.status);
  if (f.tipo) p.set("tipo", f.tipo);
  if (f.abertos) p.set("abertos", "1");
  if (f.responsavel) p.set("responsavel", String(f.responsavel));
  if (f.evento) p.set("evento", String(f.evento));
  if (f.ficha) p.set("ficha", String(f.ficha));
  if (f.busca?.trim()) p.set("busca", f.busca.trim());
  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

export function useProducoes(filtros: ProducaoFiltros) {
  return useQuery({
    queryKey: producaoKeys.list(filtros),
    queryFn: () =>
      apiFetch<ProducaoListResponse>(`/api/figurino/producoes${buildQuery(filtros)}`),
  });
}

export function useProducao(id: number | null) {
  return useQuery({
    queryKey: producaoKeys.detail(id ?? 0),
    queryFn: () => apiFetch<ProducaoDetailResponse>(`/api/figurino/producoes/${id}`),
    enabled: id != null,
  });
}

export function useResponsaveis() {
  return useQuery({
    queryKey: producaoKeys.responsaveis(),
    queryFn: () =>
      apiFetch<{ items: ResponsavelOption[] }>("/api/figurino/producoes/responsaveis"),
  });
}

export function useGastosVinculaveis(id: number | null) {
  return useQuery({
    queryKey: producaoKeys.gastosVinculaveis(id ?? 0),
    queryFn: () =>
      apiFetch<{ items: GastoVinculavel[] }>(
        `/api/figurino/producoes/${id}/gastos-vinculaveis`,
      ),
    enabled: id != null,
  });
}

/**
 * Invalida tudo que depende do pedido. A home entra na lista porque o painel pessoal
 * "Minhas peças" muda junto — designar responsável, concluir ou cancelar altera o que a
 * pessoa vê ao entrar no sistema.
 */
function useInvalidate() {
  const qc = useQueryClient();
  return (id?: number) => {
    void qc.invalidateQueries({ queryKey: [KEY] });
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
    if (id) void qc.invalidateQueries({ queryKey: producaoKeys.detail(id) });
  };
}

export interface ProducaoInput {
  title: string;
  description?: string;
  kind?: ProducaoKind;
  /** Obrigatório quando `kind: "manutencao"` — é o que decide se a peça pode ir para o evento. */
  severity?: ProducaoSeveridade | null;
  event_id?: number | null;
  figurino_sheet_id?: number | null;
  responsible_id?: number | null;
  due_date?: string | null;
  estimated_cost?: number | null;
  quantity?: number;
}

export function useCreateProducao() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: ProducaoInput) =>
      apiFetch<MutationResponse>("/api/figurino/producoes", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidate(),
  });
}

export function useUpdateProducao(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: Partial<ProducaoInput>) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidate(id),
  });
}

export function useMudarStatus(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: { status: ProducaoStatus; motivo?: string; observacao?: string }) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/status`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidate(id),
  });
}

export function useDeleteProducao() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ ok: boolean }>(`/api/figurino/producoes/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(),
  });
}

export function useComentar(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (message: string) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/comentarios`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
    onSuccess: () => invalidate(id),
  });
}

export interface AnexoInput {
  file: File;
  kind: AnexoKind;
  caption?: string;
  supplier_name?: string;
  amount?: string;
}

export function useAddAnexo(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: AnexoInput) => {
      const body = new FormData();
      body.append("file", input.file);
      body.append("kind", input.kind);
      if (input.caption) body.append("caption", input.caption);
      if (input.supplier_name) body.append("supplier_name", input.supplier_name);
      if (input.amount) body.append("amount", input.amount);
      return apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/anexos`, {
        method: "POST",
        body,
      });
    },
    onSuccess: () => invalidate(id),
  });
}

export function useRemoveAnexo(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (anexoId: number) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/anexos/${anexoId}`, {
        method: "DELETE",
      }),
    onSuccess: () => invalidate(id),
  });
}

export function useVincularGasto(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (gastoId: number) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/gastos`, {
        method: "POST",
        body: JSON.stringify({ gasto_id: gastoId }),
      }),
    onSuccess: () => invalidate(id),
  });
}

export function useDesvincularGasto(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (gastoId: number) =>
      apiFetch<MutationResponse>(`/api/figurino/producoes/${id}/gastos/${gastoId}`, {
        method: "DELETE",
      }),
    onSuccess: () => invalidate(id),
  });
}

/** Rótulo curto do prazo, já com o tom de urgência que a lista usa. */
export function prazoInfo(p: Producao): {
  texto: string;
  tone: "red" | "gold" | "neutral";
} {
  if (!p.prazo_efetivo) return { texto: "Sem prazo", tone: "neutral" };
  const [ano, mes, dia] = p.prazo_efetivo.split("-");
  const data = `${dia}/${mes}/${ano}`;
  const dias = p.dias_para_prazo;
  if (dias == null) return { texto: data, tone: "neutral" };
  if (!p.is_open) return { texto: data, tone: "neutral" };
  if (dias < 0) return { texto: `${data} · atrasado ${Math.abs(dias)}d`, tone: "red" };
  if (dias === 0) return { texto: `${data} · é hoje`, tone: "red" };
  if (dias <= 2) return { texto: `${data} · em ${dias}d`, tone: "red" };
  if (dias <= 7) return { texto: `${data} · em ${dias}d`, tone: "gold" };
  return { texto: data, tone: "neutral" };
}
