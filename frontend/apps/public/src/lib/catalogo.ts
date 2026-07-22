import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Forma resumida de um item — usada nas listas (grade, categoria, relacionados). */
export interface CatalogItemSummary {
  id: number;
  name: string;
  slug: string;
  cover_image_url: string | null;
  categories: string[];
}

/** Forma resumida de uma categoria, com contagem e foto de capa. */
export interface CatalogCategorySummary {
  id: number;
  name: string;
  slug: string;
  item_count: number;
  cover_image_url: string | null;
}

export interface CatalogList {
  items: CatalogItemSummary[];
  total: number;
  categories: CatalogCategorySummary[];
  whatsapp_number: string;
}

export interface CatalogCategoryList {
  categories: CatalogCategorySummary[];
}

export interface CatalogCategoryDetail {
  category: { id: number; name: string; slug: string };
  items: CatalogItemSummary[];
}

export interface CatalogItemImage {
  url: string;
  position: number;
}

export interface CatalogItemDetail {
  id: number;
  name: string;
  slug: string;
  description_html: string | null;
  categories: { name: string; slug: string }[];
  images: CatalogItemImage[];
  related: CatalogItemSummary[];
}

/** Grade geral do catálogo — itens ativos + categorias com contagem + WhatsApp de destino. */
export function useCatalogList() {
  return useQuery<CatalogList>({
    queryKey: ["catalogo-list"],
    queryFn: () => apiFetch<CatalogList>("/api/catalogo"),
  });
}

/** Grade de categorias com pelo menos 1 item ativo. */
export function useCategories() {
  return useQuery<CatalogCategoryList>({
    queryKey: ["catalogo-categorias"],
    queryFn: () => apiFetch<CatalogCategoryList>("/api/catalogo/categorias"),
  });
}

/** Itens ativos de uma categoria por slug. */
export function useCategoryDetail(slug: string | undefined) {
  return useQuery<CatalogCategoryDetail>({
    queryKey: ["catalogo-categoria", slug],
    queryFn: () => apiFetch<CatalogCategoryDetail>(`/api/catalogo/categoria/${slug}`),
    enabled: Boolean(slug),
  });
}

/** Detalhe de um produto por slug — fotos, categorias e relacionados. */
export function useProductDetail(slug: string | undefined) {
  return useQuery<CatalogItemDetail>({
    queryKey: ["catalogo-detail", slug],
    queryFn: () => apiFetch<CatalogItemDetail>(`/api/catalogo/${slug}`),
    enabled: Boolean(slug),
  });
}
