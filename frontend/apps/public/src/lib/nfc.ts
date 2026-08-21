import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Produto (item do Acervo 3D) da tag — `null` quando o código não resolve. */
export interface NfcProduct {
  name: string;
  photo_url: string;
}

/**
 * Resolução pública de um código de tag NFC — espelho de `contracts/nfc-api.md` (feature 255).
 *
 * O endpoint responde SEMPRE 200 com este shape: código inexistente e tag desativada são
 * indistinguíveis (`product: null`), então a página não tem caminho de erro — só o modo
 * genérico. `campaign` é o gancho do sistema futuro de campanhas: hoje sempre `null`.
 */
export interface NfcResolution {
  product: NfcProduct | null;
  campaign: null;
  instagram_url: string;
}

/** Resolve o código no servidor — é o servidor quem decide TODO o conteúdo da página. */
export function useNfcResolution(code: string) {
  return useQuery<NfcResolution>({
    queryKey: ["nfc", code],
    queryFn: () => apiFetch<NfcResolution>(`/api/nfc/${encodeURIComponent(code)}`),
    retry: false,
    // A URL está gravada numa tag física: o conteúdo não muda durante a visita.
    staleTime: Infinity,
  });
}
