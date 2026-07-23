import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

const ME_KEY = ["portal", "auth", "me"] as const;

interface PhotoUploadResult {
  photo_face_url: string | null;
  photo_full_url: string | null;
}

/** Envia uma nova foto de rosto (`kind: "face"`) ou corpo inteiro (`kind: "full"`). */
export function usePhotoUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, file }: { kind: "face" | "full"; file: File }) => {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file);
      return apiFetch<PhotoUploadResult>("/api/portal/profile/photo", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(ME_KEY, (prev: unknown) =>
        prev && typeof prev === "object" ? { ...prev, ...result } : prev,
      );
    },
  });
}

/** Envia um novo arquivo de CNH, substituindo o anterior. */
export function useDocumentUpload() {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiFetch<{ cnh_file_url: string | null }>("/api/portal/profile/document", {
        method: "POST",
        body: form,
      });
    },
  });
}
