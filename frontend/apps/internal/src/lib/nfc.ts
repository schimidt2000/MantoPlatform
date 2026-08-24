import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Tags NFC das peças 3D (feature 255) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/3d/nfc*` (`contracts/nfc-api.md`): a tela `/3d/tags`
 * consome daqui, nenhum `fetch` avulso. A tag nunca é apagada — o contrato só tem listagem,
 * lote e edição dos campos mutáveis (evento, situação, observações).
 */

export interface NfcTagItemRef {
  id: number;
  name: string;
  /** Passar por `assetUrl()` antes de exibir. */
  photo_url: string;
  nfc_prefix: string | null;
}

export interface NfcTagEventRef {
  id: number;
  title: string;
  start_at: string | null;
}

/** Entrega de vídeo ativa da tag (feature 261) — `null` quando não há vídeo enviado ainda. */
export interface NfcTagVideoDelivery {
  id: number;
  kind: "video";
  title: string | null;
  /** Nome do arquivo em disco — só para exibir, nunca é URL (o arquivo é servido por código). */
  file_name: string | null;
  created_at: string | null;
}

export interface NfcTag {
  id: number;
  /** Código gravado na tag física — imutável e eterno (`/nfc/<code>`). */
  code: string;
  /** Nº humano por produto (1, 2, 3…): o rótulo que a equipe anota na tagzinha ao gravar. */
  sequence: number;
  item: NfcTagItemRef;
  event: NfcTagEventRef | null;
  /** Cliente DIRETA da tag (campanha/brinde sem show) — independente do evento. */
  client: { id: number; name: string } | null;
  /** Nome resolvido pelo servidor: cliente direta quando houver, senão contratante do evento. */
  client_name: string | null;
  /** `true` = `client_name` veio do vínculo direto (editável na tag), não do evento. */
  client_direct: boolean;
  is_active: boolean;
  notes: string | null;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string | null;
  video_delivery: NfcTagVideoDelivery | null;
}

export interface NfcTagListResponse {
  tags: NfcTag[];
}

const NFC_KEY = ["nfc-tags"] as const;

/** Todas as tags, ordenadas por produto + nº sequencial. */
export function useNfcTags() {
  return useQuery<NfcTagListResponse>({
    queryKey: NFC_KEY,
    queryFn: () => apiFetch<NfcTagListResponse>("/api/3d/nfc"),
  });
}

/** Gera um lote avulso (estoque, sem evento) — o servidor numera e sorteia os códigos. */
export function useGerarLoteNfc() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { item_id: number; quantity: number }) =>
      apiFetch<NfcTagListResponse>("/api/3d/nfc/lote", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

export interface UpdateNfcTagInput {
  /** `null` desassocia do evento; omitido mantém. */
  event_id?: number | null;
  /** Cliente DIRETA (sem show): `null` desassocia; omitido mantém. */
  client_id?: number | null;
  is_active?: boolean;
  notes?: string;
}

/** Edita os únicos campos mutáveis de uma tag (código e nº nunca mudam). */
export function useAtualizarNfcTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateNfcTagInput }) =>
      apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

// ── Entregas (feature 261) ───────────────────────────────────────────────────

export interface EnviarNfcVideoInput {
  tagId: number;
  file: File;
  title?: string;
}

/** Envia (ou substitui) o vídeo da tag — multipart, mesmo padrão de `eventAttachments.ts`. */
export function useEnviarNfcVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, file, title }: EnviarNfcVideoInput) => {
      const form = new FormData();
      form.append("file", file);
      form.append("kind", "video");
      if (title) form.append("title", title);
      return apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${tagId}/entregas`, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

/** Remove a entrega de vídeo da tag (linha + arquivo do disco). */
export function useRemoverNfcVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, deliveryId }: { tagId: number; deliveryId: number }) =>
      apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${tagId}/entregas/${deliveryId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}
