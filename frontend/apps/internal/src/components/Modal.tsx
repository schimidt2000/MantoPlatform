import { useEffect, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  /** Largura máxima do painel (Tailwind `max-w-*`). */
  maxWidth?: string;
}

/**
 * Modal/Dialog centralizado — não existe um componente equivalente em `@manto/ui` ainda
 * (feature 179). Overlay + painel seguem o mesmo padrão de Framer Motion do drawer mobile de
 * `@manto/ui`'s `AppLayout` (opacity/scale, respeita `useReducedMotion()`).
 */
export function Modal({ open, onClose, title, children, maxWidth = "max-w-lg" }: ModalProps) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.2 }}
            className="fixed inset-0 bg-black/50"
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={typeof title === "string" ? title : undefined}
            initial={{ opacity: 0, scale: reduceMotion ? 1 : 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: reduceMotion ? 1 : 0.96 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: "easeOut" }}
            className={`relative z-10 max-h-[90vh] w-full ${maxWidth} overflow-y-auto rounded-lg border border-line bg-panel shadow-xl`}
          >
            <div className="sticky top-0 flex items-center justify-between gap-3 border-b border-line bg-panel px-5 py-4">
              <h2 className="text-base font-semibold text-ink">{title}</h2>
              <button
                type="button"
                onClick={onClose}
                aria-label="Fechar"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-ink"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <div className="p-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
