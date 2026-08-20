import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE, ApiRequestError, apiFetch, type ApiErrorBody } from "@manto/api-client";

/**
 * Espelho de `review_ops._MEDIA_EXTS` + `_MAX_FILE` do backend. A dupla existe para o arquivo
 * inválido ser barrado ANTES do upload — subir 300 MB para descobrir a rejeição no fim era o
 * caminho do "anexei e o vídeo sumiu". Só os formatos que o navegador reproduz entram na lista
 * de vídeo; alargar aqui sem alargar o player só muda o lugar da frustração.
 */
export const REVISAO_EXTS: Record<MediaType, string[]> = {
  video: [".mp4", ".mov", ".webm", ".m4v", ".ogv"],
  audio: [".mp3", ".wav", ".m4a", ".ogg", ".aac"],
  image: [".jpg", ".jpeg", ".png", ".webp", ".gif"],
  pdf: [".pdf"],
};
export const REVISAO_MAX_MB = 512;
/** Valor do `accept` dos inputs de arquivo — extensões explícitas, não `video/*`: o seletor do
 * sistema já esconde .mkv/.avi em vez de deixá-los entrar para serem rejeitados depois. */
export const REVISAO_ACCEPT = Object.values(REVISAO_EXTS).flat().join(",");

/** Valida arquivos antes do envio. Devolve uma mensagem por problema (vazio = tudo ok). */
export function validateRevisaoFiles(files: File[]): string[] {
  const problems: string[] = [];
  const allExts = Object.values(REVISAO_EXTS).flat();
  const maxBytes = REVISAO_MAX_MB * 1024 * 1024;
  let total = 0;
  for (const f of files) {
    const ext = f.name.includes(".") ? `.${f.name.split(".").pop()!.toLowerCase()}` : "";
    if (!allExts.includes(ext)) {
      problems.push(
        `${f.name}: formato não aceito. Vídeo: MP4, MOV, WEBM, M4V ou OGV (os que o navegador reproduz).`,
      );
      continue;
    }
    if (f.size > maxBytes) {
      problems.push(`${f.name}: arquivo acima de ${REVISAO_MAX_MB} MB.`);
      continue;
    }
    total += f.size;
  }
  if (total > maxBytes) {
    problems.push(`Os arquivos juntos passam de ${REVISAO_MAX_MB} MB — envie menos por vez.`);
  }
  return problems;
}

/**
 * Upload multipart com progresso real. O `fetch` não expõe progresso de envio, e um vídeo de
 * centenas de MB sobe por minutos — sem barra, o silêncio parecia conclusão e a aba era fechada
 * no meio (o "anexei e não apareceu" da feature 254). Mesmo contrato de erro do `apiFetch`:
 * envelope da API vira `ApiRequestError`, resposta sem envelope vira a mensagem genérica.
 */
function uploadForm<T>(
  path: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    xhr.withCredentials = true;
    xhr.responseType = "text";
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && e.total > 0) onProgress(e.loaded / e.total);
      };
    }
    xhr.onerror = () => reject(new Error("Falha de rede durante o envio. Tente novamente."));
    xhr.onload = () => {
      let parsed: unknown = null;
      try {
        parsed = JSON.parse(xhr.responseText || "null");
      } catch {
        parsed = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(parsed as T);
        return;
      }
      const envelope = (parsed as { error?: ApiErrorBody } | null)?.error;
      const body: ApiErrorBody =
        envelope && typeof envelope.message === "string"
          ? envelope
          : { message: "Ocorreu um erro inesperado. Tente novamente." };
      reject(new ApiRequestError(xhr.status, body));
    };
    xhr.send(form);
  });
}

export interface RevisaoSpaceSummary {
  id: number;
  title: string;
  description: string;
  created_at: string;
  creator_name: string;
  asset_count: number;
}

export interface RevisaoListResponse {
  items: RevisaoSpaceSummary[];
  can_create: boolean;
}

export function useRevisaoSpaces() {
  return useQuery<RevisaoListResponse>({
    queryKey: ["revisao-spaces"],
    queryFn: () => apiFetch<RevisaoListResponse>("/api/revisao"),
  });
}

export interface ReviewerOption {
  id: number;
  name: string;
}

export function useReviewerOptions() {
  return useQuery<{ items: ReviewerOption[] }>({
    queryKey: ["revisao-reviewer-options"],
    queryFn: () => apiFetch<{ items: ReviewerOption[] }>("/api/revisao/reviewer-options"),
  });
}

export type MediaType = "video" | "audio" | "image" | "pdf";

export type ReviewStatus = "em_revisao" | "aprovado" | "precisa_ajustes" | "rejeitado";

export interface RevisaoAssetSummary {
  id: number;
  media_type: MediaType;
  original_name: string;
  position: number;
  version: number;
  is_available: boolean;
  days_left: number | null;
  finalized_at: string | null;
  file_url: string | null;
  status: ReviewStatus;
}

export interface RevisaoSpaceDetail extends RevisaoSpaceSummary {
  can_manage: boolean;
  assets: RevisaoAssetSummary[];
  reviewer_ids: number[];
}

export function useRevisaoSpace(id: number) {
  return useQuery<RevisaoSpaceDetail>({
    queryKey: ["revisao-spaces", id],
    queryFn: () => apiFetch<RevisaoSpaceDetail>(`/api/revisao/${id}`),
    enabled: Number.isFinite(id),
  });
}

export interface CreateSpaceInput {
  title: string;
  description?: string;
  reviewerIds: number[];
  files: File[];
  /** Fração 0..1 do corpo já enviado — alimenta a barra de progresso da página. */
  onProgress?: (fraction: number) => void;
}

export function useCreateRevisaoSpace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSpaceInput) => {
      const form = new FormData();
      form.set("title", input.title);
      form.set("description", input.description ?? "");
      input.reviewerIds.forEach((id) => form.append("reviewer_ids[]", String(id)));
      input.files.forEach((f) => form.append("files", f));
      return uploadForm<RevisaoSpaceSummary & { saved: number; errors: string[] }>(
        "/api/revisao",
        form,
        input.onProgress,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces"] });
    },
  });
}

export interface UploadAssetsInput {
  files: File[];
  onProgress?: (fraction: number) => void;
}

export function useUploadRevisaoAssets(spaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ files, onProgress }: UploadAssetsInput) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      return uploadForm<{ saved: number; errors: string[] }>(
        `/api/revisao/${spaceId}/upload`,
        form,
        onProgress,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces", spaceId] });
    },
  });
}

export function useUpdateRevisaoReviewers(spaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reviewerIds: number[]) =>
      apiFetch<{ reviewer_ids: number[] }>(`/api/revisao/${spaceId}/reviewers`, {
        method: "PATCH",
        body: JSON.stringify({ reviewer_ids: reviewerIds }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces", spaceId] });
    },
  });
}

export function useDeleteRevisaoSpace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (spaceId: number) =>
      apiFetch<void>(`/api/revisao/${spaceId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces"] });
    },
  });
}

export interface VersionInfo {
  version_number: number;
  file_url: string | null;
  original_name: string;
  is_available: boolean;
  created_at?: string;
}

export interface RevisaoAssetDetail {
  space_id: number;
  space_title: string;
  can_manage: boolean;
  asset: RevisaoAssetSummary;
  viewing_version: number | null;
  version_file: VersionInfo | null;
  history: VersionInfo[];
}

export function useRevisaoAsset(spaceId: number, assetId: number, version?: number) {
  const qs = version ? `?v=${version}` : "";
  return useQuery<RevisaoAssetDetail>({
    queryKey: ["revisao-asset", spaceId, assetId, version],
    queryFn: () =>
      apiFetch<RevisaoAssetDetail>(`/api/revisao/${spaceId}/asset/${assetId}${qs}`),
    enabled: Number.isFinite(spaceId) && Number.isFinite(assetId),
  });
}

export function useDeleteRevisaoAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assetId: number) =>
      apiFetch<void>(`/api/revisao/asset/${assetId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces"] });
    },
  });
}

export interface ReplaceAssetInput {
  file: File;
  onProgress?: (fraction: number) => void;
}

export function useReplaceRevisaoAsset(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: ReplaceAssetInput) => {
      const form = new FormData();
      form.set("file", file);
      return uploadForm<{ version: number }>(
        `/api/revisao/asset/${assetId}/replace`,
        form,
        onProgress,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-asset"] });
    },
  });
}

export function useUpdateAssetStatus(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (status: ReviewStatus) =>
      apiFetch<{ status: ReviewStatus }>(`/api/revisao/asset/${assetId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-asset"] });
    },
  });
}

export function useFinalizeRevisaoAsset(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ finalized_at: string }>(`/api/revisao/asset/${assetId}/finalize`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-asset"] });
    },
  });
}

export interface RevisaoComment {
  id: number;
  body: string;
  author: string;
  author_id: number;
  timecode: number | null;
  page: number | null;
  pos_x: number | null;
  pos_y: number | null;
  version_number: number;
  resolved: boolean;
  resolved_by_name: string | null;
  resolved_at: string | null;
  created_at: string;
  can_resolve: boolean;
  can_delete: boolean;
}

export function useRevisaoComments(assetId: number, version?: number) {
  const qs = version ? `?v=${version}` : "";
  return useQuery<RevisaoComment[]>({
    queryKey: ["revisao-comments", assetId, version],
    queryFn: () =>
      apiFetch<RevisaoComment[]>(`/api/revisao/asset/${assetId}/comments${qs}`),
    enabled: Number.isFinite(assetId),
  });
}

export interface AddCommentInput {
  body: string;
  timecode?: number;
  page?: number;
  pos_x?: number;
  pos_y?: number;
  version?: number;
}

export function useAddRevisaoComment(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AddCommentInput) =>
      apiFetch<RevisaoComment>(`/api/revisao/asset/${assetId}/comment`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-comments", assetId] });
    },
  });
}

export function useToggleResolveComment(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: number) =>
      apiFetch<RevisaoComment>(`/api/revisao/comment/${commentId}/resolve`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-comments", assetId] });
    },
  });
}

export function useDeleteComment(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: number) =>
      apiFetch<void>(`/api/revisao/comment/${commentId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-comments", assetId] });
    },
  });
}
