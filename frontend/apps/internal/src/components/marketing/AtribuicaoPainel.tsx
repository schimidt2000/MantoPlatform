import { useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  DIVISAO_ATRIBUICAO_LABELS,
  useAtribuicao,
  type AtribuicaoVenda,
  type DesempenhoParams,
  type DivisaoAtribuicao,
  type FunilComCustoGrupo,
} from "../../lib/marketing";

// Espaço que não quebra: em 390 px o "R$" não pode ficar no fim de uma linha e o número na outra.
const brl = (valor: string | null | undefined) => (valor == null ? "—" : `R$\u00a0${formatBRL(Number(valor))}`);
const VENDAS_DE_INICIO = 10;

const FONTE: Record<AtribuicaoVenda["contato"]["fonte"], string> = {
  conversa: "Conversa do anúncio",
  ficha: "Anúncio gravado na ficha",
  utm: "Origem da ficha",
};

const dataCurta = (iso: string) => {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano.slice(2)}`;
};

function plural(n: number, um: string, varios: string): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? um : varios}`;
}

function GrupoDoFunil({ g }: { g: FunilComCustoGrupo }) {
  const q = g.quantidades;
  return (
    <div className="space-y-1">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 flex-1 break-words text-sm font-medium text-ink">{g.rotulo}</p>
        <span className="shrink-0 text-sm tabular-nums text-ink">{g.gasto != null ? brl(g.gasto) : "—"}</span>
      </div>
      <p className="text-xs text-ink">
        {plural(q.chegou, "conversa", "conversas")} · {plural(q.orcamento, "orçamento", "orçamentos")} ·{" "}
        {plural(q.evento, "evento", "eventos")}
      </p>
      {g.gasto != null && Number(g.gasto) === 0 && <p className="text-xs text-muted">Nenhum gasto lido no período.</p>}
      {g.gasto != null && Number(g.gasto) > 0 && (
        <p className="text-xs text-muted">
          {brl(g.custo_conversa)} por conversa · {brl(g.custo_orcamento)} por orçamento · {brl(g.custo_evento)} por
          evento
        </p>
      )}
    </div>
  );
}

function VendaAtribuida({ v }: { v: AtribuicaoVenda }) {
  const c = v.contato;
  const detalhe = [c.anuncio, c.campanha].filter(Boolean).join(" · ");
  return (
    <li className="space-y-0.5 py-2.5">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 flex-1 break-words text-sm font-medium text-ink">{v.titulo}</p>
        {v.valor != null && <span className="shrink-0 text-sm tabular-nums text-ink">{brl(v.valor)}</span>}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
        <span>venda em {dataCurta(v.sale_date)}</span>
        <Badge tone={v.frente_nome ? "accent" : "neutral"}>{v.frente_nome ?? "Sem frente"}</Badge>
      </div>
      <p className="text-xs text-muted">
        {FONTE[c.fonte]} em {dataCurta(c.em)}
        {detalhe ? ` — ${detalhe}` : ""}
      </p>
    </li>
  );
}

function ListaDeVendas({ vendas, total }: { vendas: AtribuicaoVenda[]; total: number }) {
  const [todas, setTodas] = useState(false);
  if (!vendas.length) return <p className="py-2 text-sm text-muted">Nenhuma venda atribuída no período.</p>;
  const mostradas = todas ? vendas : vendas.slice(0, VENDAS_DE_INICIO);
  return (
    <>
      <ul className="divide-y divide-line">
        {mostradas.map((v) => (
          <VendaAtribuida key={v.event_id} v={v} />
        ))}
      </ul>
      {vendas.length > VENDAS_DE_INICIO && !todas && (
        <Button type="button" variant="ghost" size="sm" className="mt-1" onClick={() => setTodas(true)}>
          Mostrar todas ({vendas.length})
        </Button>
      )}
      {total > vendas.length && (
        <p className="mt-1 text-xs text-muted">A lista mostra as {vendas.length} mais recentes de {total}.</p>
      )}
    </>
  );
}

/**
 * Vendas atribuídas e funil com custo (feature 351), no mesmo período do Desempenho.
 *
 * A divisão do funil fica no endereço (`?dividir=`): o link "funil por conceito" se compartilha. Em 390 px
 * cada grupo é uma linha empilhada — números e custos quebram linha, nada rola de lado. O valor de cada
 * venda só chega para o Superadmin (o servidor decide).
 */
export function AtribuicaoPainel({ params }: { params: DesempenhoParams }) {
  const reduceMotion = useReducedMotion();
  const [busca, setBusca] = useSearchParams();
  const location = useLocation();
  const pedido = busca.get("dividir");
  const dividir: DivisaoAtribuicao = pedido && pedido in DIVISAO_ATRIBUICAO_LABELS ? (pedido as DivisaoAtribuicao) : "frente";
  const query = useAtribuicao(params, dividir);

  function setDividir(valor: DivisaoAtribuicao) {
    setBusca(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        if (valor === "frente") proximo.delete("dividir");
        else proximo.set("dividir", valor);
        return proximo;
      },
      { replace: true, state: location.state },
    );
  }

  if (query.isLoading) return <Skeleton className="mb-4 h-48 w-full" />;
  if (query.isError || !query.data)
    return (
      <p className="mb-4 rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível carregar a atribuição. Tente novamente.
      </p>
    );
  const { funil, vendas, vendas_total } = query.data;

  return (
    <section className={`mb-4 grid gap-3 lg:grid-cols-2 ${query.isPlaceholderData ? "opacity-60" : ""}`} aria-label="Atribuição">
      <Card className="px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Funil com custo</h3>
          <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-panel p-1" role="group" aria-label="Dividir o funil por">
            {(Object.keys(DIVISAO_ATRIBUICAO_LABELS) as DivisaoAtribuicao[]).map((opcao) => (
              <Button
                key={opcao}
                type="button"
                size="sm"
                variant={dividir === opcao ? "default" : "ghost"}
                aria-pressed={dividir === opcao}
                onClick={() => setDividir(opcao)}
              >
                {DIVISAO_ATRIBUICAO_LABELS[opcao]}
              </Button>
            ))}
          </div>
        </div>
        <p className="mt-1 text-[11px] text-muted">
          Conversas novas do período pelo primeiro anúncio delas (CRM). Gasto da Meta: é de lá que as conversas chegam
          com origem.
        </p>
        {funil.total === 0 ? (
          <p className="py-2 text-sm text-muted">Nenhuma conversa com anúncio no período.</p>
        ) : (
          <ul className="divide-y divide-line">
            <AnimatePresence initial={false}>
              {funil.grupos.map((g) => (
                <motion.li
                  key={`${dividir}-${g.chave}`}
                  className="py-2.5"
                  initial={reduceMotion ? false : { opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0 }}
                  transition={{ duration: 0.18 }}
                >
                  <GrupoDoFunil g={g} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </Card>
      <Card className="px-4 py-3">
        <h3 className="text-sm font-semibold text-ink">Vendas atribuídas ({vendas_total.toLocaleString("pt-BR")})</h3>
        <p className="mt-1 text-[11px] text-muted">Cada venda e o contato pago que a trouxe.</p>
        <ListaDeVendas vendas={vendas} total={vendas_total} />
      </Card>
    </section>
  );
}
