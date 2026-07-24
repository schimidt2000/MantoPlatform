import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button } from "@manto/ui";
import { Modal } from "./Modal";
import type { CatalogListItem } from "../lib/adminCatalogo";

interface CatalogBulkActionBarProps {
  count: number;
  /** "character": mostra a ação Mover (Personagens têm um Tema pai a que se realocar); "tema"
   * não mostra Mover (um Tema não tem pai neste modelo de dados — research.md, feature 186). */
  kind: "tema" | "character";
  /** Temas disponíveis como destino de "Mover para…" (só usado quando `kind === "character"`). */
  temaOptions?: CatalogListItem[];
  onMove?: (targetItemId: number) => void;
  moving?: boolean;
  onDeactivate: () => void;
  deactivating?: boolean;
  onDelete: () => void;
  deleting?: boolean;
  onClearSelection: () => void;
}

/**
 * Barra flutuante de ações em massa (feature 186, US4/FR-012) — aparece quando há 1+ itens
 * selecionados, some ao voltar a 0.
 */
export function CatalogBulkActionBar({
  count,
  kind,
  temaOptions = [],
  onMove,
  moving = false,
  onDeactivate,
  deactivating = false,
  onDelete,
  deleting = false,
  onClearSelection,
}: CatalogBulkActionBarProps) {
  const shouldReduceMotion = useReducedMotion();
  const [moveModalOpen, setMoveModalOpen] = useState(false);
  const [targetItemId, setTargetItemId] = useState<string>("");

  return (
    <>
      <AnimatePresence>
        {count > 0 && (
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0, y: 20 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.2, ease: "easeOut" }}
            className="fixed inset-x-0 bottom-4 z-40 mx-auto flex w-fit max-w-[95vw] flex-wrap items-center gap-2 rounded-full border border-line bg-panel px-4 py-2.5 shadow-xl"
          >
            <span className="text-sm font-medium text-ink">
              {count} selecionado{count === 1 ? "" : "s"}
            </span>
            {kind === "character" && onMove && (
              <Button variant="outline" size="sm" onClick={() => setMoveModalOpen(true)}>
                📁 Mover para…
              </Button>
            )}
            <Button variant="outline" size="sm" loading={deactivating} onClick={onDeactivate}>
              🚫 Inativar selecionados
            </Button>
            <Button variant="outline" size="sm" loading={deleting} onClick={onDelete}>
              🗑️ Excluir selecionados
            </Button>
            <Button variant="ghost" size="sm" onClick={onClearSelection}>
              Cancelar
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      <Modal
        open={moveModalOpen}
        onClose={() => setMoveModalOpen(false)}
        title={`Mover ${count} personagem${count === 1 ? "" : "ns"} para…`}
      >
        <div className="space-y-3">
          <select
            className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={targetItemId}
            onChange={(e) => setTargetItemId(e.target.value)}
            aria-label="Tema de destino"
          >
            <option value="">Selecione o Tema de destino…</option>
            {temaOptions.map((tema) => (
              <option key={tema.id} value={tema.id}>
                {tema.name}
              </option>
            ))}
          </select>
          <Button
            loading={moving}
            disabled={!targetItemId}
            onClick={() => {
              if (!targetItemId || !onMove) return;
              onMove(Number(targetItemId));
              setMoveModalOpen(false);
              setTargetItemId("");
            }}
          >
            Confirmar
          </Button>
        </div>
      </Modal>
    </>
  );
}
