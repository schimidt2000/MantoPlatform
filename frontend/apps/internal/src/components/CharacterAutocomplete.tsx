import { useMemo, useState } from "react";
import { assetUrl } from "@manto/api-client";
import type { CatalogElencoTema, CatalogElencoCharacter } from "../lib/catalogoElenco";

export interface CharacterSelection {
  temaId: number;
  temaName: string;
  character: CatalogElencoCharacter;
}

interface CharacterAutocompleteProps {
  temas: CatalogElencoTema[];
  onSelect: (selection: CharacterSelection) => void;
  placeholder?: string;
  /** Também mostra uma opção "Tema completo (pacote)" por Tema — usado no elenco de eventos. */
  includeTemaOption?: boolean;
  /** Personagens listados mas NÃO selecionáveis (ex.: já vinculados a outra ficha) — aparecem
   * apagados com a `disabledNote` ao lado. Melhor do que escondê-los: quem procura "Homem-Aranha"
   * entende por que não pode escolher, em vez de achar que o personagem sumiu do catálogo. */
  disabledCharacterIds?: ReadonlySet<number>;
  disabledNote?: string;
}

interface FlatOption {
  key: string;
  temaId: number;
  temaName: string;
  character: CatalogElencoCharacter | null;
  label: string;
  photoUrl: string | null;
  disabled: boolean;
}

/**
 * Busca com auto-complete visual (feature 186, US1/US2): mostra a foto em miniatura de cada
 * Personagem ao lado do nome E o produto de onde ele vem (feature 254 — cinco "Homem-Aranha"
 * idênticos na lista, um por produto, eram indistinguíveis). Restrita a Personagens Filhos
 * (nunca o Tema pai isolado, a menos que `includeTemaOption` peça a opção de pacote completo).
 */
export function CharacterAutocomplete({
  temas,
  onSelect,
  placeholder = "Buscar personagem…",
  includeTemaOption = false,
  disabledCharacterIds,
  disabledNote = "indisponível",
}: CharacterAutocompleteProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const options = useMemo<FlatOption[]>(() => {
    const flat: FlatOption[] = [];
    for (const tema of temas) {
      if (includeTemaOption) {
        flat.push({
          key: `tema-${tema.id}`,
          temaId: tema.id,
          temaName: tema.name,
          character: null,
          label: `${tema.name} (pacote completo)`,
          photoUrl: null,
          disabled: false,
        });
      }
      for (const character of tema.characters) {
        flat.push({
          key: `character-${character.id}`,
          temaId: tema.id,
          temaName: tema.name,
          character,
          label: character.name,
          photoUrl: character.photo_url,
          disabled: disabledCharacterIds?.has(character.id) ?? false,
        });
      }
    }
    return flat;
  }, [temas, includeTemaOption, disabledCharacterIds]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return options.slice(0, 20);
    // O produto entra na busca: "aranha aventura" acha o Homem-Aranha do produto Aventura.
    return options
      .filter((o) => `${o.label} ${o.temaName}`.toLowerCase().includes(term))
      .slice(0, 20);
  }, [options, query]);

  function handleSelect(option: FlatOption) {
    if (option.character) {
      onSelect({ temaId: option.temaId, temaName: option.temaName, character: option.character });
    } else {
      // Opção "Tema completo" — sem Personagem, quem consome decide como tratar (ex.: prefill só
      // do nome do Tema, sem figurino).
      onSelect({
        temaId: option.temaId,
        temaName: option.temaName,
        character: { id: -1, name: option.temaName, figurino_sheet_id: null, photo_url: null },
      });
    }
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="relative">
      <input
        className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          setTimeout(() => setOpen(false), 150);
        }}
      />
      {open && (
        <ul className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-line bg-panel py-1 shadow-md">
          {filtered.length === 0 && (
            <li className="px-3 py-2 text-sm text-muted">Nenhum personagem encontrado.</li>
          )}
          {filtered.map((option) => (
            <li key={option.key}>
              <button
                type="button"
                disabled={option.disabled}
                className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm ${
                  option.disabled
                    ? "cursor-not-allowed text-muted opacity-60"
                    : "text-ink hover:bg-accent-soft"
                }`}
                onMouseDown={(e) => {
                  // preventDefault evita o onBlur do input fechar a lista antes do clique registrar
                  e.preventDefault();
                  if (!option.disabled) handleSelect(option);
                }}
              >
                <span className="flex h-8 w-8 flex-none items-center justify-center overflow-hidden rounded-full bg-surface-2">
                  {option.photoUrl ? (
                    <img
                      src={assetUrl(option.photoUrl)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="text-sm">🎭</span>
                  )}
                </span>
                <span className="min-w-0 flex-1 truncate">
                  {option.label}
                  {option.character && (
                    <span className="text-muted"> — {option.temaName}</span>
                  )}
                </span>
                {option.disabled && (
                  <span className="flex-none text-xs text-muted">{disabledNote}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
