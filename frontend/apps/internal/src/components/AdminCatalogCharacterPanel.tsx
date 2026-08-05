import { useMemo, useState, type DragEvent } from "react";
import { assetUrl, ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import {
  useAdminCatalogo,
  useAdoptGalleryPhoto,
  useAdoptItemAsCharacter,
  useCreateCharacter,
  useDeleteCharacter,
  useSetOwnPage,
  useToggleOwnPage,
  useUpdateCharacter,
  type CatalogCharacter,
} from "../lib/adminCatalogo";
import { useFigurinoSheets } from "../lib/figurino";
import { FigurinoSheetPicker } from "./FigurinoSheetPicker";
import { CATALOG_PHOTO_DRAG_TYPE } from "../pages/AdminCatalogoFormPage";

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

/**
 * Busca de itens do catálogo para vincular/adotar (feature 209). Exclui o próprio tema,
 * itens que já são página de alguém e itens com elenco próprio (temas) — o backend valida
 * de novo, aqui é só para a lista não oferecer opções inválidas.
 */
function CatalogItemSearch({
  temaId,
  actionLabel,
  pending,
  onPick,
}: {
  temaId: number;
  actionLabel: string;
  pending: boolean;
  onPick: (itemId: number) => void;
}) {
  const [query, setQuery] = useState("");
  const list = useAdminCatalogo({ q: query.trim() || undefined });

  const results = useMemo(
    () =>
      (list.data?.items ?? [])
        .filter(
          (item) =>
            item.id !== temaId && !item.parte_de_tema && item.characters_total === 0,
        )
        .slice(0, 8),
    [list.data, temaId],
  );

  return (
    <div className="space-y-2">
      <input
        type="search"
        className={INPUT}
        placeholder="Buscar item do catálogo…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {query.trim().length >= 2 && (
        <ul className="max-h-56 divide-y divide-line overflow-y-auto rounded-md border border-line">
          {results.map((item) => (
            <li key={item.id} className="flex items-center gap-2 p-2">
              <span className="h-9 w-9 flex-none overflow-hidden rounded bg-surface-2">
                {item.cover_url && (
                  <img src={assetUrl(item.cover_url)} alt="" className="h-full w-full object-cover" />
                )}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm text-ink">{item.name}</span>
              <Button
                variant="outline"
                size="sm"
                loading={pending}
                onClick={() => onPick(item.id)}
              >
                {actionLabel}
              </Button>
            </li>
          ))}
          {results.length === 0 && !list.isLoading && (
            <li className="p-2 text-xs text-muted">Nenhum item disponível para “{query}”.</li>
          )}
        </ul>
      )}
    </div>
  );
}

/** Controles da "página única" de um personagem (feature 209, caso Coelho). */
function OwnPageControls({
  itemId,
  character,
}: {
  itemId: number;
  character: CatalogCharacter;
}) {
  const setOwnPage = useSetOwnPage(itemId);
  const togglePage = useToggleOwnPage(itemId);
  const [linking, setLinking] = useState(false);
  const own = character.own_item;

  if (own) {
    return (
      <div className="space-y-1.5">
        <label className={LABEL}>Página própria</label>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2 text-ink">
            <input
              type="checkbox"
              checked={own.is_active}
              disabled={togglePage.isPending}
              onChange={(e) =>
                togglePage.mutate({ characterId: character.id, enabled: e.target.checked })
              }
            />
            Página única (aparece na vitrine e na busca)
          </label>
          <a
            href={`/catalogo/${own.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-accent hover:underline"
          >
            Abrir página ↗
          </a>
          <button
            type="button"
            className="text-xs text-muted hover:text-red"
            onClick={() => setOwnPage.mutate({ characterId: character.id, ownItemId: null })}
          >
            Desvincular
          </button>
        </div>
        <p className="text-xs text-muted">
          Desmarcar esconde a página da vitrine sem apagar nada — o personagem continua no
          elenco deste tema.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <label className={LABEL}>Página própria</label>
      {linking ? (
        <CatalogItemSearch
          temaId={itemId}
          actionLabel="Vincular"
          pending={setOwnPage.isPending}
          onPick={(pickedId) =>
            setOwnPage.mutate(
              { characterId: character.id, ownItemId: pickedId },
              { onSuccess: () => setLinking(false) },
            )
          }
        />
      ) : (
        <Button variant="outline" size="sm" onClick={() => setLinking(true)}>
          Vincular a um item existente…
        </Button>
      )}
      <p className="text-xs text-muted">
        Sem página própria, o personagem existe só no elenco do tema (não aparece na busca).
      </p>
    </div>
  );
}

/** Painel de gerenciamento de Personagens filhos de um Tema (feature 185, FR-010). */
export function AdminCatalogCharacterPanel({ itemId, characters }: AdminCatalogCharacterPanelProps) {
  const figurinoQuery = useFigurinoSheets();
  const createCharacter = useCreateCharacter(itemId);
  const updateCharacter = useUpdateCharacter(itemId);
  const deleteCharacter = useDeleteCharacter(itemId);

  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showAdopt, setShowAdopt] = useState(false);
  const adoptItem = useAdoptItemAsCharacter(itemId);

  // Drop target do drag-and-drop "foto da galeria → personagem" (feature: adotar foto).
  const adoptPhoto = useAdoptGalleryPhoto(itemId);
  const [dropTargetId, setDropTargetId] = useState<number | null>(null);

  const sorted = [...characters].sort((a, b) => a.position - b.position);
  const figurinoSheets = figurinoQuery.data?.items ?? [];

  function handlePhotoDragOver(event: DragEvent, characterId: number) {
    if (!event.dataTransfer.types.includes(CATALOG_PHOTO_DRAG_TYPE)) return;
    if (adoptPhoto.isPending) return; // drops em rajada intercalam invalidações — um por vez
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setDropTargetId(characterId);
  }

  function handlePhotoDrop(event: DragEvent, character: CatalogCharacter) {
    const raw = event.dataTransfer.getData(CATALOG_PHOTO_DRAG_TYPE);
    setDropTargetId(null);
    if (!raw) return;
    event.preventDefault();
    // O confirm sai do handler de drop via setTimeout: um diálogo modal SÍNCRONO aqui
    // seguraria a sessão de drag aberta (ghost congelado, dragend da origem adiado) e
    // alguns engines suprimem o diálogo durante drag-and-drop.
    const imageId = Number(raw);
    setTimeout(() => {
      if (
        character.photo_url &&
        !window.confirm(`Substituir a foto atual de "${character.name}" pela foto arrastada?`)
      ) {
        return;
      }
      setFieldError(null);
      adoptPhoto.mutate(
        { characterId: character.id, imageId },
        {
          onError: (err) => {
            if (err instanceof ApiRequestError) setFieldError(err.message);
          },
        },
      );
    }, 0);
  }

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
          <p className="text-xs text-muted">
            Dica: arraste uma foto <strong>já salva</strong> da galeria acima até um personagem
            para usá-la como foto dele (fotos recém-adicionadas precisam ser salvas antes).
          </p>
        )}
        {sorted.length > 0 && (
          <ul className="space-y-3">
            {sorted.map((character, idx) => (
              <li
                key={character.id}
                className={`rounded-md border-b border-line pb-3 transition-shadow duration-200 last:border-none ${
                  dropTargetId === character.id ? "ring-2 ring-accent" : ""
                }`}
                onDragOver={(e) => handlePhotoDragOver(e, character.id)}
                onDragLeave={() => setDropTargetId((prev) => (prev === character.id ? null : prev))}
                onDrop={(e) => handlePhotoDrop(e, character)}
              >
                <div className="flex items-center gap-3">
                  <div className="relative h-12 w-12 flex-none overflow-hidden rounded-md bg-surface-2">
                    {character.photo_url && (
                      <img
                        src={assetUrl(character.photo_url)}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    )}
                    {adoptPhoto.isPending && adoptPhoto.variables?.characterId === character.id && (
                      <span className="absolute inset-0 flex items-center justify-center bg-panel/70 text-xs">
                        …
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{character.name}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
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
                      {character.own_item && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            character.own_item.is_active
                              ? "bg-accent-soft text-accent-dark"
                              : "bg-surface-2 text-muted"
                          }`}
                        >
                          {character.own_item.is_active ? "🔗 página única" : "🔗 página oculta"}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant={expandedId === character.id ? "default" : "outline"}
                      size="sm"
                      onClick={() =>
                        setExpandedId((prev) => (prev === character.id ? null : character.id))
                      }
                    >
                      Ficha & página
                    </Button>
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
                </div>

                {expandedId === character.id && (
                  <div className="mt-2 space-y-3 rounded-md bg-surface-2/50 p-3">
                    <div>
                      <label className={LABEL}>Ficha de figurino</label>
                      <FigurinoSheetPicker
                        value={character.figurino_sheet_id}
                        characterName={character.name}
                        disabled={updateCharacter.isPending}
                        onChange={(sheetId) =>
                          updateCharacter.mutate({
                            id: character.id,
                            input: { figurinoSheetId: sheetId },
                          })
                        }
                      />
                    </div>
                    <OwnPageControls itemId={itemId} character={character} />
                  </div>
                )}
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
            <FigurinoSheetPicker
              value={draft.figurinoSheetId}
              characterName={draft.name}
              onChange={(sheetId) => setDraft((d) => ({ ...d, figurinoSheetId: sheetId }))}
            />
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

        <div className="space-y-2 rounded-md border border-dashed border-line p-3">
          <p className="text-xs font-semibold text-muted">
            Adotar item existente como personagem
          </p>
          <p className="text-xs text-muted">
            Para itens que já têm página própria no catálogo (ex.: Coelho Branco → tema
            Alice): o item entra no elenco deste tema e CONTINUA com página e busca próprias.
          </p>
          {showAdopt ? (
            <CatalogItemSearch
              temaId={itemId}
              actionLabel="Adotar"
              pending={adoptItem.isPending}
              onPick={(pickedId) =>
                adoptItem.mutate(pickedId, {
                  onSuccess: () => setShowAdopt(false),
                  onError: (err) => {
                    if (err instanceof ApiRequestError) setFieldError(err.message);
                  },
                })
              }
            />
          ) : (
            <Button variant="outline" size="sm" onClick={() => setShowAdopt(true)}>
              🔗 Buscar item para adotar…
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
