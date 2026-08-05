import { useMemo, useRef, useState } from "react";
import { assetUrl } from "@manto/api-client";
import { useFigurinoSheets, type FigurinoSheetItem } from "../lib/figurino";

/** Remove acentos e baixa a caixa — mesmo espírito do `strip_accents_lower` do backend. */
function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export interface FigurinoSheetPickerProps {
  /** Ficha atualmente vinculada (null = sem vínculo). */
  value: number | null;
  onChange: (sheetId: number | null) => void;
  /**
   * Nome do personagem — fichas cujo nome bate sobem para o topo da lista
   * (mesmo match por nome normalizado que a impressão de fichas usa).
   */
  characterName?: string;
  disabled?: boolean;
  ariaLabel?: string;
}

const MAX_RESULTS = 30;

/**
 * Busca visual de ficha de figurino (feature 209): digita → filtra em tempo real, cada
 * resultado com a thumb da ficha (598 das 600 têm foto). Substitui o `<select>` cego do
 * painel de personagens — a escolha de ficha é visual por natureza.
 */
export function FigurinoSheetPicker({
  value,
  onChange,
  characterName,
  disabled = false,
  ariaLabel,
}: FigurinoSheetPickerProps) {
  const sheetsQuery = useFigurinoSheets();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const blurTimer = useRef<number | null>(null);

  const sheets = sheetsQuery.data?.items ?? [];
  const selected = value != null ? sheets.find((s) => s.id === value) : undefined;

  const results = useMemo(() => {
    const term = normalize(query.trim());
    const charNorm = normalize((characterName ?? "").trim());
    const matches = term
      ? sheets.filter((s) => normalize(s.character_name).includes(term))
      : sheets;
    // Sugestões primeiro: ficha com nome batendo com o personagem; depois ordem alfabética.
    return [...matches]
      .sort((a, b) => {
        if (charNorm) {
          const aHit = normalize(a.character_name).includes(charNorm) ? 0 : 1;
          const bHit = normalize(b.character_name).includes(charNorm) ? 0 : 1;
          if (aHit !== bHit) return aHit - bHit;
        }
        return a.character_name.localeCompare(b.character_name, "pt-BR");
      })
      .slice(0, MAX_RESULTS);
  }, [sheets, query, characterName]);

  function pick(sheet: FigurinoSheetItem | null) {
    onChange(sheet ? sheet.id : null);
    setQuery("");
    setOpen(false);
  }

  if (selected) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-line bg-panel p-1.5">
        <span className="h-9 w-9 flex-none overflow-hidden rounded bg-surface-2">
          {selected.photo_url && (
            <img src={assetUrl(selected.photo_url)} alt="" className="h-full w-full object-cover" />
          )}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-ink">{selected.character_name}</span>
        {!disabled && (
          <button
            type="button"
            className="flex-none rounded px-1.5 py-0.5 text-xs text-muted hover:bg-surface-2 hover:text-red"
            aria-label="Desvincular ficha"
            onClick={() => pick(null)}
          >
            ✕
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <input
        type="search"
        className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="Buscar ficha pelo nome…"
        aria-label={ariaLabel ?? "Buscar ficha de figurino"}
        value={query}
        disabled={disabled || sheetsQuery.isLoading}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          // Fecha depois do click no resultado (mousedown do item cancela via preventDefault).
          blurTimer.current = window.setTimeout(() => setOpen(false), 150);
        }}
      />
      {open && results.length > 0 && (
        <ul
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-line bg-panel shadow-md"
          role="listbox"
        >
          {results.map((sheet) => (
            <li key={sheet.id}>
              <button
                type="button"
                role="option"
                aria-selected={false}
                className="flex w-full items-center gap-2 px-2 py-1.5 text-left hover:bg-surface-2"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(sheet)}
              >
                <span className="h-10 w-10 flex-none overflow-hidden rounded bg-surface-2">
                  {sheet.photo_url ? (
                    <img
                      src={assetUrl(sheet.photo_url)}
                      alt=""
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="flex h-full w-full items-center justify-center text-sm">👗</span>
                  )}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm text-ink">
                  {sheet.character_name}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && query.trim() && results.length === 0 && !sheetsQuery.isLoading && (
        <p className="absolute z-20 mt-1 w-full rounded-md border border-line bg-panel p-2 text-xs text-muted shadow-md">
          Nenhuma ficha encontrada para “{query}”.
        </p>
      )}
    </div>
  );
}
