import { Fragment } from "react";
import { ChevronRight } from "lucide-react";

export interface FunnelStage {
  label: string;
  value: number;
  display: string;
}

interface FunnelChartProps {
  /** Etapas em ordem (gasto → cliques → leads → eventos). */
  stages: FunnelStage[];
  /** Texto da relação entre a etapa anterior e esta (ex.: "CPC R$ 0,92", "3,4 % viram lead"). */
  ratios: (string | null)[];
}

/**
 * Funil de unidades mistas: R$, cliques, leads e eventos não cabem na mesma escala, então
 * cada etapa é um tile e a relação entre etapas (custo ou taxa) fica na seta — é a relação
 * que responde "o que rendeu", não o tamanho relativo das barras.
 */
export function FunnelChart({ stages, ratios }: FunnelChartProps) {
  if (stages.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">Sem dado no período.</p>;
  }
  return (
    <ol className="grid grid-cols-2 gap-y-3 sm:flex sm:items-stretch sm:gap-0 sm:overflow-x-auto sm:pb-1" aria-label="Funil do período">
      {stages.map((etapa, i) => (
        <Fragment key={etapa.label}>
          {i > 0 && (
            <li
              aria-hidden="true"
              className="hidden min-w-[88px] flex-col items-center justify-center px-1 text-center text-[11px] leading-tight text-muted sm:flex"
            >
              <ChevronRight className="h-4 w-4 text-line-strong" />
              {ratios[i - 1] ?? "—"}
            </li>
          )}
          <li className="flex-1 rounded-lg border border-line bg-surface px-3 py-2.5">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted">{etapa.label}</span>
            <span className="block whitespace-nowrap text-lg font-semibold leading-tight tabular-nums text-ink sm:text-xl">{etapa.display}</span>
            {i > 0 && <span className="block text-[11px] text-muted sm:hidden">{ratios[i - 1] ?? "—"}</span>}
          </li>
        </Fragment>
      ))}
    </ol>
  );
}
