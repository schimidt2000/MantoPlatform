import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Item da listagem/busca de talentos (feature 154) — resumo, não o perfil completo. */
export interface TalentSummary {
  id: number;
  full_name: string;
  artistic_name: string | null;
  status: "active" | "pending";
  warning_level: string | null;
  photo_face_path: string | null;
  height_cm: number | null;
  clothing_size_top: string | null;
  clothing_size_bottom: string | null;
  shoe_size: string | null;
  character_matches: Record<string, number>;
}

export interface TalentFilterOptions {
  languages: string[];
  races: string[];
  tags: string[];
  sizes: string[];
  shoes: string[];
  passport: [string, string][];
}

export interface TalentDirectory {
  items: TalentSummary[];
  total: number;
  page: number;
  pages: number;
  pending_count: number;
  filter_options?: TalentFilterOptions;
}

export interface TalentDirectoryParams {
  status?: "active" | "pending";
  q?: string;
  ja_trabalhou?: boolean;
  language?: string[];
  race?: string[];
  top?: string[];
  bottom?: string[];
  shoe?: string[];
  height_op?: "gte" | "lte" | "eq";
  height_value?: string;
  passport?: string[];
  tag?: string[];
  character?: string;
  page?: number;
}

function buildDirectoryQuery(params: TalentDirectoryParams): string {
  const sp = new URLSearchParams();
  if (params.status) sp.set("status", params.status);
  if (params.q) sp.set("q", params.q);
  if (params.ja_trabalhou) sp.set("ja_trabalhou", "1");
  if (params.height_op) sp.set("height_op", params.height_op);
  if (params.height_value) sp.set("height_value", params.height_value);
  if (params.character) sp.set("character", params.character);
  if (params.page) sp.set("page", String(params.page));
  for (const v of params.language ?? []) sp.append("language", v);
  for (const v of params.race ?? []) sp.append("race", v);
  for (const v of params.top ?? []) sp.append("top", v);
  for (const v of params.bottom ?? []) sp.append("bottom", v);
  for (const v of params.shoe ?? []) sp.append("shoe", v);
  for (const v of params.passport ?? []) sp.append("passport", v);
  for (const v of params.tag ?? []) sp.append("tag", v);
  return sp.toString();
}

/** Busca/filtra talentos paginados (feature 154). */
export function useTalentDirectory(params: TalentDirectoryParams) {
  const qs = buildDirectoryQuery(params);
  return useQuery<TalentDirectory>({
    queryKey: ["talents-directory", params],
    queryFn: () => apiFetch<TalentDirectory>(`/api/talents/directory?${qs}`),
  });
}

export interface CharacterSuggestion {
  name: string;
  count: number;
}

/** Sugestões de personagem para o filtro (feature 180) — mín. 2 caracteres. */
export function useCharacterSuggestions(q: string) {
  const query = q.trim();
  return useQuery<CharacterSuggestion[]>({
    queryKey: ["talent-character-suggestions", query],
    queryFn: () =>
      apiFetch<CharacterSuggestion[]>(
        `/api/talents/character-suggestions?q=${encodeURIComponent(query)}`,
      ),
    enabled: query.length >= 2,
  });
}

export interface TalentProfile {
  id: number;
  full_name: string;
  artistic_name: string | null;
  status: "active" | "pending";
  gender: string | null;
  birth_date: string | null;
  race: string | null;
  languages: string | null;
  is_foreigner: boolean;
  phone: string | null;
  email_contact: string | null;
  tags: string | null;
  skills: string | null;
  height_cm: number | null;
  clothing_size_top: string | null;
  clothing_size_bottom: string | null;
  shoe_size: string | null;
  passport_status: string | null;
  rg: string | null;
  cpf: string | null;
  pix_key: string | null;
  pix_key_secondary: string | null;
  pix_key_type: string | null;
  photo_face_path: string | null;
  photo_full_path: string | null;
  doc_photo_path: string | null;
  cnh_file_path: string | null;
  cnh_expiration: string | null;
  car_brand: string | null;
  car_model: string | null;
  car_year: string | null;
  car_plate: string | null;
  worked_before: boolean | null;
  how_found_us: string | null;
  notes: string | null;
  warning_level: string | null;
}

export interface TalentHistoryItem {
  event_id: number;
  event_title: string | null;
  character_name: string;
  cache_value: number | null;
  start_at: string | null;
}

export interface TalentLastEvent {
  event_id: number;
  event_title: string | null;
  character_name: string;
  start_at: string | null;
}

export interface TalentDetail {
  talent: TalentProfile;
  history: {
    items: TalentHistoryItem[];
    total_events: number;
    total_earned: number;
    characters_done: string[];
    last_event: TalentLastEvent | null;
  };
  can_edit: boolean;
}

export interface TalentDetailParams {
  date_from?: string;
  date_to?: string;
}

function buildDetailQuery(params: TalentDetailParams): string {
  const sp = new URLSearchParams();
  if (params.date_from) sp.set("date_from", params.date_from);
  if (params.date_to) sp.set("date_to", params.date_to);
  return sp.toString();
}

/** Perfil completo de um talento, com histórico filtrável por período (feature 154/180). */
export function useTalent(id: number, params: TalentDetailParams = {}) {
  const qs = buildDetailQuery(params);
  return useQuery<TalentDetail>({
    queryKey: ["talent", id, params],
    queryFn: () => apiFetch<TalentDetail>(`/api/talents/${id}${qs ? `?${qs}` : ""}`),
    enabled: Number.isFinite(id),
  });
}

export interface TalentReceivedRating {
  category: string;
  category_label: string;
  score: number;
  comment: string | null;
  author: string;
  event_id: number;
  event_title: string | null;
  event_date: string | null;
}

export interface TalentGivenRating {
  score: number;
  comment: string | null;
  event_id: number;
  event_title: string | null;
  event_date: string | null;
  submitted_at: string | null;
  edited: boolean;
  edit_count: number;
}

export interface TalentRatingsOverview {
  received: TalentReceivedRating[];
  given: TalentGivenRating[];
  show_authors: boolean;
}

/** Avaliações recebidas/dadas por um talento — seção "Avaliações e Notas" (feature 180). */
export function useTalentRatings(id: number) {
  return useQuery<TalentRatingsOverview>({
    queryKey: ["talent-ratings", id],
    queryFn: () => apiFetch<TalentRatingsOverview>(`/api/talents/${id}/ratings`),
    enabled: Number.isFinite(id),
  });
}

function useTalentDetailMutation<TVars>(id: number, mutationFn: (vars: TVars) => Promise<TalentDetail>) {
  const queryClient = useQueryClient();
  return useMutation<TalentDetail, Error, TVars>({
    mutationFn,
    onSuccess: (updated) => {
      queryClient.setQueryData(["talent", id], updated);
      queryClient.invalidateQueries({ queryKey: ["talents-directory"] });
    },
  });
}

/** Aprova um cadastro pendente (feature 154). Idempotente. */
export function useApproveTalent() {
  const queryClient = useQueryClient();
  return useMutation<{ id: number; status: string }, Error, number>({
    mutationFn: (id) =>
      apiFetch<{ id: number; status: string }>(`/api/talents/${id}/approve`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["talents-directory"] });
    },
  });
}

/** Rejeita/exclui um cadastro pendente (feature 154). */
export function useRejectTalent() {
  const queryClient = useQueryClient();
  return useMutation<{ ok: boolean }, Error, number>({
    mutationFn: (id) => apiFetch<{ ok: boolean }>(`/api/talents/${id}/reject`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["talents-directory"] });
    },
  });
}

export type TalentUpdateInput = Partial<
  Omit<TalentProfile, "id" | "status" | "notes" | "warning_level">
>;

/** Edita os dados de um talento (feature 154). CPF só é aplicado se o usuário for SUPERADMIN. */
export function useUpdateTalent(id: number) {
  return useTalentDetailMutation<TalentUpdateInput>(id, (body) =>
    apiFetch<TalentDetail>(`/api/talents/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  );
}

/** Salva anotação interna + nível de alerta (feature 154). */
export function useSaveTalentNotes(id: number) {
  return useTalentDetailMutation<{ notes: string; warning_level: string }>(id, (body) =>
    apiFetch<TalentDetail>(`/api/talents/${id}/notes`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  );
}

export type TalentPhotoType = "face" | "full" | "doc" | "cnh";

/** Envia/substitui foto ou documento do talento (feature 155). */
export function useUploadTalentPhoto(id: number) {
  return useTalentDetailMutation<{ photoType: TalentPhotoType; file: File }>(id, ({ photoType, file }) => {
    const form = new FormData();
    form.append("photo_type", photoType);
    form.append("photo", file);
    return apiFetch<TalentDetail>(`/api/talents/${id}/photo`, { method: "POST", body: form });
  });
}

/** Remove foto ou documento do talento (feature 155). No-op seguro se já vazio. */
export function useRemoveTalentPhoto(id: number) {
  return useTalentDetailMutation<TalentPhotoType>(id, (photoType) =>
    apiFetch<TalentDetail>(`/api/talents/${id}/photo?photo_type=${photoType}`, { method: "DELETE" }),
  );
}
