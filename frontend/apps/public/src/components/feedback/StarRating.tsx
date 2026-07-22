import { useState } from "react";

interface StarRatingProps {
  score: number;
  onChange: (score: number) => void;
}

/** Grupo de 5 estrelas — substitui o truque CSS `radio` + `~` do Jinja (`research.md` §3). */
export function StarRating({ score, onChange }: StarRatingProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const filledUpTo = hovered ?? score;

  return (
    <div className="flex justify-center gap-2" onMouseLeave={() => setHovered(null)}>
      {[1, 2, 3, 4, 5].map((value) => (
        <button
          key={value}
          type="button"
          aria-label={`${value} estrela${value > 1 ? "s" : ""}`}
          aria-pressed={score === value}
          className="flex h-11 w-11 items-center justify-center text-4xl leading-none transition-transform active:scale-90"
          style={{ color: value <= filledUpTo ? "#f59e0b" : "#d9d5e8" }}
          onMouseEnter={() => setHovered(value)}
          onClick={() => onChange(value)}
        >
          ★
        </button>
      ))}
    </div>
  );
}
