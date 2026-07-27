import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FormResponseSummary {
  id: number;
  form_type: "comum" | "corporativo";
  form_type_label: string;
  contact_name: string;
  contact_phone_display: string;
  event_date: string | null;
  client_id: number | null;
  /** Nome do cliente vinculado — vem já na listagem, alimenta o badge "Cliente: <nome>". */
  client_name: string | null;
  event_id: number | null;
  event_link_source: string | null;
  event_link_ambiguous: boolean;
  event_link_locked: boolean;
  created_at: string;
}

export interface FormResponseDetail extends FormResponseSummary {
  data_sections: { secao: string; campos: [string, string, string][] }[];
  event_title: string | null;
}

/** Lista as respostas de formulário mais recentes (feature 177, US7). */
export function useFormResponses() {
  return useQuery<{ responses: FormResponseSummary[] }>({
    queryKey: ["formularios-respostas"],
    queryFn: () => apiFetch<{ responses: FormResponseSummary[] }>("/api/formularios/respostas"),
  });
}

/** Busca respostas por nome/telefone. */
export function useSearchFormResponses(q: string) {
  return useQuery<{ responses: FormResponseSummary[] }>({
    queryKey: ["formularios-respostas-search", q],
    queryFn: () =>
      apiFetch<{ responses: FormResponseSummary[] }>(
        `/api/formularios/respostas/search?q=${encodeURIComponent(q)}`,
      ),
    enabled: q.trim().length >= 2,
  });
}

/** Detalhe completo de uma resposta + sugestão de cliente. */
export function useFormResponseDetail(id: number | null) {
  return useQuery<{
    response: FormResponseDetail;
    suggested_client: { id: number; name: string } | null;
    can_edit_structure: boolean;
  }>({
    queryKey: ["formularios-resposta-detalhe", id],
    queryFn: () =>
      apiFetch(`/api/formularios/respostas/${id}`),
    enabled: id != null,
  });
}

function invalidateResponse(queryClient: ReturnType<typeof useQueryClient>, id: number) {
  queryClient.invalidateQueries({ queryKey: ["formularios-resposta-detalhe", id] });
  queryClient.invalidateQueries({ queryKey: ["formularios-respostas"] });
}

/** Associa a resposta a um cliente existente ou cria um a partir dos dados dela. */
export function useAssociateClient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (clientId?: number) =>
      apiFetch<{ client_id: number; client_name: string }>(`/api/formularios/respostas/${id}/associar`, {
        method: "POST",
        body: JSON.stringify({ client_id: clientId }),
      }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Remove a associação da resposta com o cliente. */
export function useDissociateClient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/formularios/respostas/${id}/desassociar`, { method: "POST" }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Vincula manualmente a resposta a um evento da agenda. */
export function useLinkEvent(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) =>
      apiFetch<{ event_id: number; event_title: string }>(`/api/formularios/respostas/${id}/vincular-evento`, {
        method: "POST",
        body: JSON.stringify({ event_id: eventId }),
      }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Desfaz o vínculo de evento (automático ou manual). */
export function useUnlinkEvent(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>(`/api/formularios/respostas/${id}/desvincular-evento`, { method: "POST" }),
    onSuccess: () => invalidateResponse(queryClient, id),
  });
}

/** Exclui uma resposta (SUPERADMIN). */
export function useDeleteFormResponse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/formularios/respostas/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["formularios-respostas"] }),
  });
}

// ══════════════════════════════════════════════════════════════════
//  Editor de estrutura dos formulários (SUPERADMIN)
// ══════════════════════════════════════════════════════════════════

export interface FormFieldDefinition {
  id: number;
  section_name: string;
  field_key: string;
  field_type: string;
  label: string;
  help_text: string | null;
  placeholder: string | null;
  required: boolean;
  options: string | null;
  order: number;
  is_system: boolean;
}

/** Definição de campos de um formulário (`comum`/`corporativo`). */
export function useFormFieldDefinitions(formType: "comum" | "corporativo") {
  return useQuery<{ fields: FormFieldDefinition[] }>({
    queryKey: ["formularios-editor", formType],
    queryFn: () => apiFetch<{ fields: FormFieldDefinition[] }>(`/api/formularios/editor/${formType}`),
  });
}

function invalidateEditor(queryClient: ReturnType<typeof useQueryClient>, formType: string) {
  queryClient.invalidateQueries({ queryKey: ["formularios-editor", formType] });
}

/** Tipos de campo aceitos pelo backend (`FormFieldDefinition.FIELD_TYPES`). */
export const FIELD_TYPES = [
  { value: "texto_curto", label: "Texto curto" },
  { value: "texto_longo", label: "Texto longo" },
  { value: "selecao", label: "Seleção (lista de opções)" },
  { value: "data", label: "Data" },
  { value: "hora", label: "Hora" },
  { value: "telefone", label: "Telefone" },
  { value: "email", label: "E-mail" },
  { value: "cpf", label: "CPF" },
  { value: "cnpj", label: "CNPJ" },
  { value: "cep", label: "CEP" },
  { value: "sim_nao", label: "Sim/Não" },
] as const;

/**
 * Converte o `options` do backend (string JSON `list[str]`) no texto do editor — uma opção
 * por linha, que é o formato que `create_field`/`update_field` esperam de volta.
 */
export function optionsToText(options: string | null): string {
  if (!options) return "";
  try {
    const parsed: unknown = JSON.parse(options);
    return Array.isArray(parsed) ? parsed.join("\n") : "";
  } catch {
    return "";
  }
}

export interface CreateFieldInput {
  label: string;
  section_name: string;
  field_type: string;
  help_text?: string;
  placeholder?: string;
  required?: boolean;
  options?: string;
}

/**
 * Corpo do PATCH de um campo. `update_field` no backend **substitui** todos estes atributos:
 * omitir `help_text`/`placeholder`/`required` os apaga. Por isso o payload é sempre completo
 * (menos `field_type`/`section_name`, que são imutáveis após a criação).
 */
export type UpdateFieldInput = {
  id: number;
  label: string;
  help_text?: string;
  placeholder?: string;
  required: boolean;
  options?: string;
};

/** Adiciona um campo personalizado ao fim de uma seção. */
export function useCreateField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateFieldInput) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/${formType}/campo`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo (payload completo). */
export function useUpdateField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: UpdateFieldInput) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/campo/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Reordena um campo dentro da própria seção. */
export function useMoveField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, direction }: { id: number; direction: "up" | "down" }) =>
      apiFetch<FormFieldDefinition>(`/api/formularios/editor/campo/${id}/mover`, {
        method: "POST",
        body: JSON.stringify({ direction }),
      }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}

/** Remove um campo personalizado (campos de sistema são protegidos). */
export function useDeleteField(formType: "comum" | "corporativo") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/formularios/editor/campo/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateEditor(queryClient, formType),
  });
}
