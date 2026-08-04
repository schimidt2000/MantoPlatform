import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

/**
 * Autocomplete de endereço do Google Places, via proxy do backend (feature 195; movido para cá na
 * 205 para o checkout público reusar a mesma implementação).
 *
 * A chave do Maps **nunca** chega ao navegador — o hook fala só com o endpoint do Flask
 * (Princípio XII.4). A busca é debounced e só dispara a partir de `ADDRESS_MIN_CHARS`, para
 * economizar quota do Places (XII.5).
 *
 * O endpoint é parâmetro porque existem dois com o mesmo contrato e gates diferentes:
 * `/api/maps/address-autocomplete` (staff autenticado) e `/api/virtuais/enderecos/autocomplete`
 * (checkout público, com teto por origem). A lógica é uma só.
 */

/** Mesma regra do backend (`AUTOCOMPLETE_MIN_CHARS`) — abaixo disso nem consultamos o Google. */
export const ADDRESS_MIN_CHARS = 3;

/** Espera depois da última tecla antes de disparar a busca — economiza quota do Places. */
const DEBOUNCE_MS = 350;

/** Endpoint padrão: o do staff autenticado. */
export const ADDRESS_ENDPOINT_INTERNAL = "/api/maps/address-autocomplete";

/** Endpoint do checkout público da Loja de Interações Virtuais (feature 205). */
export const ADDRESS_ENDPOINT_PUBLIC = "/api/virtuais/enderecos/autocomplete";

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

export function useAddressAutocomplete(
  query: string,
  endpoint: string = ADDRESS_ENDPOINT_INTERNAL,
) {
  const debouncedQuery = useDebounced(query.trim(), DEBOUNCE_MS);
  const enabled = debouncedQuery.length >= ADDRESS_MIN_CHARS;

  const result = useQuery<AddressSuggestion[]>({
    queryKey: ["address-autocomplete", endpoint, debouncedQuery],
    queryFn: async () => {
      const data = await apiFetch<{ items: AddressSuggestion[] }>(
        `${endpoint}?q=${encodeURIComponent(debouncedQuery)}`,
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
