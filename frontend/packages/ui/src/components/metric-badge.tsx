import { type ReactNode } from "react";
import { cn } from "../lib/cn";

type MetricBadgeTone = "neutral" | "accent" | "green" | "red" | "blue" | "gold";

export interface MetricBadgeProps {
  /** Itens unidos por "•" (ex.: ["180cm", "M", "Calçado 40"]). */
  items?: string[];
  tone?: MetricBadgeTone;
  size?: "xs" | "sm";
  className?: string;
  children?: ReactNode;
}

const TONE_CLASSES: Record<MetricBadgeTone, string> = {
  neutral: "bg-surface-2 text-ink",
  accent: "bg-accent-soft text-accent",
  green: "bg-green-soft text-green",
  red: "bg-red-soft text-red",
  blue: "bg-blue-soft text-blue",
  // `text-gold-ink` (5.15:1 sobre `gold-soft`) — `text-gold` dava 3.25:1 e reprovava AA.
  gold: "bg-gold-soft text-gold-ink",
};

/**
 * Badge métrico compacto do design system Manto (feature 173): medidas de
 * talento ("180cm • M • 40"), status de evento e afins — alta densidade sem
 * perder legibilidade (mínimo 12px em superfícies públicas; aqui painel staff).
 */
function MetricBadge({ items, tone = "neutral", size = "xs", className, children }: MetricBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full font-medium tabular-nums",
        size === "xs" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {items ? items.join(" • ") : children}
    </span>
  );
}

export { MetricBadge };
