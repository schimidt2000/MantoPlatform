import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ChevronRight } from "lucide-react";
import { assetUrl } from "@manto/api-client";
import { KebabMenu } from "./KebabMenu";
import type { CatalogCharacterSummary, CatalogListItem } from "../lib/adminCatalogo";

interface CatalogTreeViewProps {
  items: CatalogListItem[];
  selectedCharacterIds: Set<number>;
  onToggleCharacterSelect: (id: number) => void;
  onToggleCharacterActive: (character: CatalogCharacterSummary) => void;
  onDeleteCharacter: (character: CatalogCharacterSummary) => void;
  onQuickLinkCharacter: (character: CatalogCharacterSummary) => void;
}

/** Uma linha de Personagem filho, recuada com guia de hierarquia (feature 186, US3/FR-008). */
function CharacterRow({
  character,
  selected,
  onToggleSelect,
  onToggleActive,
  onDelete,
  onQuickLink,
}: {
  character: CatalogCharacterSummary;
  selected: boolean;
  onToggleSelect: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
  onQuickLink: () => void;
}) {
  return (
    <li className="relative flex items-center gap-2.5 py-1.5 pl-8">
      <span className="absolute left-3 top-0 h-full w-px bg-line" aria-hidden="true" />
      <span className="absolute left-3 top-1/2 h-px w-4 bg-line" aria-hidden="true" />
      <input
        type="checkbox"
        className="h-4 w-4 flex-none"
        checked={selected}
        onChange={onToggleSelect}
        aria-label={`Selecionar ${character.name}`}
      />
      <div className="h-8 w-8 flex-none overflow-hidden rounded-full bg-surface-2">
        {character.photo_url ? (
          <img src={assetUrl(character.photo_url)} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-sm">🎭</span>
        )}
      </div>
      <span className="min-w-0 flex-1 truncate text-sm text-ink">{character.name}</span>
      {character.figurino_sheet_id ? (
        <span className="rounded-full bg-green-soft px-2 py-0.5 text-[11px] font-medium text-green">
          ✓ figurino
        </span>
      ) : (
        <button
          type="button"
          onClick={onQuickLink}
          className="rounded-full bg-red-soft px-2 py-0.5 text-[11px] font-medium text-red hover:opacity-80"
        >
          ⚠ Sem ficha — + Vincular
        </button>
      )}
      {!character.is_active && (
        <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[11px] text-muted">inativo</span>
      )}
      <KebabMenu
        label={`Mais ações para ${character.name}`}
        items={[
          { label: character.is_active ? "Inativar" : "Ativar", onClick: onToggleActive },
          { label: "Excluir", onClick: onDelete, destructive: true },
        ]}
      />
    </li>
  );
}

/**
 * Modo Árvore do gerenciador (feature 186, US3) — cada Tema expansível revela seus Personagens
 * filhos recuados com guia visual, foto, nome, status do vínculo de figurino e ações rápidas.
 */
export function CatalogTreeView({
  items,
  selectedCharacterIds,
  onToggleCharacterSelect,
  onToggleCharacterActive,
  onDeleteCharacter,
  onQuickLinkCharacter,
}: CatalogTreeViewProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const shouldReduceMotion = useReducedMotion();

  function toggleExpanded(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const isExpanded = expanded.has(item.id);
        const hasChildren = item.characters.length > 0;
        return (
          <li key={item.id} className="rounded-md border border-line bg-panel">
            <div className="flex items-center gap-2.5 p-2.5">
              <button
                type="button"
                onClick={() => toggleExpanded(item.id)}
                disabled={!hasChildren}
                aria-label={isExpanded ? `Recolher ${item.name}` : `Expandir ${item.name}`}
                aria-expanded={isExpanded}
                className="flex h-6 w-6 flex-none items-center justify-center text-muted disabled:opacity-20"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
              <div className="h-10 w-10 flex-none overflow-hidden rounded-md bg-surface-2">
                {item.cover_url && (
                  <img src={assetUrl(item.cover_url)} alt="" className="h-full w-full object-cover" />
                )}
              </div>
              <Link
                to={`/admin/catalogo/${item.id}/editar`}
                className="min-w-0 flex-1 truncate text-sm font-medium text-ink hover:underline"
              >
                {item.name}
              </Link>
              <span className="text-xs text-muted">
                {item.characters.length} personagem{item.characters.length === 1 ? "" : "ns"}
              </span>
              {!item.is_active && (
                <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">inativo</span>
              )}
            </div>
            <AnimatePresence initial={false}>
              {isExpanded && hasChildren && (
                <motion.div
                  initial={shouldReduceMotion ? false : { height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={shouldReduceMotion ? undefined : { height: 0, opacity: 0 }}
                  transition={{ duration: shouldReduceMotion ? 0 : 0.22, ease: "easeOut" }}
                  className="overflow-hidden"
                >
                  <ul className="pb-2">
                    {item.characters.map((character) => (
                      <CharacterRow
                        key={character.id}
                        character={character}
                        selected={selectedCharacterIds.has(character.id)}
                        onToggleSelect={() => onToggleCharacterSelect(character.id)}
                        onToggleActive={() => onToggleCharacterActive(character)}
                        onDelete={() => onDeleteCharacter(character)}
                        onQuickLink={() => onQuickLinkCharacter(character)}
                      />
                    ))}
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </li>
        );
      })}
    </ul>
  );
}
