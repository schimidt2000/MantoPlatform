interface TagChipsProps {
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}

/** Chips de etiqueta com seleção múltipla — usado para as categorias positiva e de atenção. */
export function TagChips({ options, selected, onChange }: TagChipsProps) {
  function toggle(tag: string) {
    onChange(selected.includes(tag) ? selected.filter((t) => t !== tag) : [...selected, tag]);
  }

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {options.map((tag) => {
        const isSelected = selected.includes(tag);
        return (
          <button
            key={tag}
            type="button"
            onClick={() => toggle(tag)}
            aria-pressed={isSelected}
            className={
              isSelected
                ? "rounded-full border-[1.5px] border-accent bg-accent px-4 py-2 text-sm font-semibold text-white"
                : "rounded-full border-[1.5px] border-line bg-panel px-4 py-2 text-sm font-semibold text-ink"
            }
          >
            {tag}
          </button>
        );
      })}
    </div>
  );
}
