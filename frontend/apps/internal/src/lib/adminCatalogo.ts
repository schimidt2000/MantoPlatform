import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface CatalogListItem {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  cover_url: string | null;
  category_names: string[];
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

export interface CatalogItemDetail {
  id: number;
  name: string;
  description: string;
  tags: string[];
  is_active: boolean;
  category_ids: number[];
  images: CatalogImage[];
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
}

function buildCatalogFormData(input: SaveCatalogItemInput): FormData {
  const form = new FormData();
  form.set("name", input.name);
  form.set("description", input.description ?? "");
  form.set("tags", input.tags ?? "");
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
