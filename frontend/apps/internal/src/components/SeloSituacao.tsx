import { CalendarX } from "lucide-react";
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

interface SeloSituacaoProps {
  situacao?: SituacaoEvento | null;
  desde?: string | null;
  /** Só o ícone — o chip do Mês (~80 px) e o bloco curto do Dia não cabem o texto. */
  compacto?: boolean;
}

/**
 * O selo único da situação do evento na agenda (feature 303). Nesta entrega só desenha a marca
 * "Sumiu do Google Agenda"; qualquer outra situação, ou a ausência dela, não desenha nada (o selo
 * do cancelado chega com a terceira entrega). O ícone é o mesmo do aviso no sino.
 *
 * O tooltip é o `title` de um `span` em volta: o `Badge` não repassa atributos. Em toque não há
 * tooltip — a data é lida no banner do evento.
 */
export function SeloSituacao({ situacao, desde, compacto = false }: SeloSituacaoProps) {
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
