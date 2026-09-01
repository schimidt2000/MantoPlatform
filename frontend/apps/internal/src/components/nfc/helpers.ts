import { ApiRequestError } from "@manto/api-client";

/**
 * Miúdos compartilhados da tela de Tags NFC (features 255/261/265) — extraídos de
 * `Tags3DPage.tsx` quando a página ganhou a aba de revisão de vídeos e os diálogos
 * viraram arquivos próprios em `components/nfc/`.
 */

/** Mensagem de campo devolvida pela API (400 com `fields`). */
export function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

/** URL pública completa da tag — o que se grava na tag física e se copia daqui. */
export function publicUrl(code: string): string {
  return `${window.location.origin}/nfc/${code}`;
}

/** Extensões aceitas — espelha `NFC_DELIVERY_VIDEO_EXTENSIONS` de `app/constants.py`. */
export const NFC_VIDEO_ACCEPT = ".mp4,.mov,.webm,.m4v";
