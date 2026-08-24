import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/** Produto (item do Acervo 3D) da tag — `null` quando o código não resolve. */
export interface NfcProduct {
  name: string;
  photo_url: string;
}

/**
 * Uma entrega anexada à tag (feature 261) — hoje só `kind: "video"`. `media_url` já vem pronta
 * para `assetUrl()`; passar por `/uploads` seria errado aqui, o arquivo mora fora dali de
 * propósito (ver `app/config.py: NFC_MEDIA_FOLDER`).
 */
export interface NfcDelivery {
  kind: "video";
  /** `null` → a página usa a copy padrão ("Um vídeo especial para você"). */
  title: string | null;
  media_url: string;
}

/**
 * Resolução pública de um código de tag NFC — espelho de `contracts/nfc-api.md` (feature 255,
 * estendido na 261).
 *
 * O endpoint responde SEMPRE 200 com este shape: código inexistente e tag desativada são
 * indistinguíveis (`product: null`, `deliveries: []`), então a página não tem caminho de erro —
 * só o modo genérico. `campaign` é o gancho do sistema futuro de campanhas: hoje sempre `null`.
 */
export interface NfcResolution {
  product: NfcProduct | null;
  campaign: null;
  deliveries: NfcDelivery[];
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
