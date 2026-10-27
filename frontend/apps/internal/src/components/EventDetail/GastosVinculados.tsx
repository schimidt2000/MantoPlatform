import type { EventGasto } from "../../lib/agenda";
import { brl, formatDay } from "./parts";
import { LinkDeArquivo } from "../ArquivoViewer";

/**
 * "Gastos extras vinculados (aprovados)" (FR-061): a lista que o `KpiGrid` mostra no evento vivo e
 * o `ResultadoCancelamento` no cancelado — ali, a devolução, as multas e os outros gastos dos dias do
 * ato. A lista só chega a quem vê o financeiro, então o próprio payload é o portão.
 */
export function GastosVinculados({ gastos }: { gastos: EventGasto[] }) {
  if (gastos.length === 0) return null;
  return (
    <div className="mt-3">
      <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">
        Gastos extras vinculados (aprovados)
      </div>
      <ul className="divide-y divide-line text-sm">
        {gastos.map((gasto) => (
          <li key={gasto.id} className="flex items-center justify-between gap-2 py-1.5">
            <span className="min-w-0 truncate text-ink">
              {gasto.description}
              <span className="ml-2 text-xs text-muted">{gasto.category}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              <span className="text-xs text-muted tabular-nums">{formatDay(gasto.expense_date)}</span>
              <span className="tabular-nums text-ink">{brl(gasto.amount)}</span>
              {gasto.receipt_path && (
                <LinkDeArquivo
                  caminho={gasto.receipt_path}
                  className="text-blue underline"
                >
                  Ver comprovante
                </LinkDeArquivo>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
