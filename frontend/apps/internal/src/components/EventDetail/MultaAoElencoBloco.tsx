import { formatBRL, MoneyInput } from "@manto/money";

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

/** Uma escalação (vaga × dia) que pode receber multa. */
export interface LinhaDeMulta {
  /** `role_id` no ato; `elenco_id` depois dele. */
  chave: number;
  artista: string | null;
  vaga: string;
  dia: string | null;
  cacheReferencia: number | null;
  /** "faltavam N dias" (negativo = o evento já foi). */
  faltamDias: number | null;
  semPix: boolean;
  /** A multa já lançada (só depois do ato): a linha fica só leitura. */
  jaLancada?: number | null;
  /** Depois do ato: o Casting já tirou o artista da vaga (a multa continua cabendo). */
  foraDaVaga?: boolean;
  /** O artista que a tela mostrou (vai junto da multa no ato). */
  talentId?: number | null;
  /** No ato: o artista tem e-mail cadastrado (recebe o e-mail de cancelamento). */
  comEmail?: boolean;
}

interface MultaAoElencoBlocoProps {
  linhas: LinhaDeMulta[];
  valores: Record<number, number>;
  onValor: (chave: number, valor: number) => void;
  /** Os erros por `multa_<chave>` do servidor. */
  erros: Record<string, string>;
  titulo?: string;
}

/**
 * "Multa ao elenco" (feature 306, FR-070–FR-072): uma linha por escalação com artista, vaga e dia,
 * o cachê de referência e quantos dias faltavam. Vazio ou zero é "sem multa". Cada multa vira um
 * Gasto Extra aprovado, a pagar ao artista (pelo PIX do cadastro). Nenhuma conta aqui.
 */
export function MultaAoElencoBloco({ linhas, valores, onValor, erros, titulo = "Multa ao elenco (opcional)" }: MultaAoElencoBlocoProps) {
  if (linhas.length === 0) return null;
  return (
    <fieldset className="rounded-md border border-line p-3">
      <legend className="px-1 text-xs font-semibold uppercase text-muted">{titulo}</legend>
      <p className="mb-2 text-xs text-muted">
        Deixe vazio para não lançar multa. Cada multa vira um Gasto Extra a pagar ao artista.
      </p>
      <ul className="space-y-2">
        {linhas.map((l) => {
          const erro = erros[`multa_${l.chave}`];
          return (
            <li key={l.chave} className="rounded-md border border-line p-2 text-sm">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-semibold text-ink">{l.artista ?? "—"}</span>
                {l.foraDaVaga && (
                  <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[11px] font-semibold text-muted">
                    saiu da escala
                  </span>
                )}
                <span className="text-muted">
                  {l.vaga}
                  {l.dia ? ` · ${diaMes(l.dia)}` : ""}
                </span>
                {l.cacheReferencia != null && (
                  <span className="text-xs text-muted">cachê {brl(l.cacheReferencia)}</span>
                )}
                {l.faltamDias != null && (
                  <span className="text-xs text-muted">
                    {l.faltamDias >= 0 ? `faltavam ${l.faltamDias} dia(s)` : `foi há ${-l.faltamDias} dia(s)`}
                  </span>
                )}
              </div>
              {l.jaLancada != null ? (
                <p className="mt-1 text-xs text-ink">Multa lançada: {brl(l.jaLancada)} (corrija em Gastos Extras).</p>
              ) : (
                <div className="mt-1 max-w-[12rem]">
                  <MoneyInput
                    className={FIELD}
                    value={valores[l.chave] ?? 0}
                    onValueChange={(v) => onValor(l.chave, v)}
                    aria-label={`Multa para ${l.artista ?? "o artista"} (${l.vaga})`}
                    aria-invalid={Boolean(erro)}
                  />
                </div>
              )}
              {l.semPix && l.jaLancada == null && (
                <p className="mt-1 text-xs text-gold-ink">Sem PIX no cadastro: a multa vai à Planilha sem chave.</p>
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
