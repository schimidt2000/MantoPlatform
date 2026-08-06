import { Star } from "lucide-react";

const SCORES = [1, 2, 3, 4, 5] as const;

/**
 * Seletor de nota de 1 a 5 estrelas.
 *
 * Radiogroup de verdade (não um `<div>` clicável): cada estrela é um `<input type="radio">`
 * invisível sobre um alvo de 44px, então funciona por toque, por teclado e para leitor de tela.
 */
export function StarRating({
  name,
  value,
  onChange,
  label,
  disabled = false,
}: {
  name: string;
  value: number | null;
  onChange: (score: number) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className="sr-only">{label}</legend>
      <div className="flex items-center gap-0.5">
        {SCORES.map((score) => {
          const active = value != null && score <= value;
          return (
            <label
              key={score}
              className={`relative flex h-11 w-11 items-center justify-center rounded-md ${
                disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-surface-2"
              }`}
            >
              <input
                type="radio"
                name={name}
                value={score}
                checked={value === score}
                onChange={() => onChange(score)}
                className="absolute inset-0 cursor-inherit opacity-0"
                aria-label={`${score} ${score === 1 ? "estrela" : "estrelas"}`}
              />
              {/* Estrela vazia em `text-line` (1.2:1 sobre o branco do Card) desaparecia: o
                  artista abria a tela de avaliação e via espaço em branco no lugar do
                  seletor. `line` é token de borda de 1px, não de ícone de 24px que precisa
                  ser percebido e tocado — `muted` dá 7.17:1 e mantém o contorno leve. */}
              <Star
                className={`h-6 w-6 ${active ? "fill-accent text-accent" : "text-muted"}`}
                aria-hidden="true"
              />
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
