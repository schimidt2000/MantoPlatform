import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { CancelamentosDoPeriodo } from "../lib/financeiro";

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

/** `dd/mm` de uma data `AAAA-MM-DD…`, sem `new Date()` (data pura não escorrega de fuso). */
function diaMes(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes ? `${dia}/${mes}` : iso;
}

/** O `AAAA-MM` do período quando ele é um mês só (o link da página vai filtrado nele). */
function mesDoPeriodo(inicio?: string | null, fim?: string | null): string | null {
  if (!inicio || !fim) return null;
  return inicio.slice(0, 7) === fim.slice(0, 7) ? inicio.slice(0, 7) : null;
}

export interface CardCancelamentosDoPeriodoProps {
  painel?: CancelamentosDoPeriodo;
  inicio?: string | null;
  fim?: string | null;
}

/**
 * Card "Cancelamentos do período" (feature 312; D31 do dono): os cancelados do mês do
 * cancelamento, com o dinheiro que ficou e o link para cada um — é por aqui que a vendedora acha o
 * próprio cancelado, que saiu da agenda, da busca e da lista de vendas. Os números saem da mesma
 * função da linha "Retido de cancelamentos" da DRE (servidor). Imposto e efeito no resultado só
 * chegam a Superadmin e Financeiro (Q1 = B), que são também quem abre a página de Cancelamentos —
 * daí o link aparecer com eles.
 */
export function CardCancelamentosDoPeriodo({ painel, inicio, fim }: CardCancelamentosDoPeriodoProps) {
  if (!painel || painel.quantidade <= 0) return null;
  const gestor = painel.imposto !== undefined;
  const mes = mesDoPeriodo(inicio, fim);
  const numeros: { rotulo: string; valor: string }[] = [
    { rotulo: "Cancelados", valor: String(painel.quantidade) },
    { rotulo: "Pago", valor: brl(painel.pago) },
    { rotulo: "Devolvido", valor: brl(painel.devolvido) },
    { rotulo: "A devolver", valor: brl(painel.devolucao_a_pagar) },
    { rotulo: "Retido", valor: brl(painel.retido) },
    { rotulo: "Comissão do retido", valor: brl(painel.comissao_retido) },
    { rotulo: "BV do retido", valor: brl(painel.bv_retido) },
  ];
  if (gestor) {
    numeros.push({ rotulo: "Imposto", valor: brl(painel.imposto) });
    numeros.push({ rotulo: "Efeito no resultado", valor: brl(painel.efeito_resultado) });
  }

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 pb-2">
        <CardTitle className="text-base">🚫 Cancelamentos do período</CardTitle>
        {gestor && (
          <Link
            to={mes ? `/events/cancelamentos?mes=${mes}` : "/events/cancelamentos"}
            className="text-sm text-blue underline"
          >
            Ver na página de Cancelamentos
          </Link>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
          {numeros.map((n) => (
            <div key={n.rotulo} className="min-w-0">
              <dt className="text-xs text-muted">{n.rotulo}</dt>
              <dd className="tabular-nums text-ink">{n.valor}</dd>
            </div>
          ))}
        </dl>
        <ul className="divide-y divide-line text-sm">
          {painel.itens.map((item) => (
            <li key={item.event_id} className="flex flex-wrap items-baseline justify-between gap-2 py-1.5">
              <span className="min-w-0">
                <Link to={`/events/${item.event_id}`} className="text-ink hover:underline">
                  {item.titulo}
                </Link>
                <span className="block text-xs text-muted">
                  {item.event_date ? `evento ${diaMes(item.event_date)} · ` : ""}cancelado {diaMes(item.cancelado_em)}
                  {item.seller_name ? ` · ${item.seller_name}` : ""}
                </span>
              </span>
              <span className="text-xs tabular-nums text-muted">
                retido <span className="text-ink">{brl(item.retido)}</span>
                {item.devolvido !== undefined && ` · devolvido ${brl(item.devolvido)}`}
                {item.comissao_retido !== undefined && ` · comissão ${brl(item.comissao_retido)}`}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
