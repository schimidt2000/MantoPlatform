import { type ReactNode } from "react";
import { cn } from "../lib/cn";

type BadgeTone = "neutral" | "accent" | "green" | "red" | "blue" | "gold";

export interface BadgeProps {
  tone?: BadgeTone;
  className?: string;
  children: ReactNode;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: "bg-surface-2 text-ink",
  accent: "bg-accent-soft text-accent",
  green: "bg-green-soft text-green",
  red: "bg-red-soft text-red",
  blue: "bg-blue-soft text-blue",
  // `text-gold-ink` (5.15:1) e não `text-gold` (3.25:1): o dourado da marca é cor de
  // preenchimento gráfico, não de texto sobre fundo claro.
  gold: "bg-gold-soft text-gold-ink",
};

/**
 * Rótulo compacto de valor único (tipo de evento, receptivo/interativo, situação) — mesmos
 * tokens de cor de `MetricBadge`, mas para um texto só em vez de uma lista de itens unidos
 * por "•". Use `MetricBadge` quando o conteúdo for uma lista de métricas.
 */
function Badge({ tone = "neutral", className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        // 11px e não 10px: o Badge carrega estado ("Confirmado", "Precisa de Ajustes"), e a
        // 10px nenhum par de cor do sistema se sustenta como texto normal.
        "inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-bold whitespace-nowrap",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export { Badge };
