import { Star } from "lucide-react";
import { cn } from "../lib/cn";

const SCORES = [1, 2, 3, 4, 5] as const;

const SIZES = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-6 w-6",
} as const;

export interface StarRatingProps {
  /** Nota exibida, de 0 a 5. Aceita fração (ex.: 4.3) — a última estrela é preenchida em parte. */
  value: number;
  /** Tamanho do ícone. `md` é o padrão das listagens; `lg` para KPI em destaque. */
  size?: keyof typeof SIZES;
  /** Rótulo acessível. Padrão: `"4,3 de 5 estrelas"`. */
  label?: string;
  className?: string;
}

/**
 * Estrelas em modo somente-leitura (feature 197).
 *
 * Fonte única de exibição de nota no design system: substitui os `StarsInt`/`StarsAvg` locais
 * que a tela de avaliações do casting mantinha em cópia própria. Aceita nota fracionária
 * (média) preenchendo a estrela parcial por recorte, então serve tanto para a nota inteira de
 * uma avaliação quanto para a média geral de um KPI.
 *
 * NÃO confundir com `apps/portal/src/components/StarRating.tsx`, que é o *seletor* de nota
 * (radiogroup interativo do formulário de avaliação do talento). Este aqui só exibe.
 */
export function StarRating({ value, size = "md", label, className }: StarRatingProps) {
  const clamped = Math.min(5, Math.max(0, Number.isFinite(value) ? value : 0));
  const iconSize = SIZES[size];
  const ariaLabel = label ?? `${clamped.toFixed(1).replace(".", ",")} de 5 estrelas`;

  return (
    <span
      className={cn("relative inline-flex shrink-0 align-middle", className)}
      role="img"
      aria-label={ariaLabel}
    >
      <span className="flex items-center gap-0.5" aria-hidden="true">
        {SCORES.map((score) => (
          <Star key={score} className={cn(iconSize, "text-line")} />
        ))}
      </span>
      <span
        className="absolute inset-y-0 left-0 flex items-center gap-0.5 overflow-hidden"
        style={{ width: `${(clamped / 5) * 100}%` }}
        aria-hidden="true"
      >
        {SCORES.map((score) => (
          <Star key={score} className={cn(iconSize, "shrink-0 fill-gold text-gold")} />
        ))}
      </span>
    </span>
  );
}
