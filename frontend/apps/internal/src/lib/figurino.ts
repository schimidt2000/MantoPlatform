import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface FigurinoPiece {
  name: string;
  qty: number;
}

/** Manutenções abertas nesta ficha (feature 225b). `null` quando o figurino está inteiro. */
export interface FigurinoManutencaoAlerta {
  abertas: number;
  /** True quando alguma delas impede a peça de ir para um evento. */
  impede_uso: boolean;
  titulos: string[];
}

export interface FigurinoSheetItem {
  id: number;
  character_name: string;
  /**
   * Quantos figurinos IGUAIS a Manto tem desta ficha (feature 235). Não confundir com o `qty`
   * de `FigurinoPiece` — aquele é "2 luvas" dentro de um figurino; este é "temos 3 Gatunos".
   */
  quantity: number;
  pieces: FigurinoPiece[];
  tags: string[];
  notes: string | null;
  photo_url: string | null;
  updated_at: string | null;
  created_at: string | null;
  manutencao: FigurinoManutencaoAlerta | null;
}

export interface MissingCharacter {
  character_name: string;
  character_name_norm: string;
}

export interface FigurinoList {
  items: FigurinoSheetItem[];
  chars_without_sheet: MissingCharacter[];
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
  tags?: string[];
  /** Omitido numa edição = não altera a quantidade guardada. */
  quantity?: number;
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

/** Descarta o alerta de "personagem sem ficha" para as ocorrências atuais (feature 183,
 * SUPERADMIN apenas — RBAC validado no backend). */
export function useDismissMissingCharacter() {
  const invalidate = useInvalidateFigurino();
  return useMutation<{ ok: boolean }, Error, string>({
    mutationFn: (characterNameNorm) =>
      apiFetch<{ ok: boolean }>("/api/figurino/faltantes/dispensar", {
        method: "POST",
        body: JSON.stringify({ character_name_norm: characterNameNorm }),
      }),
    onSuccess: invalidate,
  });
}

/** Vincula os cargos de evento pendentes de um personagem a uma ficha existente (feature 183,
 * SUPERADMIN apenas). */
export function useAssociateMissingCharacter() {
  const invalidate = useInvalidateFigurino();
  return useMutation<
    { ok: boolean; updated_role_count: number; sheet_id: number },
    Error,
    { characterNameNorm: string; sheetId: number }
  >({
    mutationFn: ({ characterNameNorm, sheetId }) =>
      apiFetch("/api/figurino/faltantes/associar", {
        method: "POST",
        body: JSON.stringify({ character_name_norm: characterNameNorm, sheet_id: sheetId }),
      }),
    onSuccess: invalidate,
  });
}
