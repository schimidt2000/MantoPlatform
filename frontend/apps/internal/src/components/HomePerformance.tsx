import { useState } from "react";
import { Button, Card, Input } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { PerformanceSummary } from "../lib/types";

export type PerformanceRange = "7" | "30" | "custom";

export interface PerformancePeriod {
  range: PerformanceRange;
  start?: string;
  end?: string;
}

interface HomePerformanceProps {
  summary: PerformanceSummary | null;
  period: PerformancePeriod;
  onPeriodChange: (period: PerformancePeriod) => void;
  /** True enquanto a troca de período está recarregando (os números antigos ficam à mostra). */
  atualizando?: boolean;
}

const RANGE_OPTIONS: { value: PerformanceRange; label: string }[] = [
  { value: "7", label: "7 dias" },
  { value: "30", label: "30 dias" },
  { value: "custom", label: "Personalizado" },
];

function formatarData(iso: string | null): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano.slice(2)}`;
}

/** Tom da barra pelo percentual concluído — verde ≥ 90 %, dourado ≥ 70 %, vermelho abaixo. */
function tomDoPercentual(pct: number): { barra: string; texto: string } {
  if (pct >= 90) return { barra: "bg-green", texto: "text-green" };
  if (pct >= 70) return { barra: "bg-gold", texto: "text-gold-ink" };
  return { barra: "bg-red", texto: "text-red" };
}

function MetricaConclusao({
  label,
  done,
  total,
  hint,
}: {
  label: string;
  done: number;
  total: number;
  hint: string;
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const tom = tomDoPercentual(pct);
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</span>
        <span className={`text-lg font-semibold leading-none tabular-nums ${total > 0 ? tom.texto : "text-muted"}`}>
          {total > 0 ? `${pct}%` : "—"}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${done} de ${total}`}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-300 ease-out ${tom.barra}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] text-muted">
        <span className="tabular-nums text-ink">{done}</span> de{" "}
        <span className="tabular-nums text-ink">{total}</span> {hint}
      </p>
    </div>
  );
}

/**
 * Painel Performance da Home — só o superadmin real recebe `performance` da API (durante o
 * "Ver como" ela vem `null` e o painel some). Somente leitura: acompanhar como as equipes
 * estão indo no período — quanto do casting foi escalado, quanto do figurino ficou pronto e
 * quanto de cachê foi comprometido.
 */
export function HomePerformance({ summary, period, onPeriodChange, atualizando }: HomePerformanceProps) {
  const [rascunho, setRascunho] = useState({ start: period.start ?? "", end: period.end ?? "" });
  const personalizadoInvalido = !rascunho.start || !rascunho.end || rascunho.start > rascunho.end;

  return (
    <Card className="divide-y divide-line">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2.5">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <h3 className="text-sm font-semibold text-ink">📈 Performance</h3>
          <span className="text-[11px] text-muted">
            {summary ? `${formatarData(summary.start)} – ${formatarData(summary.end)}` : "período inválido"}
            {" · "}só você vê
          </span>
        </div>
        <div
          className="inline-flex rounded-md border border-line bg-surface p-0.5"
          role="radiogroup"
          aria-label="Período da performance"
        >
          {RANGE_OPTIONS.map((opt) => {
            const ativo = period.range === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={ativo}
                onClick={() =>
                  onPeriodChange(
                    opt.value === "custom"
                      ? { range: "custom", start: rascunho.start || undefined, end: rascunho.end || undefined }
                      : { range: opt.value },
                  )
                }
                className={`cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  ativo ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink"
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {period.range === "custom" && (
        <form
          className="flex flex-wrap items-center gap-2 px-4 py-2.5"
          onSubmit={(e) => {
            e.preventDefault();
            if (!personalizadoInvalido) {
              onPeriodChange({ range: "custom", start: rascunho.start, end: rascunho.end });
            }
          }}
        >
          <Input
            type="date"
            value={rascunho.start}
            onChange={(e) => setRascunho((r) => ({ ...r, start: e.target.value }))}
            className="h-9 w-40"
            aria-label="Data inicial"
          />
          <span className="text-sm text-muted">até</span>
          <Input
            type="date"
            value={rascunho.end}
            onChange={(e) => setRascunho((r) => ({ ...r, end: e.target.value }))}
            className="h-9 w-40"
            aria-label="Data final"
          />
          <Button type="submit" size="sm" variant="outline" disabled={personalizadoInvalido}>
            Aplicar
          </Button>
        </form>
      )}

      {summary ? (
        <div
          className={`grid gap-4 px-4 py-3 transition-opacity duration-200 sm:grid-cols-3 ${
            atualizando ? "opacity-60" : ""
          }`}
          aria-busy={atualizando || undefined}
        >
          <MetricaConclusao
            label="Casting escalado"
            done={summary.casting_done}
            total={summary.casting_total}
            hint="cargos com talento definido"
          />
          <MetricaConclusao
            label="Figurino pronto"
            done={summary.figurino_done}
            total={summary.figurino_total}
            hint="cargos com figurino fechado"
          />
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Cachês escalados
            </span>
            <div className="text-lg font-semibold leading-none tabular-nums text-ink">
              R$ {formatBRL(summary.money_total)}
            </div>
            <p className="text-[11px] text-muted">soma dos cachês dos cargos escalados no período</p>
          </div>
        </div>
      ) : (
        <p className="px-4 py-3 text-sm text-muted">
          Escolha um período válido (data inicial até data final) e clique em Aplicar.
        </p>
      )}
    </Card>
  );
}
