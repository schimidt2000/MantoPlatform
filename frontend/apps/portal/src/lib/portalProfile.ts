import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

const ME_KEY = ["portal", "auth", "me"] as const;
const PROFILE_KEY = ["portal", "profile"] as const;

interface PhotoUploadResult {
  photo_face_url: string | null;
  photo_full_url: string | null;
}

/** Item do portfólio do talento: foto de atuação ou link (Vimeo, YouTube…). */
export interface PortalMediaItem {
  id: number;
  media_type: "photo" | "link";
  label: string | null;
  file_url: string | null;
  url: string | null;
  created_at: string | null;
}

/** Perfil completo do talento (`GET /api/portal/profile`). */
export interface PortalProfile {
  id: number;
  cpf: string | null;
  full_name: string;
  artistic_name: string | null;
  phone: string | null;
  email_contact: string | null;
  gender: string | null;
  race: string | null;
  languages: string | null;
  skills: string | null;
  birth_date: string | null;
  height_cm: number | null;
  clothing_size_top: string | null;
  clothing_size_bottom: string | null;
  shoe_size: string | null;
  pix_key: string | null;
  pix_key_type: string | null;
  pix_key_secondary: string | null;
  rg: string | null;
  has_visa: boolean;
  passport_visa_text: string | null;
  cnh_expiration: string | null;
  cnh_file_url: string | null;
  car_brand: string | null;
  car_model: string | null;
  car_year: string | null;
  car_plate: string | null;
  photo_face_url: string | null;
  photo_full_url: string | null;
  media: PortalMediaItem[];
  max_photos: number;
}

/** Campos que o talento pode editar — PATCH parcial: só o que for enviado é alterado. */
export type PortalProfilePatch = Partial<
  Pick<
    PortalProfile,
    | "full_name"
    | "artistic_name"
    | "phone"
    | "email_contact"
    | "gender"
    | "race"
    | "languages"
    | "skills"
    | "birth_date"
    | "height_cm"
    | "clothing_size_top"
    | "clothing_size_bottom"
    | "shoe_size"
    | "pix_key"
    | "pix_key_type"
    | "pix_key_secondary"
    | "rg"
    | "has_visa"
    | "passport_visa_text"
    | "cnh_expiration"
    | "car_brand"
    | "car_model"
    | "car_year"
    | "car_plate"
  >
>;

/** Perfil completo do talento logado. */
export function useProfile() {
  return useQuery({
    queryKey: PROFILE_KEY,
    queryFn: () => apiFetch<PortalProfile>("/api/portal/profile"),
  });
}

/** Atualiza campos do perfil (PATCH parcial) e sincroniza o cache do talento no header. */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation<PortalProfile, Error, PortalProfilePatch>({
    mutationFn: (patch) =>
      apiFetch<PortalProfile>("/api/portal/profile", {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: (profile) => {
      queryClient.setQueryData(PROFILE_KEY, profile);
      queryClient.invalidateQueries({ queryKey: ME_KEY });
    },
  });
}

/** Adiciona uma foto de atuação ao portfólio (limite devolvido em `max_photos`). */
export function useAddPortfolioPhoto() {
  const queryClient = useQueryClient();
  return useMutation<PortalProfile, Error, { file: File; label?: string }>({
    mutationFn: ({ file, label }) => {
      const form = new FormData();
      form.append("file", file);
      if (label) form.append("label", label);
      return apiFetch<PortalProfile>("/api/portal/profile/media/photo", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: (profile) => queryClient.setQueryData(PROFILE_KEY, profile),
  });
}

/** Adiciona um link de portfólio (Vimeo, YouTube…). */
export function useAddPortfolioLink() {
  const queryClient = useQueryClient();
  return useMutation<PortalProfile, Error, { url: string; label?: string }>({
    mutationFn: (body) =>
      apiFetch<PortalProfile>("/api/portal/profile/media/link", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (profile) => queryClient.setQueryData(PROFILE_KEY, profile),
  });
}

/** Remove um item do portfólio — confirmar com `window.confirm` antes de chamar. */
export function useDeletePortfolioItem() {
  const queryClient = useQueryClient();
  return useMutation<PortalProfile, Error, number>({
    mutationFn: (mediaId) =>
      apiFetch<PortalProfile>(`/api/portal/profile/media/${mediaId}`, { method: "DELETE" }),
    onSuccess: (profile) => queryClient.setQueryData(PROFILE_KEY, profile),
  });
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
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY });
    },
  });
}

/** Envia um novo arquivo de CNH, substituindo o anterior. */
export function useDocumentUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiFetch<{ cnh_file_url: string | null }>("/api/portal/profile/document", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY });
    },
  });
}
