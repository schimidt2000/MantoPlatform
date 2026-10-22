import type { ReactNode } from "react";
import { formatBRL } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";

export type PedidoDeCancelamento = NonNullable<EventoDetalhe["event"]["deletion_request"]>;

/** `dd/mm/aaaa` a partir de um ISO, sem passar por `Date` (horário de parede de São Paulo). */
function dataCurta(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : iso;
}

function brl(valor: string | number): string {
  return `R$ ${formatBRL(Number(valor))}`;
}

/** O alcance como o quadro o diz; `null` (pedido de antes da 315) não diz nada. */
function textoDoAlcance(alcance: PedidoDeCancelamento["alcance"]): string | null {
  if (alcance === "so_este_dia") return "só este dia da venda";
  return null;
}

/** "Devolver parte: R$ 600,00 a Fulana (PIX …)" — com o que o servidor mandou para este papel. */
export function textoDaDevolucao(pedido: PedidoDeCancelamento): string | null {
  const dev = pedido.devolucao;
  if (!dev?.modo) return null;
  const rotulo = { tudo: "Devolver tudo", parte: "Devolver parte", nada: "Não devolver" }[dev.modo];
  let texto = dev.valor ? `${rotulo}: ${brl(dev.valor)}` : rotulo;
  if (dev.nome) texto += ` a ${dev.nome}`;
  if (dev.pix) texto += ` (PIX ${dev.pix})`;
  if (pedido.venda_nova) texto += ` · a venda passa a ${brl(pedido.venda_nova)}`;
  return texto;
}

export interface QuadroDoPedidoProps {
  pedido: PedidoDeCancelamento;
  /** Quem pediu está olhando: o quadro lembra que só o Superadmin fecha o pedido. */
  ehAutor?: boolean;
  /** Os botões do Superadmin, quando cabem. */
  acoes?: ReactNode;
}

/**
 * O pedido de cancelamento pendente (feature 315). Mostra só o que veio: o servidor corta motivo,
 * autor e devolução por papel — chave ausente é "não mostrar", nunca "sem motivo".
 */
export function QuadroDoPedido({ pedido, ehAutor = false, acoes }: QuadroDoPedidoProps) {
  const alcance = textoDoAlcance(pedido.alcance);
  const devolucao = textoDaDevolucao(pedido);
  return (
    <div className="mt-3 rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="status">
      <p className="font-semibold text-gold-ink">Cancelamento pedido — aguardando o Superadmin</p>
      <p className="mt-0.5 text-ink">
        Pedido em {dataCurta(pedido.requested_at)}
        {pedido.requested_by ? ` por ${pedido.requested_by}` : ""}
        {alcance ? ` — ${alcance}` : ""}.
      </p>
      {pedido.reason && <p className="mt-1 whitespace-pre-line text-ink">{pedido.reason}</p>}
      {devolucao && <p className="mt-1 text-ink">Devolução combinada: {devolucao}</p>}
      {ehAutor && (
        <p className="mt-1 text-muted">Se a cliente voltar atrás, avise o Superadmin — só ele fecha o pedido.</p>
      )}
      {acoes}
    </div>
  );
}
