import { type ReactNode } from "react";
import { cn } from "../lib/cn";
import { Card } from "./card";

export interface DenseCardStat {
  label: string;
  value: ReactNode;
}

export interface DenseCardProps {
  title?: ReactNode;
  /** Conteúdo à direita do cabeçalho (badge, ação, contagem). */
  headerRight?: ReactNode;
  /** Estatísticas rápidas em linha, separadas por divisórias. */
  stats?: DenseCardStat[];
  padding?: "compact" | "normal";
  className?: string;
  children?: ReactNode;
}

/**
 * Card denso do design system Manto (feature 173): cabeçalho compacto, divisões
 * limpas e faixa opcional de estatísticas — densidade de informação do painel
 * clássico com o acabamento do design system.
 */
function DenseCard({
  title,
  headerRight,
  stats,
  padding = "compact",
  className,
  children,
}: DenseCardProps) {
  const pad = padding === "compact" ? "px-4 py-3" : "px-5 py-4";
  return (
    <Card className={cn("divide-y divide-line", className)}>
      {(title || headerRight) && (
        <div className={cn("flex items-center justify-between gap-2", pad, "py-2.5")}>
          {title && <h3 className="truncate text-sm font-semibold text-ink">{title}</h3>}
          {headerRight && <div className="flex shrink-0 items-center gap-2">{headerRight}</div>}
        </div>
      )}
      {stats && stats.length > 0 && (
        <div className="flex divide-x divide-line">
          {stats.map((stat) => (
            <div key={stat.label} className={cn("flex-1", pad, "py-2.5")}>
              <div className="text-lg font-semibold leading-tight text-ink">{stat.value}</div>
              <div className="text-[11px] uppercase tracking-wide text-muted">{stat.label}</div>
            </div>
          ))}
        </div>
      )}
      {children && <div className={pad}>{children}</div>}
    </Card>
  );
}

export { DenseCard };
