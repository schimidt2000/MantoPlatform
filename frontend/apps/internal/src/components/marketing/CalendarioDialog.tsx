import { useEffect, useRef, useState } from "react";
import { Badge, Button, Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, Input } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { MoneyInput, formatBRL } from "@manto/money";
import {
  NOMES_DOS_MESES,
  useCalendario,
  useSalvarCalendario,
  type CalendarioFrente,
  type CalendarioMes,
} from "../../lib/marketing";

const SELECT = "h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink";
const CAMPO_DINHEIRO =
  "h-10 w-full rounded-md border border-line bg-panel px-2 text-right text-sm text-ink tabular-nums";

function padrao(frente: CalendarioFrente | undefined): string {
  if (!frente) return "";
  const meta = frente.meta_vendas_mes != null ? `${frente.meta_vendas_mes} vendas` : "sem meta";
  const verba = frente.verba_mes ? `R$ ${formatBRL(Number(frente.verba_mes))}` : "sem verba";
  return `Padrão da frente: ${meta} · ${verba} por mês. Mês em branco usa o padrão.`;
}

function LinhaDoMes({
  mes,
  atual,
  editavel,
  erros,
  onChange,
}: {
  mes: CalendarioMes;
  atual: boolean;
  editavel: boolean;
  erros: Record<string, string>;
  onChange: (proximo: CalendarioMes) => void;
}) {
  const indice = mes.mes - 1;
  return (
    <li
      data-mes-atual={atual || undefined}
      className={`space-y-1.5 rounded-md border px-3 py-2.5 ${atual ? "border-accent/60 bg-accent/5" : "border-line"}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-ink">{NOMES_DOS_MESES[indice]}</span>
        {atual && <Badge tone="accent">Este mês</Badge>}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="block text-[11px] font-medium text-muted">
          Meta de vendas
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            disabled={!editavel}
            className="mt-0.5 h-10 text-right tabular-nums"
            value={mes.meta_vendas ?? ""}
            aria-invalid={Boolean(erros[`meses.${indice}.meta_vendas`])}
            onChange={(e) => onChange({ ...mes, meta_vendas: e.target.value === "" ? null : Number(e.target.value) })}
          />
        </label>
        <label className="block text-[11px] font-medium text-muted">
          Verba (R$)
          <MoneyInput
            disabled={!editavel}
            className={`mt-0.5 ${CAMPO_DINHEIRO}`}
            value={mes.verba ? Number(mes.verba) : 0}
            onValueChange={(v) => onChange({ ...mes, verba: v > 0 ? v.toFixed(2) : null })}
          />
        </label>
      </div>
      <label className="block text-[11px] font-medium text-muted">
        Foco do mês
        <textarea
          disabled={!editavel}
          rows={2}
          maxLength={500}
          className="mt-0.5 w-full rounded-md border border-line bg-panel px-2 py-1.5 text-sm text-ink"
          value={mes.foco ?? ""}
          onChange={(e) => onChange({ ...mes, foco: e.target.value || null })}
        />
      </label>
      {Object.entries(erros)
        .filter(([chave]) => chave.startsWith(`meses.${indice}.`))
        .map(([chave, texto]) => (
          <p key={chave} className="text-xs text-red" role="alert">
            {texto}
          </p>
        ))}
    </li>
  );
}

/**
 * Calendário do ano por frente (feature 351): meta, verba e foco de cada mês.
 *
 * Era prosa na skill da rotina; virou dado que a rotina lê toda segunda e que o card da frente mostra
 * no mês corrente. Uma frente por vez (5 opções num `<select>` nativo); os 12 meses empilham em 390 px.
 */
export function CalendarioDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const calendario = useCalendario(open);
  const salvar = useSalvarCalendario();
  const [frente, setFrente] = useState("festas");
  const [meses, setMeses] = useState<CalendarioMes[]>([]);
  const [salvo, setSalvo] = useState(false);
  const atual = calendario.data?.frentes.find((f) => f.slug === frente);

  const lista = useRef<HTMLUListElement>(null);

  // Os dados salvos (ou de outra frente) substituem o rascunho; o aviso de "salvo" some só ao trocar de frente.
  useEffect(() => {
    setMeses(atual ? atual.meses.map((m) => ({ ...m })) : []);
  }, [atual]);

  // Abre no mês corrente: é ele que importa hoje, e em 390 px novembro fica a onze cartões de distância.
  useEffect(() => {
    if (!meses.length) return;
    lista.current?.querySelector("[data-mes-atual]")?.scrollIntoView({ block: "nearest" });
  }, [frente, meses.length]);

  const erros = salvar.error instanceof ApiRequestError ? salvar.error.fields ?? {} : {};
  const erro =
    salvar.error instanceof ApiRequestError ? salvar.error.message : salvar.error ? "Não foi possível salvar. Tente novamente." : null;
  const editavel = Boolean(calendario.data?.pode_editar);

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Calendário do ano</DialogTitle>
          <DialogDescription>
            O que vender e prospectar em cada mês, com a meta e a verba do mês. A rotina de segunda lê este calendário.
          </DialogDescription>
        </DialogHeader>

        {calendario.isLoading && <p className="text-sm text-muted">Carregando…</p>}
        {calendario.isError && (
          <p className="text-sm text-red" role="alert">
            Não foi possível carregar o calendário. Tente novamente.
          </p>
        )}

        {calendario.data && (
          <div className="space-y-3">
            <label className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
              Frente
              <select aria-label="Frente do calendário" className={SELECT} value={frente} onChange={(e) => {
                  setFrente(e.target.value);
                  setSalvo(false);
                }}>
                {calendario.data.frentes.map((f) => (
                  <option key={f.slug} value={f.slug}>
                    {f.nome}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs text-muted">{padrao(atual)}</p>
            <ul ref={lista} className="max-h-[55vh] space-y-2 overflow-y-auto pr-1">
              {meses.map((m, i) => (
                <LinhaDoMes
                  key={m.mes}
                  mes={m}
                  atual={m.mes === calendario.data.mes_corrente}
                  editavel={editavel}
                  erros={erros}
                  onChange={(proximo) => setMeses((todos) => todos.map((x, j) => (j === i ? proximo : x)))}
                />
              ))}
            </ul>
            <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
              {erro && (
                <span className="mr-auto text-sm text-red" role="alert">
                  {erro}
                </span>
              )}
              {salvo && !erro && <span className="mr-auto text-sm text-green">Calendário salvo.</span>}
              {!editavel && <span className="mr-auto text-sm text-muted">Só o Superadmin altera o calendário.</span>}
              <Button type="button" variant="outline" onClick={onClose}>
                Fechar
              </Button>
              {editavel && (
                <Button
                  type="button"
                  disabled={salvar.isPending}
                  onClick={() => salvar.mutate({ frente, meses }, { onSuccess: () => setSalvo(true) })}
                >
                  {salvar.isPending ? "Salvando…" : "Salvar"}
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
