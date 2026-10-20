import { Input } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { ImpactoExclusao } from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

export type BvEntrada = { recebedor: string; pix: string };

interface CancelamentoBvBlocoProps {
  bvs: NonNullable<ImpactoExclusao["bvs"]>;
  /** O BV do retido por acréscimo, vindo da prévia (`efeito.bvs`); ausente enquanto não há prévia. */
  proporcional: Map<number, number>;
  entradas: Record<number, BvEntrada>;
  onEntrada: (acrescimoId: number, entrada: BvEntrada) => void;
  erros: Record<string, string>;
}

/**
 * "BV do parceiro" do diálogo de cancelar (feature 306, FR-023): sem campo de valor — o BV
 * acompanha o retido. Mostra o cheio, o proporcional (da prévia, nunca calculado aqui) e o "já
 * pago". Quando faltam, quem recebe e o PIX são obrigatórios: esse PIX vai à Planilha.
 */
export function CancelamentoBvBloco({ bvs, proporcional, entradas, onEntrada, erros }: CancelamentoBvBlocoProps) {
  if (bvs.length === 0) return null;
  return (
    <fieldset className="rounded-md border border-line p-3">
      <legend className="px-1 text-xs font-semibold uppercase text-muted">BV do parceiro</legend>
      <ul className="space-y-3">
        {bvs.map((bv) => {
          const conta = proporcional.get(bv.acrescimo_id);
          const falta = !bv.pago && (bv.falta_recebedor || bv.falta_pix);
          const entrada = entradas[bv.acrescimo_id] ?? { recebedor: "", pix: "" };
          const erro = erros[`bv_pix_${bv.acrescimo_id}`];
          return (
            <li key={bv.acrescimo_id} className="text-sm">
              <p className="text-ink">
                <strong>{bv.recebedor || "Sem recebedor"}</strong> — BV cheio {brl(bv.cheio)}
              </p>
              <p className="text-xs text-muted">
                {bv.pago
                  ? "Já pago: fica pelo valor pago, sem acerto ao parceiro."
                  : conta === undefined
                    ? "Escolha a devolução para ver o BV que acompanha o retido."
                    : conta > 0
                      ? `Acompanha o retido: ${brl(conta)} a pagar na Planilha.`
                      : "Sem retido, o BV sai da Planilha."}
              </p>
              {falta && (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <div>
                    <label className={LABEL} htmlFor={`bv-recebedor-${bv.acrescimo_id}`}>
                      Quem recebe o BV
                    </label>
                    <Input
                      id={`bv-recebedor-${bv.acrescimo_id}`}
                      value={entrada.recebedor}
                      maxLength={200}
                      placeholder={bv.recebedor ?? ""}
                      onChange={(e) => onEntrada(bv.acrescimo_id, { ...entrada, recebedor: e.target.value })}
                      aria-invalid={Boolean(erro)}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor={`bv-pix-${bv.acrescimo_id}`}>
                      PIX do BV
                    </label>
                    <Input
                      id={`bv-pix-${bv.acrescimo_id}`}
                      value={entrada.pix}
                      maxLength={140}
                      onChange={(e) => onEntrada(bv.acrescimo_id, { ...entrada, pix: e.target.value })}
                      aria-invalid={Boolean(erro)}
                    />
                  </div>
                  <p className="text-xs text-gold-ink sm:col-span-2">
                    Esse PIX vai à Planilha de Pagamentos — sem ele, o BV não tem como ser pago.
                  </p>
                </div>
              )}
              {erro && (
                <p className="mt-1 text-xs text-red" role="alert">
                  {erro}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
