import { Input } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import type { ModoDevolucao } from "../../lib/agenda";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

const MODOS: { modo: ModoDevolucao; rotulo: string; ajuda: string }[] = [
  { modo: "tudo", rotulo: "Devolver tudo", ajuda: "A Manto não fica com nada." },
  { modo: "parte", rotulo: "Devolver parte", ajuda: "Você informa quanto volta." },
  { modo: "nada", rotulo: "Não devolver", ajuda: "A Manto retém o que recebeu." },
];

export interface DevolucaoState {
  modo: ModoDevolucao | null;
  valor: number;
  nome: string;
  pix: string;
  observacao: string;
}

interface CancelamentoDevolucaoBlocoProps {
  state: DevolucaoState;
  onChange: (patch: Partial<DevolucaoState>) => void;
  /** Pago do grupo (o que a cliente pagou). */
  pago: number;
  /** Pago − já devolvido: o que "Tudo" devolve. */
  maxDevolucao: number;
  comprovantesSemValor: number;
  erros: Record<string, string>;
}

/**
 * "Devolução à cliente" do diálogo de cancelar (feature 306, FR-023): começa sem modo marcado
 * (D27, "vem vazio"); o valor só em Parte (em Tudo, só leitura); nome e PIX só em Tudo e Parte.
 * Com pago zero, só "Não devolver" fica habilitado. Nenhuma conta aqui: o máximo vem do servidor.
 */
export function CancelamentoDevolucaoBloco({
  state,
  onChange,
  pago,
  maxDevolucao,
  comprovantesSemValor,
  erros,
}: CancelamentoDevolucaoBlocoProps) {
  const pagoZero = pago <= 0;
  const devolve = state.modo === "tudo" || state.modo === "parte";

  return (
    <fieldset className="rounded-md border border-line p-3">
      <legend className="px-1 text-xs font-semibold uppercase text-muted">Devolução à cliente</legend>
      <p className="mb-2 text-sm text-ink">
        A cliente pagou <strong>{brl(pago)}</strong>
        {maxDevolucao < pago && <> — dá para devolver até {brl(maxDevolucao)}</>}.
      </p>
      {pagoZero && (
        <p className="mb-2 text-xs text-gold-ink" role="note">
          Sem pagamento com valor: só cabe “Não devolver”.
          {comprovantesSemValor > 0 &&
            ` ${comprovantesSemValor} comprovante(s) estão sem valor — corrija na aba Financeiro se a cliente pagou.`}
        </p>
      )}
      <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Quanto devolver">
        {MODOS.map(({ modo, rotulo, ajuda }) => {
          const desabilitado = pagoZero && modo !== "nada";
          const marcado = state.modo === modo;
          return (
            <label
              key={modo}
              className={`flex min-h-11 cursor-pointer items-start gap-2 rounded-md border p-2 text-sm ${
                marcado ? "border-blue bg-blue-soft" : "border-line"
              } ${desabilitado ? "cursor-not-allowed opacity-50" : ""}`}
            >
              <input
                type="radio"
                name="modo-devolucao"
                className="mt-1"
                checked={marcado}
                disabled={desabilitado}
                onChange={() => onChange({ modo })}
              />
              <span>
                <span className="block font-semibold text-ink">{rotulo}</span>
                <span className="block text-xs text-muted">{ajuda}</span>
              </span>
            </label>
          );
        })}
      </div>
      {erros.devolucao_modo && (
        <p className="mt-1 text-xs text-red" role="alert">
          {erros.devolucao_modo}
        </p>
      )}

      {devolve && (
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <div>
            <label className={LABEL} htmlFor="devolucao-valor">
              Valor a devolver
            </label>
            {state.modo === "parte" ? (
              <MoneyInput
                id="devolucao-valor"
                className={FIELD}
                value={state.valor}
                onValueChange={(valor) => onChange({ valor })}
                aria-invalid={Boolean(erros.devolucao_valor)}
              />
            ) : (
              <p id="devolucao-valor" className="flex h-10 items-center text-sm font-semibold text-ink">
                {brl(maxDevolucao)}
              </p>
            )}
            {erros.devolucao_valor && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erros.devolucao_valor}
              </p>
            )}
          </div>
          <div>
            <label className={LABEL} htmlFor="devolucao-nome">
              Quem recebe
            </label>
            <Input
              id="devolucao-nome"
              value={state.nome}
              maxLength={200}
              onChange={(e) => onChange({ nome: e.target.value })}
              aria-invalid={Boolean(erros.devolucao_nome)}
            />
            {erros.devolucao_nome && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erros.devolucao_nome}
              </p>
            )}
          </div>
          <div>
            <label className={LABEL} htmlFor="devolucao-pix">
              PIX
            </label>
            <Input
              id="devolucao-pix"
              value={state.pix}
              maxLength={120}
              onChange={(e) => onChange({ pix: e.target.value })}
              aria-invalid={Boolean(erros.devolucao_pix)}
            />
            {erros.devolucao_pix && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erros.devolucao_pix}
              </p>
            )}
          </div>
          <div className="sm:col-span-3">
            <label className={LABEL} htmlFor="devolucao-observacao">
              Observação (opcional)
            </label>
            <Input
              id="devolucao-observacao"
              value={state.observacao}
              onChange={(e) => onChange({ observacao: e.target.value })}
            />
          </div>
          <p className="text-xs text-muted sm:col-span-3">
            A devolução entra aprovada em Gastos Extras e vai à Planilha de Pagamentos do mês.
          </p>
        </div>
      )}
    </fieldset>
  );
}
