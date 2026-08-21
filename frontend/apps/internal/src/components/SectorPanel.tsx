import { useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Card } from "@manto/ui";

export interface SectorPanelProps {
  title: string;
  count: number;
  /** Subconjunto de `count` que precisa de ação imediata — vira selo vermelho no cabeçalho. */
  urgentCount?: number;
  children: ReactNode;
  defaultOpen?: boolean;
  /** Modo controlado (Home): o pai decide o estado para poder abrir via card da visão geral. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/** Painel colapsável por setor (Casting/Figurino/Comercial/Recorrentes) — paridade com o
 * `.sector-panel`/`toggleSector()` do Jinja clássico; estado local, sem persistência. */
export function SectorPanel({
  title,
  count,
  urgentCount = 0,
  children,
  defaultOpen = true,
  open: controlledOpen,
  onOpenChange,
}: SectorPanelProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const open = controlledOpen ?? internalOpen;
  const reduceMotion = useReducedMotion();

  const toggle = () => {
    const next = !open;
    setInternalOpen(next);
    onOpenChange?.(next);
  };

  return (
    <Card className="overflow-hidden">
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-surface-2"
        aria-expanded={open}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">{title}</span>
          {count > 0 ? (
            <span className="text-xs text-muted">
              {count} pendente{count !== 1 ? "s" : ""}
            </span>
          ) : (
            <span className="rounded-full bg-green-soft px-2 py-0.5 text-xs font-medium text-green">
              Tudo em dia ✓
            </span>
          )}
          {urgentCount > 0 && (
            <span className="rounded-full bg-red-soft px-2 py-0.5 text-xs font-medium text-red">
              {urgentCount} urgente{urgentCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <span
          className={`text-xs text-muted transition-transform duration-200 ${open ? "" : "-rotate-90"}`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-line px-4 py-2">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

export interface Urgency {
  label: string;
  tone: "red" | "neutral";
  /** Tinta suave de fundo da linha — paridade com `.task-row` do Jinja clássico. */
  rowBackground: string;
}

/**
 * Urgência a partir de `start_at` — paridade com `home.html`: tag vermelha "URGENTE"
 * ≤2 dias (fundo vermelho-suave), badge cinza "Nd" ≤7 dias (fundo creme/dourado-suave).
 */
export function getUrgency(startAt: string | null): Urgency | null {
  if (!startAt) return null;
  const days = Math.floor((new Date(startAt).getTime() - Date.now()) / 86_400_000);
  if (days <= 2) return { label: "URGENTE", tone: "red", rowBackground: "rgba(228,88,88,0.06)" };
  if (days <= 7) return { label: `${days}d`, tone: "neutral", rowBackground: "rgba(245,200,66,0.06)" };
  return null;
}
