import { Button } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import type { Acrescimo } from "../../lib/orcamento";

const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/**
 * Editor de acréscimos (BV, taxas, hora extra…) — extraído de `OrcamentoCalculadoraPage` na
 * feature 235 para ser fonte única entre a Calculadora de Orçamento e a contratação Manto
 * embutida no EducaManto (Princípio I). Comportamento idêntico ao original.
 */
export function AcrescimosEditor({
  acrescimos,
  onChange,
  tipos,
}: {
  acrescimos: Acrescimo[];
  onChange: (acrescimos: Acrescimo[]) => void;
  /** Tipos disponíveis no seletor — já incluindo o BV (config das Configurações de Preços). */
  tipos: string[];
}) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        O BV entra no total, mas é um repasse (não aparece para o cliente) e o PIX de quem
        recebe é informado no evento.
      </p>
      {acrescimos.map((a, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2">
          <select
            className={`${INPUT} max-w-[160px]`}
            value={a.tipo}
            onChange={(e) =>
              onChange(acrescimos.map((x, idx) => (idx === i ? { ...x, tipo: e.target.value } : x)))
            }
          >
            {tipos.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <MoneyInput
            className={`${INPUT} max-w-[120px]`}
            value={a.value}
            onValueChange={(v) =>
              onChange(acrescimos.map((x, idx) => (idx === i ? { ...x, value: v } : x)))
            }
          />
          <label className="flex items-center gap-1 text-xs text-muted">
            <input
              type="checkbox"
              checked={a.is_percent}
              onChange={(e) =>
                onChange(
                  acrescimos.map((x, idx) => (idx === i ? { ...x, is_percent: e.target.checked } : x)),
                )
              }
            />
            %
          </label>
          <Button size="sm" variant="ghost" onClick={() => onChange(acrescimos.filter((_, idx) => idx !== i))}>
            Remover
          </Button>
        </div>
      ))}
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onChange([...acrescimos, { tipo: tipos[0] ?? "", value: 0, is_percent: false }])}
      >
        + Adicionar acréscimo
      </Button>
    </div>
  );
}
