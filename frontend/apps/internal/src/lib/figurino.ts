import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FigurinoPiece {
  name: string;
  qty: number;
}

export interface FigurinoSheetItem {
  id: number;
  character_name: string;
  pieces: FigurinoPiece[];
  notes: string | null;
  photo_url: string | null;
  updated_at: string | null;
  created_at: string | null;
}

export interface FigurinoList {
  items: FigurinoSheetItem[];
  chars_without_sheet: string[];
}

/** Lista as fichas de figurino (feature 154). Leitura aberta a qualquer autenticado. */
export function useFigurinoSheets() {
  return useQuery<FigurinoList>({
    queryKey: ["figurino"],
    queryFn: () => apiFetch<FigurinoList>("/api/figurino"),
  });
}

export interface FigurinoSheetInput {
  character_name: string;
  pieces: FigurinoPiece[];
  notes?: string;
}

function useInvalidateFigurino() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["figurino"] });
}

/** Cria uma ficha de figurino sem foto (feature 154). */
export function useCreateFigurinoSheet() {
  const invalidate = useInvalidateFigurino();
  return useMutation<FigurinoSheetItem, Error, FigurinoSheetInput>({
    mutationFn: (body) =>
      apiFetch<FigurinoSheetItem>("/api/figurino", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

/** Edita nome/peças/notas de uma ficha existente (feature 154). */
export function useEditFigurinoSheet() {
  const invalidate = useInvalidateFigurino();
  return useMutation<FigurinoSheetItem, Error, { id: number } & FigurinoSheetInput>({
    mutationFn: ({ id, ...body }) =>
      apiFetch<FigurinoSheetItem>(`/api/figurino/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

/** Exclui uma ficha de figurino (feature 154). */
export function useDeleteFigurinoSheet() {
  const invalidate = useInvalidateFigurino();
  return useMutation<{ ok: boolean }, Error, number>({
    mutationFn: (id) => apiFetch<{ ok: boolean }>(`/api/figurino/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

function useFigurinoPhotoMutation<TVars>(
  mutationFn: (vars: TVars) => Promise<FigurinoSheetItem>,
) {
  const queryClient = useQueryClient();
  return useMutation<FigurinoSheetItem, Error, TVars>({
    mutationFn,
    onSuccess: (updated) => {
      queryClient.setQueryData<FigurinoList>(["figurino"], (old) =>
        old ? { ...old, items: old.items.map((s) => (s.id === updated.id ? updated : s)) } : old,
      );
    },
  });
}

/** Envia/substitui a foto de uma ficha de figurino (feature 155). */
export function useUploadFigurinoPhoto() {
  return useFigurinoPhotoMutation<{ id: number; file: File }>(({ id, file }) => {
    const form = new FormData();
    form.append("photo", file);
    return apiFetch<FigurinoSheetItem>(`/api/figurino/${id}/photo`, { method: "POST", body: form });
  });
}

/** Remove a foto de uma ficha de figurino (feature 155). No-op seguro se já vazia. */
export function useRemoveFigurinoPhoto() {
  return useFigurinoPhotoMutation<number>((id) =>
    apiFetch<FigurinoSheetItem>(`/api/figurino/${id}/photo`, { method: "DELETE" }),
  );
}

/** Gira 90° a foto de uma ficha de figurino (feature 155). */
export function useRotateFigurinoPhoto() {
  return useFigurinoPhotoMutation<{ id: number; direction: "cw" | "ccw" }>(({ id, direction }) =>
    apiFetch<FigurinoSheetItem>(`/api/figurino/${id}/photo/rotate`, {
      method: "POST",
      body: JSON.stringify({ direction }),
    }),
  );
}
