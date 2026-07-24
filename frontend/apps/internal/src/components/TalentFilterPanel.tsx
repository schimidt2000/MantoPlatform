import { useState } from "react";
import { Button, CheckboxList, FilterDropdown } from "@manto/ui";
import { useCharacterSuggestions, type TalentFilterOptions } from "../lib/talents";

export interface TalentAdvancedFilters {
  language: string[];
  race: string[];
  top: string[];
  bottom: string[];
  shoe: string[];
  passport: string[];
  tag: string[];
  character: string;
  heightOp: "gte" | "lte" | "eq";
  heightValue: string;
  jaTrabalhou: boolean;
}

export const EMPTY_ADVANCED_FILTERS: TalentAdvancedFilters = {
  language: [],
  race: [],
  top: [],
  bottom: [],
  shoe: [],
  passport: [],
  tag: [],
  character: "",
  heightOp: "gte",
  heightValue: "",
  jaTrabalhou: false,
};

/** Categorização IBGE, mesma referência usada no cadastro original do talento (feature 180). */
const RACE_OPTIONS = [
  { value: "amarela", label: "Amarela" },
  { value: "branca", label: "Branca" },
  { value: "indígena", label: "Indígena" },
  { value: "parda", label: "Parda" },
  { value: "preta", label: "Preta" },
];

function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function countActive(f: TalentAdvancedFilters): number {
  return (
    f.language.length +
    f.race.length +
    f.top.length +
    f.bottom.length +
    f.shoe.length +
    f.passport.length +
    f.tag.length +
    (f.character ? 1 : 0) +
    (f.heightValue ? 1 : 0) +
    (f.jaTrabalhou ? 1 : 0)
  );
}

function CharacterFilterDropdown({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const suggestions = useCharacterSuggestions(value);
  return (
    <FilterDropdown label="Personagem" count={value ? 1 : 0}>
      <div className="space-y-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="ex: Thor, Homem-Aranha, Mario…"
          className="h-8 w-full rounded-md border border-line bg-panel px-2 text-xs text-ink"
          aria-label="Filtrar por personagem"
        />
        {value.trim().length >= 2 && (
          <ul className="space-y-0.5">
            {(suggestions.data ?? []).map((s) => (
              <li key={s.name}>
                <button
                  type="button"
                  onClick={() => onChange(s.name)}
                  className="flex w-full items-center justify-between rounded px-1 py-0.5 text-left text-sm text-ink hover:bg-surface-2"
                >
                  <span>{s.name}</span>
                  <span className="text-xs text-muted">{s.count}</span>
                </button>
              </li>
            ))}
            {suggestions.isFetched && suggestions.data?.length === 0 && (
              <li className="px-1 py-0.5 text-xs text-muted">Nenhum personagem encontrado.</li>
            )}
          </ul>
        )}
      </div>
    </FilterDropdown>
  );
}

export interface TalentFilterPanelProps {
  filterOptions: TalentFilterOptions | undefined;
  applied: TalentAdvancedFilters;
  onApply: (filters: TalentAdvancedFilters) => void;
}

/**
 * Painel de filtros avançados do Banco de Talentos (feature 180) — fidelidade ao comportamento
 * do Jinja legado, com dropdowns por categoria e aplicação em lote via "Filtrar". O estado local
 * (`pending`) só chega ao resultado quando o usuário clica em "Filtrar" ou "Limpar filtros".
 */
export function TalentFilterPanel({ filterOptions, applied, onApply }: TalentFilterPanelProps) {
  const [pending, setPending] = useState<TalentAdvancedFilters>(applied);
  const activeCount = countActive(applied);
  const sizeOptions = (filterOptions?.sizes ?? []).map((s) => ({ value: s, label: s }));

  const set = <K extends keyof TalentAdvancedFilters>(key: K, value: TalentAdvancedFilters[K]) =>
    setPending((f) => ({ ...f, [key]: value }));

  const clear = () => {
    setPending(EMPTY_ADVANCED_FILTERS);
    onApply(EMPTY_ADVANCED_FILTERS);
  };

  if (!filterOptions) return null;

  return (
    <div className="space-y-3 rounded-lg border border-line bg-panel p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <CharacterFilterDropdown
          value={pending.character}
          onChange={(v) => set("character", v)}
        />
        <FilterDropdown label="Idioma" count={pending.language.length}>
          <CheckboxList
            options={filterOptions.languages.map((l) => ({ value: l, label: l }))}
            selected={pending.language}
            onToggle={(v) => set("language", toggleInList(pending.language, v))}
          />
        </FilterDropdown>
        <FilterDropdown label="Raça" count={pending.race.length}>
          <CheckboxList
            options={RACE_OPTIONS}
            selected={pending.race}
            onToggle={(v) => set("race", toggleInList(pending.race, v))}
          />
        </FilterDropdown>
        <FilterDropdown label="Tamanho" count={pending.top.length + pending.bottom.length}>
          <div className="space-y-3">
            <div>
              <p className="mb-1 text-xs font-medium text-muted">Parte de cima</p>
              <CheckboxList
                options={sizeOptions}
                selected={pending.top}
                onToggle={(v) => set("top", toggleInList(pending.top, v))}
              />
            </div>
            <div className="border-t border-line pt-2">
              <p className="mb-1 text-xs font-medium text-muted">Parte de baixo</p>
              <CheckboxList
                options={sizeOptions}
                selected={pending.bottom}
                onToggle={(v) => set("bottom", toggleInList(pending.bottom, v))}
              />
            </div>
          </div>
        </FilterDropdown>
        <FilterDropdown label="Calçado" count={pending.shoe.length}>
          <CheckboxList
            options={filterOptions.shoes.map((s) => ({ value: s, label: s }))}
            selected={pending.shoe}
            onToggle={(v) => set("shoe", toggleInList(pending.shoe, v))}
          />
        </FilterDropdown>
        <div className="flex h-9 items-center gap-1 rounded-md border border-line bg-panel px-2">
          <span className="text-xs font-medium text-muted">Altura</span>
          <select
            className="h-7 rounded border border-line bg-panel px-1 text-xs text-ink"
            value={pending.heightOp}
            onChange={(e) => set("heightOp", e.target.value as TalentAdvancedFilters["heightOp"])}
            aria-label="Operador de altura"
          >
            <option value="gte">≥</option>
            <option value="lte">≤</option>
            <option value="eq">=</option>
          </select>
          <input
            type="number"
            className="h-7 w-16 rounded border border-line bg-panel px-1 text-xs text-ink"
            placeholder="cm"
            value={pending.heightValue}
            onChange={(e) => set("heightValue", e.target.value)}
            aria-label="Altura em cm"
          />
        </div>
        <FilterDropdown label="Passaporte" count={pending.passport.length}>
          <CheckboxList
            options={filterOptions.passport.map(([value, label]) => ({ value, label }))}
            selected={pending.passport}
            onToggle={(v) => set("passport", toggleInList(pending.passport, v))}
          />
        </FilterDropdown>
        <FilterDropdown label="Tags" count={pending.tag.length}>
          <CheckboxList
            options={filterOptions.tags.map((t) => ({ value: t, label: t }))}
            selected={pending.tag}
            onToggle={(v) => set("tag", toggleInList(pending.tag, v))}
            searchable
            searchPlaceholder="Buscar tag…"
          />
        </FilterDropdown>
        <label className="flex h-9 items-center gap-1.5 rounded-md border border-line bg-panel px-3 text-sm text-ink">
          <input
            type="checkbox"
            checked={pending.jaTrabalhou}
            onChange={(e) => set("jaTrabalhou", e.target.checked)}
          />
          Já trabalhou com a Manto
        </label>
      </div>
      <div className="flex items-center gap-2 border-t border-line pt-3">
        <Button size="sm" onClick={() => onApply(pending)}>
          Filtrar
        </Button>
        {activeCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clear}>
            Limpar filtros ({activeCount})
          </Button>
        )}
      </div>
    </div>
  );
}
