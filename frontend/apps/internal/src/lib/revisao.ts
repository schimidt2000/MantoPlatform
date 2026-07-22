import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

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
      return apiFetch<RevisaoSpaceSummary & { saved: number; errors: string[] }>("/api/revisao", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["revisao-spaces"] });
    },
  });
}

export function useUploadRevisaoAssets(spaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      return apiFetch<{ saved: number; errors: string[] }>(
        `/api/revisao/${spaceId}/upload`,
        { method: "POST", body: form },
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

export function useReplaceRevisaoAsset(assetId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return apiFetch<{ version: number }>(`/api/revisao/asset/${assetId}/replace`, {
        method: "POST",
        body: form,
      });
    },
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
