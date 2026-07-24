import { useState } from "react";
import { assetUrl, ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import {
  useCreateCharacter,
  useDeleteCharacter,
  useUpdateCharacter,
  type CatalogCharacter,
} from "../lib/adminCatalogo";
import { useFigurinoSheets } from "../lib/figurino";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

interface AdminCatalogCharacterPanelProps {
  itemId: number;
  characters: CatalogCharacter[];
}

interface DraftState {
  name: string;
  videoUrl: string;
  figurinoSheetId: number | null;
  photo: File | null;
}

const EMPTY_DRAFT: DraftState = { name: "", videoUrl: "", figurinoSheetId: null, photo: null };

/** Painel de gerenciamento de Personagens filhos de um Tema (feature 185, FR-010). */
export function AdminCatalogCharacterPanel({ itemId, characters }: AdminCatalogCharacterPanelProps) {
  const figurinoQuery = useFigurinoSheets();
  const createCharacter = useCreateCharacter(itemId);
  const updateCharacter = useUpdateCharacter(itemId);
  const deleteCharacter = useDeleteCharacter(itemId);

  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const sorted = [...characters].sort((a, b) => a.position - b.position);
  const figurinoSheets = figurinoQuery.data?.items ?? [];

  function handleCreate() {
    setFieldError(null);
    createCharacter.mutate(
      {
        name: draft.name,
        videoUrl: draft.videoUrl,
        figurinoSheetId: draft.figurinoSheetId,
        photo: draft.photo ?? undefined,
      },
      {
        onSuccess: () => setDraft(EMPTY_DRAFT),
        onError: (err) => {
          if (err instanceof ApiRequestError) setFieldError(err.message);
        },
      },
    );
  }

  function moveCharacter(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= sorted.length) return;
    const a = sorted[index];
    const b = sorted[target];
    updateCharacter.mutate({ id: a.id, input: { name: a.name, position: b.position } });
    updateCharacter.mutate({ id: b.id, input: { name: b.name, position: a.position } });
  }

  function handleRemove(character: CatalogCharacter) {
    if (!window.confirm(`Excluir o personagem "${character.name}"? Essa ação não pode ser desfeita.`)) {
      return;
    }
    deleteCharacter.mutate(character.id);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Personagens</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {sorted.length > 0 && (
          <ul className="space-y-3">
            {sorted.map((character, idx) => (
              <li key={character.id} className="flex items-center gap-3 border-b border-line pb-3 last:border-none">
                <div className="h-12 w-12 flex-none overflow-hidden rounded-md bg-surface-2">
                  {character.photo_url && (
                    <img
                      src={assetUrl(character.photo_url)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{character.name}</p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                    <span className="text-xs text-muted">
                      {character.video_url ? "🎬 com vídeo" : "sem vídeo"}
                    </span>
                    {character.figurino_sheet_id ? (
                      <span className="rounded-full bg-green-soft px-2 py-0.5 text-xs font-medium text-green">
                        ✓{" "}
                        {figurinoSheets.find((f) => f.id === character.figurino_sheet_id)?.character_name ??
                          "figurino vinculado"}
                      </span>
                    ) : (
                      <span className="rounded-full bg-red-soft px-2 py-0.5 text-xs font-medium text-red">
                        ⚠ Sem ficha vinculada
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    className="text-muted disabled:opacity-30"
                    disabled={idx === 0}
                    onClick={() => moveCharacter(idx, -1)}
                    aria-label="Mover para cima"
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    className="text-muted disabled:opacity-30"
                    disabled={idx === sorted.length - 1}
                    onClick={() => moveCharacter(idx, 1)}
                    aria-label="Mover para baixo"
                  >
                    ›
                  </button>
                  <button
                    type="button"
                    className="text-red"
                    onClick={() => handleRemove(character)}
                    aria-label={`Excluir ${character.name}`}
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="space-y-2 rounded-md border border-dashed border-line p-3">
          <p className="text-xs font-semibold text-muted">Novo personagem</p>
          <div>
            <label className={LABEL} htmlFor="new-character-name">
              Nome
            </label>
            <input
              id="new-character-name"
              aria-label="Nome do personagem"
              className={INPUT}
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="new-character-video-url">
              URL de vídeo (Drive/MP4/Vimeo)
            </label>
            <input
              id="new-character-video-url"
              aria-label="URL de vídeo do personagem"
              className={INPUT}
              value={draft.videoUrl}
              onChange={(e) => setDraft((d) => ({ ...d, videoUrl: e.target.value }))}
            />
          </div>
          <div>
            <label className={LABEL}>Foto</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="text-sm text-ink"
              onChange={(e) => setDraft((d) => ({ ...d, photo: e.target.files?.[0] ?? null }))}
            />
          </div>
          <div>
            <label className={LABEL}>Ficha de Figurino</label>
            <select
              className={INPUT}
              value={draft.figurinoSheetId ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  figurinoSheetId: e.target.value ? Number(e.target.value) : null,
                }))
              }
            >
              <option value="">🔍 Buscar figurino…</option>
              {figurinoSheets.map((sheet) => (
                <option key={sheet.id} value={sheet.id}>
                  {sheet.character_name}
                </option>
              ))}
            </select>
          </div>
          {fieldError && <p className="text-xs text-red">{fieldError}</p>}
          <Button
            variant="outline"
            size="sm"
            loading={createCharacter.isPending}
            disabled={!draft.name.trim()}
            onClick={handleCreate}
          >
            + Adicionar personagem
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
