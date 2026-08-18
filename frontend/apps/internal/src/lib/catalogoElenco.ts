import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface CatalogElencoCharacter {
  id: number;
  name: string;
  figurino_sheet_id: number | null;
  photo_url: string | null;
}

export interface CatalogElencoTema {
  id: number;
  name: string;
  slug: string;
  /** `avulso` = item sem elenco, que veste ficha própria (fase 1). */
  kind: "tema" | "avulso";
  /** Ficha do item avulso — `null` num tema, onde a ficha é de cada personagem. */
  figurino_sheet_id: number | null;
  characters: CatalogElencoCharacter[];
}

/**
 * Temas ativos + Personagens ativos do catálogo, para a busca de elenco em Novo Evento
 * (feature 185, US4) — inclui `figurino_sheet_id` (dado interno), por isso não reusa a grade
 * pública (`GET /api/catalogo`).
 */
export function useCatalogElencoBusca() {
  return useQuery<{ temas: CatalogElencoTema[] }>({
    queryKey: ["catalogo-elenco-busca"],
    queryFn: () => apiFetch<{ temas: CatalogElencoTema[] }>("/api/catalogo/elenco-busca"),
  });
}
