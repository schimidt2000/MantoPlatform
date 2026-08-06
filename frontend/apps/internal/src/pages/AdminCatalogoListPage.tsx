import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, PageHeader, Skeleton } from "@manto/ui";
import {
  useAdminCatalogo,
  useDeleteCatalogItem,
  useToggleCatalogItemActive,
  useUpdateCharacterActiveStandalone,
  useDeleteCharacterStandalone,
  useMoveCharactersBulk,
  useLinkCharacterFigurino,
  type CatalogCharacterSummary,
  type CatalogListItem,
} from "../lib/adminCatalogo";
import { FigurinoSheetPicker } from "../components/FigurinoSheetPicker";
import { CatalogCardGrid } from "../components/CatalogCardGrid";
import { CatalogTreeView } from "../components/CatalogTreeView";
import { CatalogBulkActionBar } from "../components/CatalogBulkActionBar";
import { Modal } from "../components/Modal";

type ViewMode = "cards" | "tree";
const VIEW_MODE_KEY = "manto_admin_catalogo_view";

function loadViewMode(): ViewMode {
  const saved = window.localStorage.getItem(VIEW_MODE_KEY);
  return saved === "tree" ? "tree" : "cards";
}

export function AdminCatalogoListPage() {
  const [q, setQ] = useState("");
  const [categoria, setCategoria] = useState("");
  const [status, setStatus] = useState("todos");
  const [viewMode, setViewModeState] = useState<ViewMode>(loadViewMode);
  const [selectedTemaIds, setSelectedTemaIds] = useState<Set<number>>(new Set());
  const [selectedCharacterIds, setSelectedCharacterIds] = useState<Set<number>>(new Set());
  const [linkingCharacter, setLinkingCharacter] = useState<CatalogCharacterSummary | null>(null);

  const query = useAdminCatalogo({ q, categoria, status });
  const toggleActive = useToggleCatalogItemActive();
  const deleteItem = useDeleteCatalogItem();
  const toggleCharacterActive = useUpdateCharacterActiveStandalone();
  const deleteCharacter = useDeleteCharacterStandalone();
  const moveCharacters = useMoveCharactersBulk();
  const linkCharacter = useLinkCharacterFigurino();
  const [linkTargetSheetId, setLinkTargetSheetId] = useState<number | null>(null);

  function setViewMode(mode: ViewMode) {
    setViewModeState(mode);
    window.localStorage.setItem(VIEW_MODE_KEY, mode);
    setSelectedTemaIds(new Set());
    setSelectedCharacterIds(new Set());
  }

  function toggleTemaSelect(id: number) {
    setSelectedTemaIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleCharacterSelect(id: number) {
    setSelectedCharacterIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkDeactivateTemas() {
    if (!window.confirm(`Inativar ${selectedTemaIds.size} produto(s)?`)) return;
    await Promise.all([...selectedTemaIds].map((id) => toggleActive.mutateAsync(id)));
    setSelectedTemaIds(new Set());
  }

  async function handleBulkDeleteTemas() {
    if (!window.confirm(`Excluir ${selectedTemaIds.size} produto(s) definitivamente? Personagens filhos também serão excluídos.`)) return;
    await Promise.all([...selectedTemaIds].map((id) => deleteItem.mutateAsync(id)));
    setSelectedTemaIds(new Set());
  }

  async function handleBulkDeactivateCharacters() {
    if (!window.confirm(`Inativar ${selectedCharacterIds.size} personagem(ns)?`)) return;
    await Promise.all(
      [...selectedCharacterIds].map((id) => toggleCharacterActive.mutateAsync({ id, isActive: false })),
    );
    setSelectedCharacterIds(new Set());
  }

  async function handleBulkDeleteCharacters() {
    if (!window.confirm(`Excluir ${selectedCharacterIds.size} personagem(ns) definitivamente?`)) return;
    await Promise.all([...selectedCharacterIds].map((id) => deleteCharacter.mutateAsync(id)));
    setSelectedCharacterIds(new Set());
  }

  async function handleBulkMove(targetItemId: number) {
    await moveCharacters.mutateAsync({ characterIds: [...selectedCharacterIds], targetItemId });
    setSelectedCharacterIds(new Set());
  }

  const items: CatalogListItem[] = query.data?.items ?? [];

  // Termômetro de cobertura de fichas (feature 209): soma sobre o recorte filtrado atual.
  const fichaTotais = items.reduce(
    (acc, item) => {
      acc.personagens += item.characters_total;
      acc.comFicha += item.characters_com_ficha;
      return acc;
    },
    { personagens: 0, comFicha: 0 },
  );

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 pb-24 sm:p-6">
      <PageHeader
        title="Catálogo"
        className="mb-0"
        actions={
          <Button asChild size="sm">
            <Link to="/admin/catalogo/novo">+ Novo produto</Link>
          </Button>
        }
      />

      <div className="flex items-center gap-1 rounded-md border border-line bg-surface-2 p-1 text-sm">
        <button
          type="button"
          onClick={() => setViewMode("cards")}
          className={`rounded px-3 py-1.5 font-medium ${viewMode === "cards" ? "bg-panel text-ink shadow-sm" : "text-muted"}`}
        >
          🗂️ Cards
        </button>
        <button
          type="button"
          onClick={() => setViewMode("tree")}
          className={`rounded px-3 py-1.5 font-medium ${viewMode === "tree" ? "bg-panel text-ink shadow-sm" : "text-muted"}`}
        >
          🌳 Árvore
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          className="h-9 min-w-56 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink sm:max-w-md"
          placeholder="Buscar por nome…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {query.data && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
          >
            <option value="">Todas as categorias</option>
            {query.data.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        <select
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="todos">Todos os status</option>
          <option value="ativo">Ativos</option>
          <option value="inativo">Inativos</option>
        </select>
      </div>

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o catálogo.
        </div>
      )}

      {query.data && items.length === 0 && (
        <p className="text-sm text-muted">Nenhum produto encontrado.</p>
      )}

      {query.data && fichaTotais.personagens > 0 && (
        <p className="text-sm text-muted">
          👗 Fichas de figurino do elenco:{" "}
          <span className="font-semibold text-ink">
            {fichaTotais.comFicha} de {fichaTotais.personagens}
          </span>{" "}
          personagens com ficha vinculada
          {fichaTotais.comFicha < fichaTotais.personagens &&
            ` — faltam ${fichaTotais.personagens - fichaTotais.comFicha}`}
          .
        </p>
      )}

      {items.length > 0 && viewMode === "cards" && (
        <CatalogCardGrid
          items={items}
          selectedIds={selectedTemaIds}
          onToggleSelect={toggleTemaSelect}
          onToggleActive={(item) => toggleActive.mutate(item.id)}
          onDelete={(item) => {
            if (window.confirm(`Excluir "${item.name}" definitivamente?`)) {
              deleteItem.mutate(item.id);
            }
          }}
        />
      )}

      {items.length > 0 && viewMode === "tree" && (
        <CatalogTreeView
          items={items}
          selectedCharacterIds={selectedCharacterIds}
          onToggleCharacterSelect={toggleCharacterSelect}
          onToggleCharacterActive={(character) =>
            toggleCharacterActive.mutate({ id: character.id, isActive: !character.is_active })
          }
          onDeleteCharacter={(character) => {
            if (window.confirm(`Excluir "${character.name}" definitivamente?`)) {
              deleteCharacter.mutate(character.id);
            }
          }}
          onQuickLinkCharacter={setLinkingCharacter}
        />
      )}

      <CatalogBulkActionBar
        count={viewMode === "cards" ? selectedTemaIds.size : selectedCharacterIds.size}
        kind={viewMode === "cards" ? "tema" : "character"}
        temaOptions={items}
        onMove={viewMode === "tree" ? handleBulkMove : undefined}
        moving={moveCharacters.isPending}
        onDeactivate={viewMode === "cards" ? handleBulkDeactivateTemas : handleBulkDeactivateCharacters}
        deactivating={toggleActive.isPending || toggleCharacterActive.isPending}
        onDelete={viewMode === "cards" ? handleBulkDeleteTemas : handleBulkDeleteCharacters}
        deleting={deleteItem.isPending || deleteCharacter.isPending}
        onClearSelection={() => {
          setSelectedTemaIds(new Set());
          setSelectedCharacterIds(new Set());
        }}
      />

      <Modal
        open={linkingCharacter !== null}
        onClose={() => {
          setLinkingCharacter(null);
          setLinkTargetSheetId(null);
        }}
        title={`Vincular "${linkingCharacter?.name ?? ""}" a uma Ficha de Figurino`}
      >
        <div className="space-y-3">
          <FigurinoSheetPicker
            value={linkTargetSheetId}
            characterName={linkingCharacter?.name}
            onChange={setLinkTargetSheetId}
            ariaLabel="Buscar figurino"
          />
          <Button
            loading={linkCharacter.isPending}
            disabled={linkTargetSheetId === null}
            onClick={() => {
              if (!linkingCharacter || linkTargetSheetId === null) return;
              linkCharacter.mutate(
                { characterId: linkingCharacter.id, figurinoSheetId: linkTargetSheetId },
                {
                  onSuccess: () => {
                    setLinkingCharacter(null);
                    setLinkTargetSheetId(null);
                  },
                },
              );
            }}
          >
            Confirmar
          </Button>
        </div>
      </Modal>
    </div>
  );
}
