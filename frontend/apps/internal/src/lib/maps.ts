import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Mesma regra do backend (`AUTOCOMPLETE_MIN_CHARS`) — abaixo disso nem consultamos o Google. */
export const ADDRESS_MIN_CHARS = 3;
/** Espera depois da última tecla antes de disparar a busca — economiza quota do Places. */
const DEBOUNCE_MS = 350;

/** Sugestão de endereço devolvida por `GET /api/maps/address-autocomplete` (feature 195). */
export interface AddressSuggestion {
  description: string;
  place_id: string;
}

/** Aplica debounce a um valor — evita uma requisição por tecla digitada. */
function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/**
 * Sugestões de endereço do Google Places, via proxy do backend (feature 195).
 *
 * A chave do Maps nunca chega ao navegador: o hook fala só com `/api/maps/address-autocomplete`.
 * A busca é debounced e só dispara a partir de `ADDRESS_MIN_CHARS` caracteres.
 */
export function useAddressAutocomplete(query: string) {
  const debouncedQuery = useDebounced(query.trim(), DEBOUNCE_MS);
  const enabled = debouncedQuery.length >= ADDRESS_MIN_CHARS;

  const result = useQuery<AddressSuggestion[]>({
    queryKey: ["maps-address-autocomplete", debouncedQuery],
    queryFn: async () => {
      const data = await apiFetch<{ items: AddressSuggestion[] }>(
        `/api/maps/address-autocomplete?q=${encodeURIComponent(debouncedQuery)}`,
      );
      return data.items;
    },
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  return {
    suggestions: result.data ?? [],
    /** Inclui o intervalo do debounce, para o campo já mostrar "Buscando…" enquanto se digita. */
    isLoading: enabled && (result.isFetching || debouncedQuery !== query.trim()),
    isError: result.isError,
  };
}
