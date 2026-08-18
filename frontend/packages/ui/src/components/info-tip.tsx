import {
  useEffect,
  useId,
  useRef,
  useState,
  type FocusEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "../lib/cn";

export interface InfoTipProps {
  /** Conteúdo da dica exibido no painel. */
  content: ReactNode;
  /** Assunto da dica — entra no rótulo acessível do gatilho (ex.: "Sonorização"). */
  label?: string;
  /** Desliga o gatilho (ex.: enquanto os textos ainda estão carregando). */
  disabled?: boolean;
  /** Alinhamento do painel em relação ao gatilho. */
  align?: "left" | "right";
  className?: string;
}

/**
 * Dica de informação (ⓘ) acessível — abre no hover do mouse, no clique/toque e no foco por
 * teclado; fecha no Escape, ao sair do foco e ao clicar fora. Substitui o atributo `title`
 * nativo, que só respondia a mouse parado e nunca aparecia no toque nem no teclado.
 *
 * Sem dependência nova de overlay: mesma implementação enxuta do `FilterDropdown`.
 */
export function InfoTip({ content, label, disabled = false, align = "left", className }: InfoTipProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLSpanElement>(null);
  const panelId = useId();
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  // No toque, o navegador dispara pointerenter logo antes do clique — abrir no hover ali
  // faria o clique fechar a dica recém-aberta. Por isso o hover só vale para mouse.
  function handlePointerEnter(e: PointerEvent<HTMLSpanElement>) {
    if (!disabled && e.pointerType === "mouse") setOpen(true);
  }

  function handlePointerLeave(e: PointerEvent<HTMLSpanElement>) {
    if (e.pointerType === "mouse") setOpen(false);
  }

  function handleBlur(e: FocusEvent<HTMLSpanElement>) {
    const proximo = e.relatedTarget as Node | null;
    if (!proximo || !rootRef.current?.contains(proximo)) setOpen(false);
  }

  return (
    <span
      ref={rootRef}
      className={cn("relative inline-flex", className)}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
      onBlur={handleBlur}
    >
      <button
        type="button"
        disabled={disabled}
        aria-label={label ? `Dica sobre ${label}` : "Mais informações"}
        aria-expanded={open}
        aria-describedby={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => {
          if (!disabled) setOpen(true);
        }}
        className={cn(
          // Área de toque de 24px mesmo com o glifo pequeno (WCAG 2.2 — alvo mínimo).
          "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs leading-none transition-colors",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue",
          disabled ? "cursor-default text-muted/50" : "cursor-help text-muted hover:text-ink",
        )}
      >
        <span aria-hidden="true">ⓘ</span>
      </button>
      <AnimatePresence>
        {open && !disabled && (
          <motion.span
            id={panelId}
            role="tooltip"
            initial={reduceMotion ? undefined : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className={cn(
              "absolute top-full z-50 mt-1 block w-max max-w-xs whitespace-normal break-words",
              "rounded-md border border-line bg-panel px-3 py-2 text-xs font-normal leading-relaxed text-ink shadow-lg",
              align === "right" ? "right-0" : "left-0",
            )}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
