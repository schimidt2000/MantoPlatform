import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Badge, Button } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";
import { useSetAcrescimos, type AcrescimoInput } from "../../lib/eventOps";
import { AlertaBvDoOrcamento } from "./AlertaBvDoOrcamento";
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
  /** Chave só de renderização. O `id` (quando há) é o da linha gravada — vai ao servidor. */
  key: string;
}

/** Os BVs como estão gravados — para saber se a venda mudou o BV com o editor aberto (B10). */
function retratoDosBvs(acrescimos: EventoDetalhe["acrescimos"]): string {
  return JSON.stringify((acrescimos ?? []).filter((a) => a.is_bv).map((a) => [a.id, a.amount_brl]));
}

/**
 * O % digitado ("10,5") como número; texto que não é número segue como está, para o servidor
 * recusar NA LINHA (nunca vira outro número calado). Vazio fica vazio.
 */
function percentualDigitado(v: number | string | null | undefined): number | string {
  if (typeof v === "number") return v;
  const texto = (v ?? "").replace(/\s/g, "");
  if (texto === "") return "";
  const n = Number(texto.includes(",") ? texto.replace(/\./g, "").replace(",", ".") : texto);
  return Number.isFinite(n) ? n : texto;
}

function semValor(v: number | string | null | undefined): boolean {
  return v == null || v === "" || v === 0;
}

/**
 * Acréscimos do evento, editáveis (features 099/100; editor na 253; BV da 305).
 *
 * O BV é dinheiro que sai para outra pessoa: a tela mostra quem recebe e o status, e o servidor
 * preserva o PIX e o pagamento pela IDENTIDADE da linha (o `id` que veio do GET) — salvar sem mexer
 * não apaga o PIX nem "despaga" ninguém. BV pago não muda de valor nem sai por aqui. O valor em R$ é
 * `MoneyInput` e vai como NÚMERO: texto livre fazia "1.500" virar R$ 1,50 no servidor, e o backend
 * antigo (janela de deploy) descartava "130,95" com a linha inteira. O % vai como número também.
 */
function AcrescimosPanel({ data }: { data: EventoDetalhe }) {
  const acrescimos = data.acrescimos ?? [];
  const salvar = useSetAcrescimos(data.event.id);
  const canEdit = Boolean(data.flags.show_comercial) && !data.event.is_satellite;
  const pendente = data.venda?.bv_do_orcamento_pendente ?? null;
  const [searchParams, setSearchParams] = useSearchParams();
  const [editando, setEditando] = useState(false);
  const [linhas, setLinhas] = useState<Linha[]>([]);
  const [retrato, setRetrato] = useState("");

  function linhasGravadas(): Linha[] {
    return acrescimos.map((a, i) => {
      const linha: Linha = {
        key: `k${i}`,
        id: a.id,
        tipo: a.tipo,
        is_percent: a.is_percent,
        value: a.is_percent ? (a.value == null ? "" : String(a.value).replace(".", ",")) : (a.value ?? 0),
        bv_recipient: a.bv_recipient ?? "",
        bv_pix: a.bv_pix ?? "",
      };
      // Com o backend antigo a chave não vem: fica de fora, e o servidor mantém a descrição.
      if (a.descricao !== undefined) linha.descricao = a.descricao ?? "";
      return linha;
    });
  }

  /**
   * A linha do "Lançar o BV": SEMPRE em reais, com o valor que o servidor propôs. Sem valor (duração
   * não identificada) vai vazia, para digitar — em % a régua do evento põe os outros acréscimos na
   * base e daria outro BV (no 2407, 4× o do orçamento); e o BV fixo do orçamento abria como %.
   */
  function linhaDoBvPendente(): Linha {
    return {
      key: `n${Date.now()}`,
      tipo: TIPO_BV,
      is_percent: false,
      value: pendente?.valor ?? 0,
      bv_recipient: "",
      bv_pix: "",
    };
  }

  function abrir(comBv = false) {
    salvar.reset();
    const base = linhasGravadas();
    if (comBv && pendente) base.push(linhaDoBvPendente());
    setLinhas(base);
    setRetrato(retratoDosBvs(acrescimos));
    setEditando(true);
  }

  // "Lançar o BV" vindo de outra tela (`?lancar=bv`): o painel já está montado, então o pedido é
  // lido aqui (e apagado da URL, para recarregar a página não reabrir o editor). Com o editor JÁ
  // aberto, só acrescenta a linha (se ainda não houver um BV novo): reabrir perderia o digitado.
  const pedeLancar = searchParams.get("lancar") === "bv";
  useEffect(() => {
    if (!pedeLancar || !canEdit) return;
    if (editando) {
      if (pendente) {
        setLinhas((atual) =>
          atual.some((l) => l.id == null && l.tipo.trim().toUpperCase() === TIPO_BV)
            ? atual
            : [...atual, linhaDoBvPendente()],
        );
      }
    } else {
      abrir(true);
    }
    const proximo = new URLSearchParams(searchParams);
    proximo.delete("lancar");
    setSearchParams(proximo, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedeLancar, canEdit]);

  function alterar(key: string, campo: keyof AcrescimoInput, valor: unknown) {
    setLinhas((atual) =>
      atual.map((l) => {
        if (l.key !== key) return l;
        const nova = { ...l, [campo]: valor };
        // Linha NOVA que vira BV nasce em % (o BV lançado à mão costuma ser "10%"), mas só se ainda
        // não tem valor: com "300" digitado, virar % gravaria 300% (R$ 1.500 numa venda de 2.000).
        if (
          campo === "tipo" &&
          l.id == null &&
          semValor(l.value) &&
          String(valor).trim().toUpperCase() === TIPO_BV &&
          l.tipo.trim().toUpperCase() !== TIPO_BV
        ) {
          nova.is_percent = true;
          nova.value = "";
        }
        // Trocar a unidade leva o número junto: o R$ é número (MoneyInput); o % é texto.
        if (campo === "is_percent" && Boolean(valor) !== Boolean(l.is_percent)) {
          const numero = percentualDigitado(l.value);
          nova.value = valor
            ? typeof numero === "number" && numero !== 0
              ? String(numero).replace(".", ",")
              : ""
            : typeof numero === "number"
              ? numero
              : 0;
        }
        return nova;
      }),
    );
  }

  const total = acrescimos.reduce((s, a) => s + (a.amount_brl ?? 0), 0);
  const campos = salvar.error instanceof ApiRequestError ? (salvar.error.fields ?? {}) : {};
  const erroDaLinha = (i: number, campo: string) => campos[`items.${i}.${campo}`];
  const vendaMudouOBv = editando && retrato !== retratoDosBvs(acrescimos);

  if (editando) {
    return (
      <Panel title="Acréscimos">
        <div className="space-y-3">
          {vendaMudouOBv && (
            <p role="alert" className="rounded-md bg-gold-soft p-2 text-sm text-ink">
              A venda mudou e o BV foi recalculado enquanto este editor estava aberto. Cancele e
              abra de novo para não gravar o valor antigo.
            </p>
          )}
          {linhas.map((l, i) => {
            const ehBv = l.tipo.trim().toUpperCase() === TIPO_BV;
            const pago = l.id != null && acrescimos.some((a) => a.id === l.id && a.is_bv && a.bv_payment_status !== "nao_pago");
            return (
              <div key={l.key} className="rounded-md border border-line p-3">
                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-[9rem] flex-1">
                    <label className={LABEL}>Tipo</label>
                    <input
                      className={INPUT_CLASS}
                      value={l.tipo}
                      maxLength={40}
                      disabled={pago}
                      onChange={(e) => alterar(l.key, "tipo", e.target.value)}
                      placeholder="Ex.: BV, Taxa, Hora extra"
                    />
                  </div>
                  <div className="w-36">
                    <label className={LABEL}>{l.is_percent ? "Percentual" : "Valor (R$)"}</label>
                    {l.is_percent ? (
                      <input
                        className={INPUT_CLASS}
                        inputMode="decimal"
                        value={String(l.value ?? "")}
                        disabled={pago}
                        aria-invalid={Boolean(erroDaLinha(i, "value"))}
                        onChange={(e) => alterar(l.key, "value", e.target.value)}
                        placeholder="10"
                      />
                    ) : (
                      <MoneyInput
                        className={INPUT_CLASS}
                        value={typeof l.value === "number" ? l.value : 0}
                        disabled={pago}
                        aria-invalid={Boolean(erroDaLinha(i, "value"))}
                        onValueChange={(n) => alterar(l.key, "value", n)}
                      />
                    )}
                  </div>
                  <label className="mb-2 flex cursor-pointer items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(l.is_percent)}
                      disabled={pago}
                      onChange={(e) => alterar(l.key, "is_percent", e.target.checked)}
                    />
                    {ehBv ? "% do preço" : "% da venda"}
                  </label>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mb-1"
                    disabled={pago}
                    onClick={() => {
                      // Os erros do 400 são pelo índice da lista enviada: remover desloca as linhas.
                      salvar.reset();
                      setLinhas((a) => a.filter((x) => x.key !== l.key));
                    }}
                    aria-label={`Remover acréscimo ${l.tipo || "sem tipo"}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </div>
                {l.descricao ? <p className="mt-1 text-xs text-muted">{l.descricao}</p> : null}
                {pago && (
                  <p className="mt-1 text-xs text-muted">
                    BV já pago: o valor não muda e ele não sai por aqui (desmarque o pagamento na
                    Planilha de Pagamentos).
                  </p>
                )}
                {erroDaLinha(i, "value") && <p className="mt-1 text-xs text-red">{erroDaLinha(i, "value")}</p>}
                {erroDaLinha(i, "tipo") && <p className="mt-1 text-xs text-red">{erroDaLinha(i, "tipo")}</p>}
                {ehBv && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <div className="min-w-[10rem] flex-1">
                      <label className={LABEL}>Quem recebe *</label>
                      <input
                        className={INPUT_CLASS}
                        value={l.bv_recipient ?? ""}
                        maxLength={200}
                        aria-invalid={Boolean(erroDaLinha(i, "bv_recipient"))}
                        onChange={(e) => alterar(l.key, "bv_recipient", e.target.value)}
                      />
                      {erroDaLinha(i, "bv_recipient") && (
                        <p className="mt-1 text-xs text-red">{erroDaLinha(i, "bv_recipient")}</p>
                      )}
                    </div>
                    <div className="min-w-[10rem] flex-1">
                      <label className={LABEL}>Chave PIX *</label>
                      <input
                        className={INPUT_CLASS}
                        value={l.bv_pix ?? ""}
                        maxLength={140}
                        aria-invalid={Boolean(erroDaLinha(i, "bv_pix"))}
                        onChange={(e) => alterar(l.key, "bv_pix", e.target.value)}
                      />
                      {erroDaLinha(i, "bv_pix") && (
                        <p className="mt-1 text-xs text-red">{erroDaLinha(i, "bv_pix")}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setLinhas((a) => [
                ...a,
                { key: `n${Date.now()}`, tipo: "", value: 0, is_percent: false, bv_recipient: "", bv_pix: "" },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            Adicionar acréscimo
          </Button>

          <div className="space-y-1 text-xs text-muted">
            <p>
              <strong>BV em %</strong>: sobre o preço com os outros acréscimos, antes do BV e da
              nota — com nota, R$ 1.309,52 dá BV de R$ 100,00; com um "Outro" de R$ 300 e venda de
              R$ 1.430,00 sem nota, R$ 130,00.
            </p>
            <p>
              <strong>BV em reais</strong>: o valor combinado com quem indicou, gravado como
              digitado; se a venda mudar depois, acompanha na mesma proporção enquanto não for pago.
            </p>
            <p>Outros acréscimos em % são sobre a venda. BV exige quem recebe e o PIX.</p>
          </div>

          {salvar.isError && (
            <p className="text-sm text-red">{campos.items ?? salvar.error?.message}</p>
          )}

          <div className="flex gap-2">
            <Button
              loading={salvar.isPending}
              disabled={vendaMudouOBv}
              onClick={() =>
                salvar.mutate(
                  linhas.map(({ key: _key, ...resto }) => ({
                    ...resto,
                    value: resto.is_percent ? percentualDigitado(resto.value) : resto.value,
                  })),
                  { onSuccess: () => setEditando(false) },
                )
              }
            >
              Salvar
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                salvar.reset();
                setEditando(false);
              }}
            >
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
          <Button variant="outline" size="sm" onClick={() => abrir()}>
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Editar
          </Button>
        ) : null
      }
    >
      {canEdit && (
        <div className="mb-3">
          <AlertaBvDoOrcamento pendente={pendente} onLancar={() => abrir(true)} />
        </div>
      )}
      {acrescimos.length === 0 ? (
        <Empty>Nenhum acréscimo.</Empty>
      ) : (
        <div className="divide-y divide-line">
          {acrescimos.map((a) => (
            <DataRow key={a.id} label={a.label}>
              <span className="flex items-center justify-end gap-2">
                {a.is_bv && (
                  <Badge tone={a.bv_payment_status === "pago" ? "green" : "gold"}>
                    {a.bv_payment_status === "pago"
                      ? "BV pago"
                      : a.bv_payment_status === "no_banco"
                        ? "BV no banco"
                        : "BV a pagar"}
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
