import { X } from "lucide-react";
import { Button } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import { brl } from "../../lib/pagamentos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Mesmos limites de `parcela_ops` no servidor (a tela só antecipa; quem decide é ele). */
export const MIN_PARCELAS = 2;
export const MAX_PARCELAS = 24;

const SITUACAO_TRAVADA: Record<"no_banco" | "pago", string> = {
  no_banco: "No banco",
  pago: "Paga",
};

/** Uma linha do formulário. `chave` só existe para o React; `id` só nas parcelas já gravadas. */
export interface ParcelaLinha {
  chave: string;
  id?: number;
  data: string;
  valor: number;
  status?: "nao_pago" | "no_banco" | "pago";
}

let proximaChave = 0;
export function novaLinha(data = "", valor = 0): ParcelaLinha {
  proximaChave += 1;
  return { chave: `nova-${proximaChave}`, data, valor };
}

export function somaDasLinhas(linhas: ParcelaLinha[]): number {
  return Math.round(linhas.reduce((total, l) => total + (l.valor || 0), 0) * 100) / 100;
}

function travada(linha: ParcelaLinha): linha is ParcelaLinha & { status: "no_banco" | "pago" } {
  return linha.status === "pago" || linha.status === "no_banco";
}

export interface ParcelasCampoProps {
  ativo: boolean;
  linhas: ParcelaLinha[];
  fieldErrors: Record<string, string>;
  onAtivar: (ativo: boolean) => void;
  onLinhas: (linhas: ParcelaLinha[]) => void;
}

/**
 * "Pagar em parcelas" no gasto extra (feature 353).
 *
 * Cada parcela tem data e valor; o valor do gasto passa a ser a soma (a tela de cima mostra o
 * total). A parcela paga ou "no banco" aparece travada: muda só depois de desmarcada na Planilha de
 * Pagamentos. Os erros chegam do servidor pelo índice da parcela (`parcelas.N.data|valor`).
 */
export function ParcelasCampo({ ativo, linhas, fieldErrors, onAtivar, onLinhas }: ParcelasCampoProps) {
  const algumaTravada = linhas.some(travada);
  const mudar = (indice: number, patch: Partial<ParcelaLinha>) =>
    onLinhas(linhas.map((l, i) => (i === indice ? { ...l, ...patch } : l)));

  return (
    <div className="space-y-2">
      <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={ativo}
          disabled={ativo && algumaTravada}
          onChange={(e) => onAtivar(e.target.checked)}
        />
        Pagar em parcelas
      </label>
      {ativo && algumaTravada && (
        <p className="text-xs text-muted">Com parcela paga, o gasto continua parcelado.</p>
      )}
      {ativo && (
        <div className="space-y-2 rounded-md border border-line p-2">
          {linhas.map((linha, indice) => {
            const bloqueada = travada(linha);
            const erroData = fieldErrors[`parcelas.${indice}.data`];
            const erroValor = fieldErrors[`parcelas.${indice}.valor`];
            return (
              <div key={linha.chave} className="space-y-1">
                <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-end gap-2">
                  <div className="min-w-0">
                    <label className={LABEL} htmlFor={`parcela-data-${linha.chave}`}>
                      Parcela {indice + 1} · data
                    </label>
                    <input
                      id={`parcela-data-${linha.chave}`}
                      type="date"
                      className={INPUT}
                      value={linha.data}
                      disabled={bloqueada}
                      aria-invalid={Boolean(erroData)}
                      onChange={(e) => mudar(indice, { data: e.target.value })}
                    />
                  </div>
                  <div className="min-w-0">
                    <label className={LABEL} htmlFor={`parcela-valor-${linha.chave}`}>
                      Valor (R$)
                    </label>
                    <MoneyInput
                      id={`parcela-valor-${linha.chave}`}
                      className={INPUT}
                      value={linha.valor}
                      disabled={bloqueada}
                      onValueChange={(valor) => mudar(indice, { valor })}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 px-0"
                    aria-label={`Remover parcela ${indice + 1}`}
                    disabled={bloqueada || linhas.length <= MIN_PARCELAS}
                    onClick={() => onLinhas(linhas.filter((_, i) => i !== indice))}
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
                {bloqueada && (
                  <p className="text-xs text-muted">
                    {SITUACAO_TRAVADA[linha.status]}: altere na Planilha de Pagamentos para editar.
                  </p>
                )}
                {(erroData || erroValor) && (
                  <p className="text-xs text-red" role="alert">
                    {erroData || erroValor}
                  </p>
                )}
              </div>
            );
          })}
          {fieldErrors.parcelas && (
            <p className="text-xs text-red" role="alert">
              {fieldErrors.parcelas}
            </p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={linhas.length >= MAX_PARCELAS}
              onClick={() => onLinhas([...linhas, novaLinha()])}
            >
              + Adicionar parcela
            </Button>
            <p className="text-sm tabular-nums text-ink">
              Total das parcelas: <span className="font-semibold">{brl(somaDasLinhas(linhas))}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
