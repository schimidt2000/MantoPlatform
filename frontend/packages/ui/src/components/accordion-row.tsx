import { useId, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "../lib/cn";

export interface AccordionRowProps {
  /** Conteúdo sempre visível — tipicamente uma linha de tabela/resumo clicável. Não deve
   * conter elementos interativos (botões, links) — use `actions` para isso, já que `summary`
   * é renderizado dentro do `<button>` de expandir/recolher (HTML inválido teria `<button>`
   * dentro de `<button>`). */
  summary: ReactNode;
  /** Ações interativas (ex.: botão "Pagar Mês") — renderizadas ao lado do botão de
   * expandir/recolher, nunca dentro dele. */
  actions?: ReactNode;
  /** Conteúdo revelado ao expandir. */
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  defaultOpen?: boolean;
}

/**
 * Linha expansível (feature 187) — usada na visão "Resumo por Vendedor" para revelar os
 * eventos individuais por trás do total de um vendedor. Altura animada via Framer Motion,
 * respeitando `useReducedMotion()` (Princípio IX). Sem dependência de overlay/portal — é uma
 * expansão inline, não um popover flutuante, então não precisa de `@radix-ui/react-*` (a
 * mesma lógica de "implementação própria enxuta quando não há overlay" já usada em
 * `FilterDropdown`).
 */
export function AccordionRow({
  summary,
  actions,
  children,
  className,
  contentClassName,
  defaultOpen = false,
}: AccordionRowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("border-b border-line last:border-0", className)}>
      <div className="flex w-full items-center gap-2">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 items-center gap-2 text-left"
        >
          <ChevronDown
            className={cn("h-4 w-4 shrink-0 text-muted transition-transform", open && "rotate-180")}
            aria-hidden="true"
          />
          <div className="flex-1">{summary}</div>
        </button>
        {actions && (
          <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={contentId}
            initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className={cn("pb-3 pl-6", contentClassName)}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
