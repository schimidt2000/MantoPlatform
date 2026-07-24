import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "../lib/cn";

export interface FilterDropdownProps {
  /** Rótulo do botão-gatilho (nome da categoria de filtro, ex.: "Raça"). */
  label: string;
  /** Quantidade de valores selecionados nessa categoria — exibida como badge no gatilho. */
  count?: number;
  /** Conteúdo do painel (tipicamente um ou mais `CheckboxList`). */
  children: ReactNode;
  /** Alinhamento do painel em relação ao gatilho. */
  align?: "left" | "right";
  className?: string;
}

/**
 * Popover de filtro reutilizável (feature 180) — botão-gatilho + painel ancorado, fecha ao
 * clicar fora ou Esc. Sem dependência de overlay nova (Radix Popover etc.) — implementação
 * própria enxuta, único padrão de dropdown de filtro do design system (ver research.md §6).
 */
export function FilterDropdown({ label, count = 0, children, align = "left", className }: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
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

  return (
    <div ref={rootRef} className={cn("relative inline-block", className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-9 items-center gap-1.5 rounded-md border px-3 text-sm transition-colors",
          count > 0
            ? "border-accent bg-accent-soft text-accent-dark"
            : "border-line bg-panel text-ink hover:bg-surface-2",
        )}
      >
        {label}
        {count > 0 && (
          <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-white">
            {count}
          </span>
        )}
        <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={panelId}
            role="dialog"
            initial={reduceMotion ? undefined : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={cn(
              "absolute z-20 mt-1.5 max-h-80 w-64 overflow-y-auto rounded-md border border-line bg-panel p-3 shadow-lg",
              align === "right" ? "right-0" : "left-0",
            )}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export interface CheckboxOption {
  value: string;
  label: string;
}

export interface CheckboxListProps {
  options: CheckboxOption[];
  selected: string[];
  onToggle: (value: string) => void;
  /** Campo de busca interna que restringe as opções exibidas (feature 180 — Personagem/Tags). */
  searchable?: boolean;
  searchPlaceholder?: string;
  emptyMessage?: string;
}

/** Lista de checkboxes com busca interna opcional — bloco reutilizado dentro de `FilterDropdown`. */
export function CheckboxList({
  options,
  selected,
  onToggle,
  searchable = false,
  searchPlaceholder = "Buscar…",
  emptyMessage = "Nenhuma opção encontrada.",
}: CheckboxListProps) {
  const [search, setSearch] = useState("");
  const filtered = searchable && search.trim()
    ? options.filter((o) => o.label.toLowerCase().includes(search.trim().toLowerCase()))
    : options;

  return (
    <div className="space-y-2">
      {searchable && (
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={searchPlaceholder}
          className="h-8 w-full rounded-md border border-line bg-panel px-2 text-xs text-ink"
          aria-label={searchPlaceholder}
        />
      )}
      {filtered.length === 0 ? (
        <p className="text-xs text-muted">{emptyMessage}</p>
      ) : (
        <ul className="space-y-1">
          {filtered.map((opt) => (
            <li key={opt.value}>
              <label className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm text-ink hover:bg-surface-2">
                <input
                  type="checkbox"
                  checked={selected.includes(opt.value)}
                  onChange={() => onToggle(opt.value)}
                  className="h-3.5 w-3.5 rounded border-line accent-accent"
                />
                {opt.label}
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
