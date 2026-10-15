import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import type { FaixaEspecial } from "../../lib/orcamento";
import { INPUT_PRECOS, PriceTable } from "./PriceTable";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const NOTA_FAIXA_MAX = 200;
const ROTULO_FAIXA_MAX = 60;

/** "MM-DD" (como a tabela guarda) → "DD/MM" (como o time lê). */
export const diaParaTela = (mmdd: string) => `${mmdd.slice(3, 5)}/${mmdd.slice(0, 2)}`;

/** "DD/MM" digitado → "MM-DD" da tabela; `null` se não for um dia. O servidor valida de novo. */
export function diaParaApi(texto: string): string | null {
  const m = /^(\d{2})\/(\d{2})$/.exec(texto.trim());
  if (!m) return null;
  const dia = Number(m[1]);
  const mes = Number(m[2]);
  if (mes < 1 || mes > 12 || dia < 1 || dia > 31) return null;
  return `${m[2]}-${m[1]}`;
}

/**
 * Feature 307 — uma faixa de data especial da tabela de preços (ex.: "Véspera e Natal", 24 e 25/12).
 * A calculadora resolve pela data do evento; aqui o superadmin mexe em dias, markup, cachês, piso e
 * nota sem deploy. `erros` são os `fields` do 400 (`datas_especiais.<chave>.<campo>`): o campo
 * errado ganha destaque e o foco (Princípio V).
 */
export function DatasEspeciaisCard({
  chave,
  faixa,
  especiais,
  erros,
  onChange,
}: {
  chave: string;
  faixa: FaixaEspecial;
  especiais: string[];
  erros: Record<string, string>;
  onChange: (nova: FaixaEspecial) => void;
}) {
  const reduzir = useReducedMotion();
  const raiz = useRef<HTMLDivElement>(null);
  const [novoDia, setNovoDia] = useState("");
  const erro = (campo: string) => erros[`datas_especiais.${chave}.${campo}`];
  const classeDe = (campo: string) =>
    `${INPUT_PRECOS}${erro(campo) ? " border-red ring-1 ring-red" : ""}`;
  const errosDaTabela = Object.entries(erros)
    .filter(([k]) => k.startsWith(`datas_especiais.${chave}.`))
    .map(([k, msg]) => [k.replace(`datas_especiais.${chave}.`, ""), msg] as const)
    .filter(([campo]) => !["rotulo", "dias", "nota_mensagem"].includes(campo));

  // O primeiro campo inválido recebe o foco quando o servidor recusa (não basta mostrar texto).
  useEffect(() => {
    const alvo = raiz.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
    alvo?.focus();
  }, [erros]);

  const set = (patch: Partial<FaixaEspecial>) => onChange({ ...faixa, ...patch });
  const semSobrescrita = especiais.filter((n) => !(n in faixa.cache));
  const adicionarDia = () => {
    const mmdd = diaParaApi(novoDia);
    if (!mmdd || faixa.dias.includes(mmdd)) return;
    set({ dias: [...faixa.dias, mmdd] });
    setNovoDia("");
  };
  const transicao = reduzir ? { duration: 0 } : { duration: 0.18 };

  return (
    <Card ref={raiz}>
      <CardHeader>
        <CardTitle>Datas especiais — {faixa.rotulo}</CardTitle>
        <p className="text-xs text-muted">
          Quando a data do evento cai num destes dias, a calculadora usa este markup e estes cachês
          para qualquer orçamento; quem não tem cachê próprio sobe ao piso. Sem dias, a faixa fica
          desligada.
        </p>
      </CardHeader>
      <CardContent className="space-y-3 p-0">
        <div className="grid gap-3 p-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Rótulo</label>
            <input
              className={classeDe("rotulo")}
              aria-invalid={erro("rotulo") ? true : undefined}
              value={faixa.rotulo}
              maxLength={ROTULO_FAIXA_MAX}
              onChange={(e) => set({ rotulo: e.target.value })}
            />
            {erro("rotulo") && <p className="mt-1 text-xs text-red">{erro("rotulo")}</p>}
          </div>
          <div>
            <label className={LABEL}>Dias (DD/MM, valem todo ano)</label>
            <div className="flex flex-wrap items-center gap-2">
              <AnimatePresence initial={false}>
                {faixa.dias.map((d) => (
                  <motion.span
                    key={d}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={transicao}
                    className="flex items-center gap-1 rounded-md bg-surface-2 px-2 py-1 text-xs text-ink"
                  >
                    {diaParaTela(d)}
                    <button
                      type="button"
                      className="text-muted hover:text-red"
                      aria-label={`Remover ${diaParaTela(d)}`}
                      onClick={() => set({ dias: faixa.dias.filter((x) => x !== d) })}
                    >
                      ×
                    </button>
                  </motion.span>
                ))}
              </AnimatePresence>
              <input
                className={`${classeDe("dias")} w-24`}
                aria-invalid={erro("dias") ? true : undefined}
                placeholder="26/12"
                value={novoDia}
                onChange={(e) => setNovoDia(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") adicionarDia();
                }}
              />
              <Button size="sm" variant="outline" onClick={adicionarDia}>
                Adicionar
              </Button>
            </div>
            {erro("dias") && <p className="mt-1 text-xs text-red">{erro("dias")}</p>}
          </div>
        </div>
        {errosDaTabela.length > 0 && (
          <ul className="px-3 text-xs text-red" role="alert">
            {errosDaTabela.map(([campo, msg]) => (
              <li key={campo}>
                {campo}: {msg}
              </li>
            ))}
          </ul>
        )}
        <PriceTable
          rows={[
            { label: "Markup (coeficiente)", values: faixa.markup, onChange: (v) => set({ markup: v }) },
            {
              label: "Coordenador (com e sem show)",
              values: faixa.coordenador,
              onChange: (v) => set({ coordenador: v }),
            },
            { label: "Piso dos demais personagens", values: faixa.piso, onChange: (v) => set({ piso: v }) },
            ...Object.entries(faixa.cache).map(([nome, values]) => ({
              label: `Cachê — ${nome}`,
              values,
              onChange: (v: number[]) => set({ cache: { ...faixa.cache, [nome]: v } }),
            })),
          ]}
        />
        {/* Sobrescritas como chips, não select nativo: a lista de especiais passa de 10 (XII.1). */}
        <div className="flex flex-wrap items-center gap-2 px-3">
          {Object.keys(faixa.cache).map((nome) => (
            <Button
              key={nome}
              size="sm"
              variant="ghost"
              onClick={() => {
                const { [nome]: _removido, ...rest } = faixa.cache;
                set({ cache: rest });
              }}
            >
              × {nome}
            </Button>
          ))}
          {semSobrescrita.length > 0 && <span className="text-xs text-muted">Sobrescrever cachê de:</span>}
          {semSobrescrita.map((nome) => (
            <Button
              key={nome}
              size="sm"
              variant="outline"
              onClick={() => set({ cache: { ...faixa.cache, [nome]: [0, 0, 0, 0] } })}
            >
              + {nome}
            </Button>
          ))}
        </div>
        <div className="p-3">
          <label className={LABEL}>Nota na mensagem e no PDF (até {NOTA_FAIXA_MAX} caracteres)</label>
          <textarea
            className={`${classeDe("nota_mensagem")} h-16 py-1`}
            aria-invalid={erro("nota_mensagem") ? true : undefined}
            maxLength={NOTA_FAIXA_MAX}
            value={faixa.nota_mensagem}
            onChange={(e) => set({ nota_mensagem: e.target.value })}
          />
          {erro("nota_mensagem") && <p className="mt-1 text-xs text-red">{erro("nota_mensagem")}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
