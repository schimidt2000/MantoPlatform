import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export type AvatarThumbShape = "circle" | "square";
export type AvatarThumbSize = "sm" | "md" | "lg";

export interface AvatarThumbProps {
  /** URL já resolvida da imagem (use `assetUrl()` antes de passar). `null` cai no placeholder. */
  src?: string | null;
  /** Nome usado para gerar as iniciais do placeholder e o `alt` da imagem. */
  name?: string | null;
  /** Circular para pessoas (talentos, coordenadores); quadrado para figurinos/personagens. */
  shape?: AvatarThumbShape;
  size?: AvatarThumbSize;
  /** Placeholder alternativo às iniciais (ex.: `🎭`), usado quando não há nome nem foto. */
  fallbackIcon?: ReactNode;
  className?: string;
}

const SIZE_CLASS: Record<AvatarThumbSize, string> = {
  sm: "h-7 w-7 text-[10px]",
  md: "h-9 w-9 text-xs",
  lg: "h-12 w-12 text-sm",
};

/** Iniciais do nome (no máximo duas), em maiúsculas — "Ana Paula Silva" → "AS". */
function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Miniatura de foto com placeholder elegante (feature 195, Princípio X.2).
 *
 * Circular para pessoas e quadrada para figurinos/personagens. Sem foto salva, renderiza as
 * iniciais do nome (ou `fallbackIcon`) sobre o fundo neutro do tema — nunca uma imagem quebrada.
 */
export function AvatarThumb({
  src,
  name,
  shape = "circle",
  size = "md",
  fallbackIcon,
  className,
}: AvatarThumbProps) {
  const initials = name ? initialsOf(name) : "";
  const shapeClass = shape === "circle" ? "rounded-full" : "rounded-md";

  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex flex-none select-none items-center justify-center overflow-hidden",
        "bg-surface-2 font-semibold uppercase leading-none text-muted",
        shapeClass,
        SIZE_CLASS[size],
        className,
      )}
    >
      {src ? (
        <img src={src} alt="" loading="lazy" className="h-full w-full object-cover" />
      ) : (
        (fallbackIcon ?? initials ?? null)
      )}
    </span>
  );
}
