import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Resumo de um Personagem dentro da listagem de Temas (feature 186) — sem precisar do detalhe. */
export interface CatalogCharacterSummary {
  id: number;
  name: string;
  photo_url: string | null;
  figurino_sheet_id: number | null;
  is_active: boolean;
}

export interface CatalogListItem {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  cover_url: string | null;
  category_names: string[];
  characters: CatalogCharacterSummary[];
}

export interface CatalogCategoryOption {
  id: number;
  name: string;
}

export interface CatalogListResponse {
  items: CatalogListItem[];
  categories: CatalogCategoryOption[];
}

export function useAdminCatalogo(filters: { q?: string; categoria?: string; status?: string }) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.categoria) params.set("categoria", filters.categoria);
  if (filters.status) params.set("status", filters.status);
  return useQuery<CatalogListResponse>({
    queryKey: ["admin-catalogo", filters],
    queryFn: () => apiFetch<CatalogListResponse>(`/api/admin/catalogo?${params.toString()}`),
  });
}

export interface CatalogImage {
  id: number;
  url: string;
  position: number;
}

/** Personagem filho de um Tema (feature 185) — forma completa (admin), com `figurino_sheet_id`. */
export interface CatalogCharacter {
  id: number;
  name: string;
  slug: string;
  photo_url: string | null;
  video_url: string | null;
  figurino_sheet_id: number | null;
  position: number;
  is_active: boolean;
}

export interface CatalogItemDetail {
  id: number;
  name: string;
  description: string;
  tags: string[];
  is_active: boolean;
  category_ids: number[];
  video_url: string | null;
  images: CatalogImage[];
  characters: CatalogCharacter[];
}

export function useAdminCatalogoItem(id: number | undefined) {
  return useQuery<CatalogItemDetail>({
    queryKey: ["admin-catalogo", id],
    queryFn: () => apiFetch<CatalogItemDetail>(`/api/admin/catalogo/${id}`),
    enabled: id !== undefined,
  });
}

export function useCreateCategory() {
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<CatalogCategoryOption>("/api/admin/catalogo/categorias", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
  });
}

export interface SaveCatalogItemInput {
  name: string;
  description?: string;
  tags?: string;
  categoryIds: number[];
  newPhotos: File[];
  removePhotoIds?: number[];
  photoOrder?: number[];
  coverPhotoId?: number;
  newPhotoCoverIndex?: number;
  videoUrl?: string;
}

function buildCatalogFormData(input: SaveCatalogItemInput): FormData {
  const form = new FormData();
  form.set("name", input.name);
  form.set("description", input.description ?? "");
  form.set("tags", input.tags ?? "");
  form.set("video_url", input.videoUrl ?? "");
  (input.categoryIds ?? []).forEach((id) => form.append("category_ids[]", String(id)));
  input.newPhotos.forEach((file) => form.append("new_photos", file));
  (input.removePhotoIds ?? []).forEach((id) => form.append("remove_photo_ids[]", String(id)));
  if (input.photoOrder && input.photoOrder.length > 0) {
    form.set("photo_order", input.photoOrder.join(","));
  }
  if (input.coverPhotoId !== undefined) form.set("cover_photo_id", String(input.coverPhotoId));
  if (input.newPhotoCoverIndex !== undefined) {
    form.set("new_photo_cover_index", String(input.newPhotoCoverIndex));
  }
  return form;
}

export function useCreateCatalogItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveCatalogItemInput) =>
      apiFetch<CatalogListItem>("/api/admin/catalogo", {
        method: "POST",
        body: buildCatalogFormData(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

export function useUpdateCatalogItem(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveCatalogItemInput) =>
      apiFetch<CatalogListItem>(`/api/admin/catalogo/${id}`, {
        method: "PATCH",
        body: buildCatalogFormData(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

export function useToggleCatalogItemActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<CatalogListItem>(`/api/admin/catalogo/${id}/toggle-ativo`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

export function useDeleteCatalogItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/admin/catalogo/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

/** Todas as tags já usadas em algum produto do catálogo — autocomplete do `ChipInput`. */
export function useCatalogTagSuggestions() {
  return useQuery<{ tags: string[] }>({
    queryKey: ["admin-catalogo-tags"],
    queryFn: () => apiFetch<{ tags: string[] }>("/api/admin/catalogo/tags"),
  });
}

export interface SaveCharacterInput {
  /** Omitido = não altera o nome (ex.: vínculo de figurino feito de fora da tela do Tema). */
  name?: string;
  videoUrl?: string;
  figurinoSheetId?: number | null;
  photo?: File;
  removePhoto?: boolean;
  position?: number;
  isActive?: boolean;
}

function buildCharacterFormData(input: SaveCharacterInput): FormData {
  const form = new FormData();
  if (input.name !== undefined) form.set("name", input.name);
  if (input.videoUrl !== undefined) form.set("video_url", input.videoUrl);
  if (input.figurinoSheetId !== undefined) {
    form.set("figurino_sheet_id", input.figurinoSheetId === null ? "" : String(input.figurinoSheetId));
  }
  if (input.photo) form.set("photo", input.photo);
  if (input.removePhoto) form.set("remove_photo", "true");
  if (input.position !== undefined) form.set("position", String(input.position));
  if (input.isActive !== undefined) form.set("is_active", String(input.isActive));
  return form;
}

export function useCreateCharacter(itemId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveCharacterInput) =>
      apiFetch<CatalogCharacter>(`/api/admin/catalogo/${itemId}/personagens`, {
        method: "POST",
        body: buildCharacterFormData(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo", itemId] });
    },
  });
}

export function useUpdateCharacter(itemId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: SaveCharacterInput }) =>
      apiFetch<CatalogCharacter>(`/api/admin/catalogo/personagens/${id}`, {
        method: "PATCH",
        body: buildCharacterFormData(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo", itemId] });
    },
  });
}

export function useDeleteCharacter(itemId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/admin/catalogo/personagens/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo", itemId] });
    },
  });
}

/**
 * Variantes "standalone" das mutações de Personagem, usadas onde o `itemId` (Tema pai) não é
 * conhecido de antemão — modo Árvore/ações em massa (feature 186, US4) e vínculo a partir da
 * Ficha (US2). Invalidam as queries de catálogo de forma ampla.
 */
export function useUpdateCharacterActiveStandalone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      apiFetch<CatalogCharacter>(`/api/admin/catalogo/personagens/${id}`, {
        method: "PATCH",
        body: buildCharacterFormData({ isActive }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

export function useDeleteCharacterStandalone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/admin/catalogo/personagens/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}

/**
 * Vincula/desvincula um Personagem a uma Ficha de Figurino a partir de um contexto que não
 * conhece o Tema pai de antemão (ex.: a tela da própria Ficha — feature 186, US2). Invalida as
 * queries de catálogo de forma ampla (não sabemos qual `itemId` foi afetado sem uma segunda
 * leitura).
 */
export function useLinkCharacterFigurino() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ characterId, figurinoSheetId }: { characterId: number; figurinoSheetId: number | null }) =>
      apiFetch<CatalogCharacter>(`/api/admin/catalogo/personagens/${characterId}`, {
        method: "PATCH",
        body: buildCharacterFormData({ figurinoSheetId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
      queryClient.invalidateQueries({ queryKey: ["catalogo-elenco-busca"] });
    },
  });
}

/** Realoca em massa Personagens para um novo Tema pai (feature 186, US4). */
export function useMoveCharactersBulk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ characterIds, targetItemId }: { characterIds: number[]; targetItemId: number }) =>
      apiFetch<{ moved: number }>("/api/admin/catalogo/personagens/mover-em-massa", {
        method: "POST",
        body: JSON.stringify({ character_ids: characterIds, target_item_id: targetItemId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-catalogo"] });
    },
  });
}
