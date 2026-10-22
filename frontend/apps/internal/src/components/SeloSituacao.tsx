import { Ban, CalendarX, FileX } from "lucide-react";
import { Badge, formatShortDate } from "@manto/ui";
import type { SituacaoEvento } from "../lib/agenda";

/**
 * `Sumiu do Google Agenda — percebido em dd/mm/aaaa`: o tooltip do selo e do chip do Mês. A data
 * sai por `formatShortDate` porque `desde` é horário de parede de São Paulo sem fuso — passar
 * por `toISOString()` deslocaria o dia.
 */
export function textoDoSumico(desde: string | null | undefined): string {
  return desde
    ? `Sumiu do Google Agenda — percebido em ${formatShortDate(desde)}`
    : "Sumiu do Google Agenda";
}

/**
 * `Cancelamento pedido em dd/mm/aaaa` (feature 315): o tooltip do selo e dos chips. Sem data (as
 * listas que mandam só o código), só "Cancelamento pedido".
 */
export function textoDoPedido(desde: string | null | undefined): string {
  return desde ? `Cancelamento pedido em ${formatShortDate(desde)}` : "Cancelamento pedido";
}

/** `Evento cancelado em dd/mm/aaaa`: o tooltip do selo do cancelado (feature 312). */
export function textoDoCancelamento(desde: string | null | undefined): string {
  return desde ? `Evento cancelado em ${formatShortDate(desde)}` : "Evento cancelado";
}

interface SeloSituacaoProps {
  situacao?: SituacaoEvento | null;
  desde?: string | null;
  /** Só o ícone — o chip do Mês (~80 px) e o bloco curto do Dia não cabem o texto. */
  compacto?: boolean;
}

/**
 * O selo único da situação do evento (features 303 e 312): "Sumiu do Google Agenda" e "Cancelado".
 * O do cancelado só é desenhado onde uma coisa VIVA ligada a ele aparece (Gastos Extras, tags NFC,
 * formulários, pedidos de figurino) — na agenda, na busca e no painel do grupo o cancelado não chega
 * do servidor. O pedido de cancelamento (feature 315; código `exclusao_solicitada`) é um selo neutro —
"Cancelamento pedido" —, também no dia da venda que herda o pedido do 1º. O ícone do sumiço é o do sino.
 *
 * O tooltip é o `title` de um `span` em volta: o `Badge` não repassa atributos. Em toque não há
 * tooltip — a data é lida no banner do evento.
 */
export function SeloSituacao({ situacao, desde, compacto = false }: SeloSituacaoProps) {
  if (situacao === "cancelado") {
    return compacto ? (
      <span
        title={textoDoCancelamento(desde)}
        className="mr-1 inline-flex shrink-0 items-center align-middle text-red"
      >
        <Ban role="img" aria-label="Evento cancelado" className="h-3 w-3" />
      </span>
    ) : (
      <span title={textoDoCancelamento(desde)} className="inline-flex shrink-0">
        <Badge tone="red" className="gap-1">
          <Ban aria-hidden className="h-3 w-3" />
          Cancelado
        </Badge>
      </span>
    );
  }
  if (situacao === "exclusao_solicitada") {
    return compacto ? (
      <span title={textoDoPedido(desde)} className="mr-1 inline-flex shrink-0 items-center align-middle text-muted">
        <FileX role="img" aria-label="Cancelamento pedido" className="h-3 w-3" />
      </span>
    ) : (
      <span title={textoDoPedido(desde)} className="inline-flex shrink-0">
        <Badge tone="neutral" className="gap-1">
          <FileX aria-hidden className="h-3 w-3" />
          Cancelamento pedido
        </Badge>
      </span>
    );
  }
  if (situacao !== "sumiu_do_google") return null;
  if (compacto) {
    return (
      <span
        title={textoDoSumico(desde)}
        className="mr-1 inline-flex shrink-0 items-center align-middle"
      >
        <CalendarX role="img" aria-label="Sumiu do Google Agenda" className="h-3 w-3" />
      </span>
    );
  }
  return (
    <span title={textoDoSumico(desde)} className="inline-flex shrink-0">
      <Badge tone="gold" className="gap-1">
        <CalendarX aria-hidden className="h-3 w-3" />
        Sumiu do Google
      </Badge>
    </span>
  );
}
