import { useEffect, useId, useRef, useState } from "react";
import { MoreVertical } from "lucide-react";

export interface KebabMenuItem {
  label: string;
  onClick: () => void;
  /** Estilo de alerta (ex.: Excluir) — mesmo padrão de cor usado no resto do app (Princípio V). */
  destructive?: boolean;
}

interface KebabMenuProps {
  items: KebabMenuItem[];
  label?: string;
}

/**
 * Menu de 3 pontos genérico (feature 186, US4) — não existe `DropdownMenu` em `@manto/ui` ainda;
 * implementação enxuta própria, no mesmo espírito de `FilterDropdown` já existente
 * (research.md §7). Fecha ao clicar fora ou Esc.
 */
export function KebabMenu({ items, label = "Mais ações" }: KebabMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    function handleClick(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((o) => !o)}
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-ink"
      >
        <MoreVertical className="h-4 w-4" aria-hidden="true" />
      </button>
      {open && (
        <ul
          id={menuId}
          role="menu"
          className="absolute right-0 z-20 mt-1 min-w-[10rem] rounded-md border border-line bg-panel py-1 shadow-md"
        >
          {items.map((item) => (
            <li key={item.label} role="none">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  item.onClick();
                }}
                className={`block w-full px-3 py-2 text-left text-sm hover:bg-surface-2 ${
                  item.destructive ? "text-red" : "text-ink"
                }`}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
