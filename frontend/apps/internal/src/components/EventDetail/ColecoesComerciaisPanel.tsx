import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Badge, Button } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";
import { useSetAcrescimos, type AcrescimoInput } from "../../lib/eventOps";
import { DataRow, Empty, INPUT_CLASS, Panel } from "./parts";

const LABEL = "mb-1 block text-[11px] font-bold uppercase tracking-wider text-muted";

/** Tipo de acréscimo que é repasse a terceiro — o único que carrega recebedor e chave PIX. */
const TIPO_BV = "BV";

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

function dataCurta(iso: string | null): string {
  if (!iso) return "—";
  // A data vem "YYYY-MM-DD" e é dia de calendário: fatiar evita o deslocamento de fuso que
  // `new Date(...)` introduziria.
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

interface Linha extends AcrescimoInput {
  /** Chave só de renderização — o servidor recria as linhas a cada PUT, então id não sobrevive. */
  key: string;
}

/**
 * Acréscimos do evento, editáveis (features 099/100; editor na 253).
 *
 * Até aqui só o formulário Jinja escrevia isto. O BV é dinheiro que sai para outra pessoa, então a
 * tela mostra o recebedor e o status de pagamento — que o servidor **preserva** entre salvamentos,
 * mesmo apagando e recriando as linhas.
 */
function AcrescimosPanel({ data }: { data: EventoDetalhe }) {
  const acrescimos = data.acrescimos ?? [];
  const salvar = useSetAcrescimos(data.event.id);
  const canEdit = Boolean(data.flags.show_comercial) && !data.event.is_satellite;
  const [editando, setEditando] = useState(false);
  const [linhas, setLinhas] = useState<Linha[]>([]);

  function abrir() {
    setLinhas(
      acrescimos.map((a, i) => ({
        key: `k${i}`,
        tipo: a.tipo,
        is_percent: a.is_percent,
        value: String(a.value ?? ""),
        bv_recipient: a.bv_recipient ?? "",
        bv_pix: "",
      })),
    );
    setEditando(true);
  }

  function alterar(key: string, campo: keyof AcrescimoInput, valor: unknown) {
    setLinhas((atual) => atual.map((l) => (l.key === key ? { ...l, [campo]: valor } : l)));
  }

  const total = acrescimos.reduce((s, a) => s + (a.amount_brl ?? 0), 0);

  if (editando) {
    return (
      <Panel title="Acréscimos">
        <div className="space-y-3">
          {linhas.map((l) => (
            <div key={l.key} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-end gap-2">
                <div className="min-w-[9rem] flex-1">
                  <label className={LABEL}>Tipo</label>
                  <input
                    className={INPUT_CLASS}
                    value={l.tipo}
                    onChange={(e) => alterar(l.key, "tipo", e.target.value)}
                    placeholder="Ex.: BV, Taxa, Hora extra"
                  />
                </div>
                <div className="w-32">
                  <label className={LABEL}>{l.is_percent ? "Percentual" : "Valor (R$)"}</label>
                  <input
                    className={INPUT_CLASS}
                    inputMode="decimal"
                    value={String(l.value ?? "")}
                    onChange={(e) => alterar(l.key, "value", e.target.value)}
                    placeholder={l.is_percent ? "10" : "150.00"}
                  />
                </div>
                <label className="mb-2 flex cursor-pointer items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(l.is_percent)}
                    onChange={(e) => alterar(l.key, "is_percent", e.target.checked)}
                  />
                  % da venda
                </label>
                <Button
                  variant="outline"
                  size="sm"
                  className="mb-1"
                  onClick={() => setLinhas((a) => a.filter((x) => x.key !== l.key))}
                  aria-label={`Remover acréscimo ${l.tipo || "sem tipo"}`}
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              </div>
              {l.tipo === TIPO_BV && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <div className="min-w-[10rem] flex-1">
                    <label className={LABEL}>Quem recebe</label>
                    <input
                      className={INPUT_CLASS}
                      value={l.bv_recipient ?? ""}
                      onChange={(e) => alterar(l.key, "bv_recipient", e.target.value)}
                    />
                  </div>
                  <div className="min-w-[10rem] flex-1">
                    <label className={LABEL}>Chave PIX</label>
                    <input
                      className={INPUT_CLASS}
                      value={l.bv_pix ?? ""}
                      onChange={(e) => alterar(l.key, "bv_pix", e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}

          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setLinhas((a) => [
                ...a,
                { key: `n${Date.now()}`, tipo: "", value: "", is_percent: false, bv_recipient: "", bv_pix: "" },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            Adicionar acréscimo
          </Button>

          <p className="text-xs text-muted">
            Percentual é congelado em reais no momento de salvar, sobre a venda atual. Um BV que já
            foi pago continua marcado como pago.
          </p>

          {salvar.isError && <p className="text-sm text-red">{salvar.error?.message}</p>}

          <div className="flex gap-2">
            <Button
              loading={salvar.isPending}
              onClick={() =>
                salvar.mutate(
                  linhas.map(({ key: _key, ...resto }) => resto),
                  { onSuccess: () => setEditando(false) },
                )
              }
            >
              Salvar
            </Button>
            <Button variant="outline" onClick={() => setEditando(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel
      title="Acréscimos"
      actions={
        canEdit ? (
          <Button variant="outline" size="sm" onClick={abrir}>
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Editar
          </Button>
        ) : null
      }
    >
      {acrescimos.length === 0 ? (
        <Empty>Nenhum acréscimo.</Empty>
      ) : (
        <div className="divide-y divide-line">
          {acrescimos.map((a) => (
            <DataRow key={a.id} label={a.label}>
              <span className="flex items-center justify-end gap-2">
                {a.is_bv && (
                  <Badge tone={a.bv_payment_status === "pago" ? "green" : "gold"}>
                    {a.bv_payment_status === "pago" ? "BV pago" : "BV a pagar"}
                    {a.bv_recipient ? ` · ${a.bv_recipient}` : ""}
                  </Badge>
                )}
                {brl(a.amount_brl)}
              </span>
            </DataRow>
          ))}
          <DataRow label="Total">
            <strong>{brl(total)}</strong>
          </DataRow>
        </div>
      )}
    </Panel>
  );
}

/**
 * Cronograma de parcelas — leitura.
 *
 * Só parcelas: nota fiscal já tem painel próprio no `FinanceiroSection`, e duplicar deixava dois
 * blocos iguais na mesma tela. O cronograma, esse sim, não aparecia em lugar nenhum da plataforma
 * nova — entrava no cálculo do KPI e nunca era exibido.
 *
 * `received` é marcado pela planilha de pagamentos; aqui é só informação.
 */
function ParcelasPanel({ data }: { data: EventoDetalhe }) {
  const parcelas = data.parcelas ?? [];
  if (parcelas.length === 0) return null;

  const total = parcelas.reduce((s, p) => s + (p.amount ?? 0), 0);
  return (
    <Panel title="Parcelas">
      <div className="divide-y divide-line">
        {parcelas.map((p) => (
          <DataRow key={p.id} label={dataCurta(p.due_date)}>
            <span className="flex items-center justify-end gap-2">
              {p.received && <Badge tone="green">Recebida</Badge>}
              {brl(p.amount)}
            </span>
          </DataRow>
        ))}
        <DataRow label="Total das parcelas">
          <strong>{brl(total)}</strong>
        </DataRow>
      </div>
    </Panel>
  );
}

export interface ColecoesComerciaisPanelProps {
  data: EventoDetalhe;
}

/**
 * As coleções que penduram no valor da venda: acréscimos (editáveis) e parcelas (leitura).
 *
 * Nenhuma das duas era escrita pela plataforma nova — só pelo formulário Jinja, que a fase 6
 * apaga. Acréscimo vem primeiro porque é o que altera a base da comissão.
 *
 * Nota fiscal ficou de fora de propósito: já tem painel no `FinanceiroSection`, e a API dela
 * (`PATCH`/`DELETE` por id, feature 252) é o que falta ligar por lá.
 */
export function ColecoesComerciaisPanel({ data }: ColecoesComerciaisPanelProps) {
  if (!data.venda) return null;
  return (
    <>
      <AcrescimosPanel data={data} />
      <ParcelasPanel data={data} />
    </>
  );
}
