import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, CardHeader, CardTitle, ConfirmDialog } from "@manto/ui";
import { diaParaApi, diaParaTela, type FaixaEspecial } from "../../lib/orcamento";
import { INPUT_PRECOS, PriceTable } from "./PriceTable";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const NOTA_FAIXA_MAX = 200;
const ROTULO_FAIXA_MAX = 60;

/** Rótulo legível de cada campo da faixa, para a lista de erros não mostrar chave técnica. */
function rotuloDoCampo(campo: string): string {
  if (campo === "markup") return "Markup";
  if (campo === "coordenador") return "Coordenador";
  if (campo === "piso") return "Cachê mínimo";
  if (campo.startsWith("cache.")) return `Cachê próprio — ${campo.slice("cache.".length)}`;
  return campo;
}

/**
 * Feature 307 — uma faixa de data especial da tabela de preços (ex.: "Véspera e Natal", 24 e 25/12).
 * A calculadora resolve pela data do evento; aqui o superadmin mexe em dias, markup, cachês, piso e
 * nota sem deploy. `erros` são os `fields` do 400 (`datas_especiais.<chave>.<campo>`): o campo
 * errado ganha destaque e o foco (Princípio V) — inclusive as linhas da tabela.
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
  const [erroDiaLocal, setErroDiaLocal] = useState<string | null>(null);
  const [remocaoCache, setRemocaoCache] = useState<string | null>(null);
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
    if (!mmdd) {
      setErroDiaLocal("Dia inválido — use DD/MM");
      return;
    }
    if (faixa.dias.includes(mmdd)) {
      setErroDiaLocal(`${diaParaTela(mmdd)} já está na lista`);
      return;
    }
    setErroDiaLocal(null);
    set({ dias: [...faixa.dias, mmdd] });
    setNovoDia("");
  };
  const erroDias = erro("dias") ?? erroDiaLocal;
  const transicao = reduzir ? { duration: 0 } : { duration: 0.18 };

  return (
    <Card ref={raiz}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{faixa.rotulo || "Data especial"}</CardTitle>
        <p className="text-xs text-muted">
          Quando o evento cai num destes dias, a calculadora troca o markup e o cachê do coordenador
          pelos desta tabela. Personagem com cachê próprio usa o valor dele; os demais sobem até o
          cachê mínimo. Sem nenhum dia na lista, a data especial fica desligada.
        </p>
      </CardHeader>
      <CardContent className="space-y-4 p-0">
        <div className="grid gap-4 px-5 sm:grid-cols-2">
          <div>
            <label htmlFor={`faixa-${chave}-nome`} className={LABEL}>
              Nome
            </label>
            <input
              id={`faixa-${chave}-nome`}
              className={classeDe("rotulo")}
              aria-invalid={erro("rotulo") ? true : undefined}
              value={faixa.rotulo}
              maxLength={ROTULO_FAIXA_MAX}
              onChange={(e) => set({ rotulo: e.target.value })}
            />
            {erro("rotulo") && <p className="mt-1 text-xs text-red">{erro("rotulo")}</p>}
          </div>
          <div>
            <label htmlFor={`faixa-${chave}-dia`} className={LABEL}>
              Dias (DD/MM, repetem todo ano)
            </label>
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
                id={`faixa-${chave}-dia`}
                className={`${INPUT_PRECOS} w-24${erroDias ? " border-red ring-1 ring-red" : ""}`}
                aria-invalid={erroDias ? true : undefined}
                placeholder="26/12"
                value={novoDia}
                onChange={(e) => {
                  setNovoDia(e.target.value);
                  setErroDiaLocal(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") adicionarDia();
                }}
              />
              <Button size="sm" variant="outline" onClick={adicionarDia}>
                Adicionar dia
              </Button>
            </div>
            {erroDias && <p className="mt-1 text-xs text-red">{erroDias}</p>}
          </div>
        </div>
        {errosDaTabela.length > 0 && (
          <ul className="px-5 text-xs text-red" role="alert">
            {errosDaTabela.map(([campo, msg]) => (
              <li key={campo}>
                {rotuloDoCampo(campo)}: {msg}
              </li>
            ))}
          </ul>
        )}
        <PriceTable
          rows={[
            {
              label: "Markup",
              hint: "Vale para receptivo e show",
              values: faixa.markup,
              onChange: (v) => set({ markup: v }),
              invalid: !!erro("markup"),
            },
            {
              label: "Coordenador",
              hint: "Com ou sem show",
              values: faixa.coordenador,
              onChange: (v) => set({ coordenador: v }),
              invalid: !!erro("coordenador"),
            },
            {
              label: "Cachê mínimo",
              hint: "Ator, cantor ou especial sem cachê próprio sobe até este valor",
              values: faixa.piso,
              onChange: (v) => set({ piso: v }),
              invalid: !!erro("piso"),
            },
            ...Object.entries(faixa.cache).map(([nome, values]) => ({
              label: nome,
              hint: "Cachê próprio nesta data",
              key: `cache-${nome}`,
              acao: (
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Tirar o cachê próprio de ${nome}`}
                  onClick={() => setRemocaoCache(nome)}
                >
                  Tirar
                </Button>
              ),
              values,
              onChange: (v: number[]) => set({ cache: { ...faixa.cache, [nome]: v } }),
              invalid: !!erro(`cache.${nome}`),
            })),
          ]}
        />
        {/* Sobrescritas como chips, não select nativo: a lista de especiais passa de 10 (XII.1). */}
        <div className="px-5">
          {semSobrescrita.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted">Dar cachê próprio a:</span>
              {semSobrescrita.map((nome) => (
                <Button
                  key={nome}
                  size="sm"
                  variant="outline"
                  // Nasce no piso, nunca zerado: o servidor recusa sobrescrita com zero (cachê zero no Natal).
                  onClick={() => set({ cache: { ...faixa.cache, [nome]: [...faixa.piso] } })}
                >
                  + {nome}
                </Button>
              ))}
            </div>
          )}
        </div>
        <div className="px-5 pb-5">
          <label htmlFor={`faixa-${chave}-nota`} className={LABEL}>
            Aviso na mensagem e no PDF do orçamento (uma linha, até {NOTA_FAIXA_MAX} caracteres)
          </label>
          <input
            id={`faixa-${chave}-nota`}
            className={classeDe("nota_mensagem")}
            aria-invalid={erro("nota_mensagem") ? true : undefined}
            maxLength={NOTA_FAIXA_MAX}
            value={faixa.nota_mensagem}
            onChange={(e) => set({ nota_mensagem: e.target.value })}
          />
          {erro("nota_mensagem") && <p className="mt-1 text-xs text-red">{erro("nota_mensagem")}</p>}
        </div>
      </CardContent>

      <ConfirmDialog
        open={remocaoCache != null}
        title="Tirar cachê próprio"
        description={`Tirar o cachê próprio de "${remocaoCache ?? ""}" em ${faixa.rotulo}? Nesta data ele passa a usar o cachê mínimo. Vale ao clicar em "Salvar configurações".`}
        confirmLabel="Tirar cachê próprio"
        destructive
        pending={false}
        onConfirm={() => {
          // Sem a sobrescrita o especial cai para o piso: no Noel, de 5.010 para 3.841.
          if (!remocaoCache) return;
          const { [remocaoCache]: _removido, ...rest } = faixa.cache;
          set({ cache: rest });
          setRemocaoCache(null);
        }}
        onOpenChange={(aberto) => {
          if (!aberto) setRemocaoCache(null);
        }}
      />
    </Card>
  );
}
