import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Módulo de Impressões e Acervo 3D (feature 200) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/3d/*` e `/api/events/<id>/3d-gifts`: as três telas
 * (Acervo, Fila e a seção injetada no detalhe do evento) consomem daqui, nenhuma monta `fetch`
 * por conta própria.
 */

/** Ciclo de vida de um presente 3D, na ordem em que o Artista 3D o percorre. */
export type Gift3DStatus = "pendente" | "imprimindo" | "finalizado" | "entregue";

export const GIFT_3D_STATUSES: Gift3DStatus[] = [
  "pendente",
  "imprimindo",
  "finalizado",
  "entregue",
];

export const GIFT_3D_STATUS_LABELS: Record<Gift3DStatus, string> = {
  pendente: "Pendente",
  imprimindo: "Imprimindo",
  finalizado: "Finalizado",
  entregue: "Entregue",
};

/** Tom do `Badge` de cada status — mesma paleta do design system, sem cor hardcoded. */
export const GIFT_3D_STATUS_TONES: Record<Gift3DStatus, "neutral" | "gold" | "blue" | "green"> = {
  pendente: "neutral",
  imprimindo: "gold",
  finalizado: "blue",
  entregue: "green",
};

/** Um arquivo 3D bruto de uma peça — o modelo costuma vir fatiado em várias partes. */
export interface Acervo3DFile {
  id: number;
  /** Caminho salvo (UUID); passar por `assetUrl()` antes de usar como href. */
  file_path: string;
  /** Nome enviado pelo usuário ("corpo.stl") — é o que diz qual parte é qual. */
  original_name: string | null;
  position: number;
}

export interface Acervo3DItem {
  id: number;
  name: string;
  /** Foto de preview (JPG/PNG) — sempre presente; passar por `assetUrl()` antes de exibir. */
  photo_url: string;
  /**
   * Prefixo NFC (feature 255): não-nulo = a peça sai com tag NFC embutida e presentes dela
   * geram códigos `<prefixo>-XXXXXX` automaticamente. `null` = peça comum.
   */
  nfc_prefix: string | null;
  /** Arquivos 3D (.stl/.3mf/.zip) — sempre pelo menos um. */
  files: Acervo3DFile[];
  is_active: boolean;
  created_at: string | null;
  /** Quantas vezes a peça já foi usada em eventos. */
  usage_count: number;
}

export interface Acervo3DListResponse {
  items: Acervo3DItem[];
}

/** Peça do Acervo aninhada dentro de um presente (subset, sem `usage_count`). */
export interface Gift3DItemRef {
  id: number;
  name: string;
  photo_url: string;
  /** Arquivos vêm junto na Fila: o Artista 3D baixa direto, sem passar pelo Acervo. */
  files: Acervo3DFile[];
  is_active: boolean;
}

export interface Event3DGift {
  id: number;
  event_id: number;
  item_id: number;
  status: Gift3DStatus;
  /** `YYYY-MM-DD` ou `null`. */
  deadline_date: string | null;
  quantity: number;
  notes: string | null;
  item: Gift3DItemRef | null;
}

export interface Fila3DEventRef {
  id: number;
  title: string;
  event_type: string;
  start_at: string | null;
  location: string | null;
}

/** Personagem contratado do evento (com o talento escalado, se já houver). */
export interface Fila3DRole {
  id: number;
  character_name: string;
  role_type: string;
  talent_name: string | null;
  talent_photo_url: string | null;
}

export interface FormResponseField {
  chave: string;
  rotulo: string;
  valor: string;
}

export interface FormResponseSection {
  secao: string;
  campos: FormResponseField[];
}

/** Extrato do formulário de pré-contrato — só os campos que a cliente preencheu. */
export interface Fila3DFormResponse {
  id: number;
  form_type: string;
  form_type_label: string;
  contact_name: string;
  contact_phone_display: string | null;
  event_date: string | null;
  created_at: string | null;
  sections: FormResponseSection[];
}

/** Linha da Fila de Impressão: presente + evento + elenco + formulário. */
export interface Fila3DEntry extends Event3DGift {
  event: Fila3DEventRef;
  roles: Fila3DRole[];
  form_response: Fila3DFormResponse | null;
}

/**
 * Evento SHOW futuro **sem nenhum presente vinculado** — uma tarefa aberta (feature 202).
 * A pendência nasce do evento, não do presente: um SHOW novo na agenda já aparece aqui.
 */
export interface Fila3DPendingEvent extends Fila3DEventRef {
  /** Marcado como "não leva presente 3D" — só vem quando a busca pede os dispensados. */
  dismissed: boolean;
  dismissed_by: string | null;
  /** Personagens contratados, para o Artista 3D reconhecer o show de relance. */
  characters: string[];
}

export interface Fila3DResponse {
  items: Fila3DEntry[];
  sem_presente: Fila3DPendingEvent[];
}

/**
 * Formata uma data pura `YYYY-MM-DD` (prazo do presente) em pt-BR.
 *
 * Não usa `new Date(iso)`: o JS interpreta string **só de data** como UTC, e no fuso de São
 * Paulo (UTC−3) isso exibiria o dia anterior. `formatShortDate` de `@manto/ui` continua sendo o
 * certo para os ISO com hora (ex.: `start_at` do evento).
 */
export function formatDeadline(deadline: string | null): string {
  if (!deadline) return "—";
  const [year, month, day] = deadline.split("-");
  if (!year || !month || !day) return "—";
  return `${day}/${month}/${year}`;
}

/**
 * Dias restantes até o prazo — negativo = atrasado, `null` sem prazo. Compara só a parte de
 * data (meia-noite local), para "hoje" nunca virar "atrasado".
 */
export function daysUntilDeadline(deadline: string | null): number | null {
  if (!deadline) return null;
  const [year, month, day] = deadline.split("-").map(Number);
  if (!year || !month || !day) return null;
  const target = new Date(year, month - 1, day).getTime();
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  return Math.round((target - start) / 86_400_000);
}

const ACERVO_KEY = ["acervo-3d"] as const;
const FILA_KEY = ["fila-3d"] as const;

/**
 * Catálogo de peças do Acervo 3D.
 *
 * `enabled` existe porque o endpoint responde 403 para quem não é Artista 3D/Superadmin: a
 * seção do evento só dispara a busca quando o usuário realmente pode vincular presentes.
 */
export function useAcervo3D(onlyActive = false, enabled = true) {
  return useQuery<Acervo3DListResponse>({
    queryKey: [...ACERVO_KEY, onlyActive],
    queryFn: () =>
      apiFetch<Acervo3DListResponse>(`/api/3d/acervo${onlyActive ? "?ativos=1" : ""}`),
    enabled,
  });
}

export interface SaveAcervoItemInput {
  name?: string;
  /** Foto JPG/PNG — obrigatória na criação, opcional na edição (mantém a atual). */
  photo?: File | null;
  /**
   * Arquivos 3D .stl/.3mf/.zip a **acrescentar**. Pelo menos um na criação; na edição são
   * cumulativos (não substituem os existentes) e a lista vazia mantém tudo como está.
   */
  files?: File[];
  /** Ids de arquivos já salvos a remover — o servidor recusa deixar a peça com zero. */
  removeFileIds?: number[];
  isActive?: boolean;
  /** Prefixo NFC (feature 255) — string vazia desabilita; omitido mantém o atual. */
  nfcPrefix?: string;
}

function buildAcervoFormData(input: SaveAcervoItemInput): FormData {
  const form = new FormData();
  if (input.name !== undefined) form.set("name", input.name);
  if (input.photo) form.set("photo", input.photo);
  (input.files ?? []).forEach((file) => form.append("files", file));
  (input.removeFileIds ?? []).forEach((id) => form.append("remove_file_ids[]", String(id)));
  if (input.isActive !== undefined) form.set("is_active", String(input.isActive));
  if (input.nfcPrefix !== undefined) form.set("nfc_prefix", input.nfcPrefix);
  return form;
}

export function useCreateAcervoItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveAcervoItemInput) =>
      apiFetch<Acervo3DItem>("/api/3d/acervo", {
        method: "POST",
        body: buildAcervoFormData(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ACERVO_KEY });
    },
  });
}

export function useUpdateAcervoItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: SaveAcervoItemInput }) =>
      apiFetch<Acervo3DItem>(`/api/3d/acervo/${id}`, {
        method: "PATCH",
        body: buildAcervoFormData(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ACERVO_KEY });
      void queryClient.invalidateQueries({ queryKey: FILA_KEY });
    },
  });
}

/**
 * Exclui uma peça do Acervo. Com `force`, o servidor **desvincula a peça de todos os eventos**
 * antes de apagá-la — irreversível e restrito a SUPERADMIN no endpoint. Sem `force`, uma peça
 * já usada é recusada com a orientação de inativar.
 */
export function useDeleteAcervoItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, force }: { id: number; force?: boolean }) =>
      apiFetch<void>(`/api/3d/acervo/${id}${force ? "?force=true" : ""}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ACERVO_KEY });
      // Os presentes somem dos eventos e da Fila de Impressão junto com a peça.
      void queryClient.invalidateQueries({ queryKey: FILA_KEY });
    },
  });
}

/**
 * Fila de Impressão — presentes não entregues **e** os shows futuros ainda sem presente.
 *
 * `showDismissed` inclui os eventos marcados como "não leva presente", para a tela poder
 * oferecer o "Reativar".
 */
export function useFila3D(showDismissed = false) {
  return useQuery<Fila3DResponse>({
    queryKey: [...FILA_KEY, showDismissed],
    queryFn: () =>
      apiFetch<Fila3DResponse>(`/api/3d/fila${showDismissed ? "?dispensados=1" : ""}`),
  });
}

/** Marca um show como "não leva presente 3D", tirando-o das pendências (feature 202). */
export function useDismissEvent3D() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) =>
      apiFetch<{ event_id: number; dismissed: boolean }>(`/api/events/${eventId}/3d-dismissal`, {
        method: "POST",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FILA_KEY });
    },
  });
}

/** Desfaz a dispensa, devolvendo o show à lista de pendências. */
export function useUndismissEvent3D() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: number) =>
      apiFetch<void>(`/api/events/${eventId}/3d-dismissal`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FILA_KEY });
    },
  });
}

export interface SaveGiftInput {
  item_id?: number;
  quantity?: number;
  /** `null` limpa o prazo; omitido mantém o atual. */
  deadline_date?: string | null;
  notes?: string;
  status?: Gift3DStatus;
}

/**
 * Invalida tudo que mostra presentes 3D: a Fila, o Acervo (a contagem de usos muda) e o detalhe
 * do evento afetado. Fonte única para as três mutações abaixo não divergirem.
 */
function useInvalidateGiftQueries() {
  const queryClient = useQueryClient();
  return (eventId: number) => {
    void queryClient.invalidateQueries({ queryKey: FILA_KEY });
    void queryClient.invalidateQueries({ queryKey: ACERVO_KEY });
    void queryClient.invalidateQueries({ queryKey: ["event", eventId] });
  };
}

export function useAddEvent3DGift(eventId: number) {
  const invalidate = useInvalidateGiftQueries();
  return useMutation({
    mutationFn: (input: SaveGiftInput) =>
      apiFetch<Event3DGift>(`/api/events/${eventId}/3d-gifts`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => invalidate(eventId),
  });
}

/**
 * Edita um presente. O `eventId` vem no payload da mutação (e não do hook) porque a Fila lista
 * presentes de eventos diferentes na mesma tela.
 */
export function useUpdateEvent3DGift() {
  const invalidate = useInvalidateGiftQueries();
  return useMutation({
    mutationFn: ({
      eventId,
      giftId,
      input,
    }: {
      eventId: number;
      giftId: number;
      input: SaveGiftInput;
    }) =>
      apiFetch<Event3DGift>(`/api/events/${eventId}/3d-gifts/${giftId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: (_data, variables) => invalidate(variables.eventId),
  });
}

export function useDeleteEvent3DGift() {
  const invalidate = useInvalidateGiftQueries();
  return useMutation({
    mutationFn: ({ eventId, giftId }: { eventId: number; giftId: number }) =>
      apiFetch<void>(`/api/events/${eventId}/3d-gifts/${giftId}`, { method: "DELETE" }),
    onSuccess: (_data, variables) => invalidate(variables.eventId),
  });
}
