import { Badge } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import type { AlcanceCancelamento, GrupoDoImpacto } from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** `AAAA-MM-DD` → `DD/MM`, pela string (sem `new Date`). */
function diaMes(iso: string | null | undefined): string {
  if (!iso) return "";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return dia ? `${dia}/${mes}` : "";
}

interface CancelamentoDiasBlocoProps {
  eventId: number;
  grupo: GrupoDoImpacto;
  /** Este evento é um dia do grupo (não o 1º): o corte, sem escolha de alcance. */
  ehDia: boolean;
  /** O 1º dia tem outro dia vivo: só então há escolha de alcance. */
  outrosVivos: boolean;
  alcance: AlcanceCancelamento | null;
  onAlcance: (alcance: AlcanceCancelamento) => void;
  /** Corte (o dia, ou o 1º dia com "só este dia"): pede o novo valor da venda do grupo. */
  corta: boolean;
  vendaDoGrupo: number;
  vendaNova: number;
  onVendaNova: (valor: number) => void;
  erros: Record<string, string>;
}

/**
 * Os dias do grupo no diálogo de cancelar (feature 306, H5; FR-054–FR-058).
 *
 * No 1º dia com outros dias vivos, a escolha: "Todos os dias" (a venda inteira é cancelada) ou "Só
 * este dia" (a venda passa ao dia vivo mais cedo, que o servidor indicou). No corte — um dia do
 * grupo, ou o 1º dia com "só este dia" —, o novo valor da venda do grupo: a prévia do servidor diz a
 * devolução mínima. Nenhuma conta de dinheiro aqui.
 */
export function CancelamentoDiasBloco({
  eventId,
  grupo,
  ehDia,
  outrosVivos,
  alcance,
  onAlcance,
  corta,
  vendaDoGrupo,
  vendaNova,
  onVendaNova,
  erros,
}: CancelamentoDiasBlocoProps) {
  const proximo = grupo.proximo_principal ?? null;
  const opcoes: { valor: AlcanceCancelamento; rotulo: string; ajuda: string }[] = [
    {
      valor: "todos",
      rotulo: "Todos os dias do grupo",
      ajuda: "A venda inteira é cancelada; cada dia vivo sai da agenda.",
    },
    {
      valor: "so_este_dia",
      rotulo: "Só este dia",
      ajuda: proximo
        ? `A venda, os comprovantes, a comissão, o BV, as parcelas, a nota e o contrato passam para ${diaMes(proximo.data)} — ${proximo.titulo}.`
        : "Não há outro dia vivo para receber a venda.",
    },
  ];

  return (
    <fieldset className="rounded-md border border-line p-3">
      <legend className="px-1 text-xs font-semibold uppercase text-muted">Dias do grupo</legend>
      <ul className="mb-2 divide-y divide-line text-sm">
        {/* O dia já cancelado não vira linha (FR-054): ele fica como está. */}
        {grupo.dias.filter((d) => !d.cancelado).map((d) => (
          <li key={d.id} className="flex flex-wrap items-center gap-2 py-1.5">
            <span className="tabular-nums text-muted">{diaMes(d.data)}</span>
            <span className="min-w-0 flex-1 truncate text-ink">{d.titulo}</span>
            {d.id === eventId && <Badge tone="blue">este</Badge>}
            {d.id === grupo.principal_id && d.id !== eventId && <Badge tone="neutral">1º dia</Badge>}
            {d.cache_pago && <Badge tone="gold">cachê pago</Badge>}
          </li>
        ))}
      </ul>
      {grupo.dias.some((d) => d.cancelado) && (
        <p className="mb-2 text-xs text-muted">Os dias já cancelados do grupo ficam como estão.</p>
      )}

      {!ehDia && outrosVivos && (
        <>
          <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="O que cancelar">
            {opcoes.map(({ valor, rotulo, ajuda }) => {
              const desabilitado = valor === "so_este_dia" && !proximo;
              const marcado = alcance === valor;
              return (
                <label
                  key={valor}
                  className={`flex min-h-11 cursor-pointer items-start gap-2 rounded-md border p-2 text-sm ${
                    marcado ? "border-blue bg-blue-soft" : "border-line"
                  } ${desabilitado ? "cursor-not-allowed opacity-50" : ""}`}
                >
                  <input
                    type="radio"
                    name="alcance-cancelamento"
                    className="mt-1"
                    checked={marcado}
                    disabled={desabilitado}
                    onChange={() => onAlcance(valor)}
                  />
                  <span>
                    <span className="block font-semibold text-ink">{rotulo}</span>
                    <span className="block text-xs text-muted">{ajuda}</span>
                  </span>
                </label>
              );
            })}
          </div>
          {erros.alcance && (
            <p className="mt-1 text-xs text-red" role="alert">
              {erros.alcance}
            </p>
          )}
        </>
      )}

      {corta && (
        <div className="mt-3">
          <label className={LABEL} htmlFor="venda-nova">
            Novo valor da venda do grupo
          </label>
          <MoneyInput
            id="venda-nova"
            className={FIELD}
            value={vendaNova}
            onValueChange={onVendaNova}
            aria-invalid={Boolean(erros.venda_nova)}
          />
          <p className="mt-1 text-xs text-muted">
            O total que a cliente paga depois do corte: os dias que ficam mais o que a Manto retém deste
            dia (até {brl(vendaDoGrupo)}, a venda de hoje). A comissão e o BV a pagar acompanham.
          </p>
          {erros.venda_nova && (
            <p className="mt-1 text-xs text-red" role="alert">
              {erros.venda_nova}
            </p>
          )}
        </div>
      )}
    </fieldset>
  );
}
