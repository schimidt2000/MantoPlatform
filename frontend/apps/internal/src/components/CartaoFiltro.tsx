import { Card, cn } from "@manto/ui";
import { brl, type BucketTone } from "../lib/pagamentos";

export interface CartaoFiltroProps {
  label: string;
  value: number;
  /** Nº de itens da faixa — mostra o tamanho do filtro antes do clique. */
  count: number;
  /** Cores da faixa; `null` = cartão neutro ("Total no período", "Todos"), que limpa o filtro. */
  tone: BucketTone | null;
  active: boolean;
  /** Há um filtro ativo em OUTRO cartão — este fica apagado para não competir. */
  dimmed: boolean;
  /** Singular e plural da contagem: ["item", "itens"] em Pagamentos, ["gasto", "gastos"] em Gastos. */
  unidade: readonly [string, string];
  /** Ajuste de grade (ex.: o cartão neutro ocupando a linha inteira no celular). */
  className?: string;
  onClick: () => void;
}

/**
 * Cartão de KPI que também é o seletor de filtro da lista (feature 194, extraído de
 * `PagamentosPage` na 314 para Gastos Extras usar o mesmo). Clicar filtra; clicar de novo no
 * ativo limpa. As cores vêm do tom da faixa, então o cartão e as linhas que ele revela têm sempre
 * a mesma cor.
 */
export function CartaoFiltro({
  label,
  value,
  count,
  tone,
  active,
  dimmed,
  unidade,
  className,
  onClick,
}: CartaoFiltroProps) {
  return (
    // As classes vão TODAS no `Card` (que passa por `cn`/twMerge e resolve `border` vs
    // `border-2`, `bg-panel` vs `bg-green-50/50`); o `Slot` do `asChild` só concatena o
    // className do filho, sem desempatar conflito de utilitário.
    <Card
      asChild
      className={cn(
        "border-2 p-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-4",
        active
          ? tone
            ? `${tone.cardActive} shadow-md`
            : "border-accent bg-accent-soft shadow-md"
          : "border-line bg-panel hover:border-accent/40 hover:shadow-md",
        dimmed && "opacity-60 grayscale-[35%] hover:opacity-100 hover:grayscale-0",
        className,
      )}
    >
      {/* `span`, não `p`: o conteúdo de um `<button>` só aceita phrasing content. */}
      <button type="button" onClick={onClick} aria-pressed={active}>
        <span className="block text-[10px] font-bold uppercase tracking-wide text-muted sm:text-[11px]">
          {label}
        </span>
        <span className={cn("mt-1 block text-base font-bold tabular-nums sm:text-lg", tone?.text ?? "text-ink")}>
          {brl(value)}
        </span>
        <span className="mt-0.5 block text-[10px] font-semibold text-muted">
          {count} {count === 1 ? unidade[0] : unidade[1]}
          {/* O cartão neutro fica "ativo" quando NÃO há filtro — anunciar "filtro ativo" nele
              dizia o contrário do que acontece. */}
          {active && tone ? " · filtro ativo" : ""}
        </span>
      </button>
    </Card>
  );
}
