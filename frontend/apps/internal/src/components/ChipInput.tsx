import { useMemo, useState } from "react";

interface ChipInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  /** Sugestões para autocomplete (ex.: tags já usadas em outros produtos). */
  suggestions?: string[];
  placeholder?: string;
  /** Rótulo acessível do campo de texto (ex.: "Tags") — liga a `<label>` visual ao input. */
  ariaLabel?: string;
}

/**
 * Tag input tokenizado estilo "Gmail recipients" (feature 185, FR-009): Enter ou vírgula
 * transforma o texto digitado em um chip removível; digitar filtra sugestões existentes.
 * Componente genérico, sem dependência de terceiros — só Tailwind + estado local.
 */
export function ChipInput({ value, onChange, suggestions = [], placeholder, ariaLabel }: ChipInputProps) {
  const [draft, setDraft] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filteredSuggestions = useMemo(() => {
    const term = draft.trim().toLowerCase();
    if (!term) return [];
    return suggestions
      .filter((s) => s.toLowerCase().includes(term) && !value.includes(s))
      .slice(0, 6);
  }, [draft, suggestions, value]);

  function commitDraft(raw: string) {
    const clean = raw.trim();
    if (!clean || value.includes(clean)) {
      setDraft("");
      return;
    }
    onChange([...value, clean]);
    setDraft("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitDraft(draft);
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  function removeChip(chip: string) {
    onChange(value.filter((v) => v !== chip));
  }

  return (
    <div className="relative">
      <div className="flex min-h-10 flex-wrap items-center gap-1.5 rounded-md border border-line bg-panel px-2 py-1.5">
        {value.map((chip) => (
          <span
            key={chip}
            className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent-dark"
          >
            {chip}
            <button
              type="button"
              onClick={() => removeChip(chip)}
              aria-label={`Remover tag ${chip}`}
              className="text-accent-dark/70 hover:text-accent-dark"
            >
              ✕
            </button>
          </span>
        ))}
        <input
          className="min-w-24 flex-1 border-none bg-transparent text-sm text-ink outline-none"
          aria-label={ariaLabel}
          value={draft}
          placeholder={value.length === 0 ? placeholder : undefined}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => {
            // Delay para permitir o clique numa sugestão antes de fechar a lista.
            setTimeout(() => setShowSuggestions(false), 150);
          }}
        />
      </div>
      {showSuggestions && filteredSuggestions.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full rounded-md border border-line bg-panel py-1 shadow-md">
          {filteredSuggestions.map((s) => (
            <li key={s}>
              <button
                type="button"
                className="block w-full px-3 py-1.5 text-left text-sm text-ink hover:bg-accent-soft"
                onClick={() => commitDraft(s)}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
