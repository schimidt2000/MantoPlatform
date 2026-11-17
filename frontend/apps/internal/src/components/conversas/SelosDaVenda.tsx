import { BellRing, Megaphone } from "lucide-react";
import { Badge } from "@manto/ui";
import { quandoDoLembrete, type VendaResumo } from "../../lib/conversas";

/**
 * Os selos da venda no item da lista (feature 349, FR-013): veio de anúncio, a etapa mais avançada (a régua do
 * funil; "Chegou" não ganha selo), qualificada, perdida com o motivo e o lembrete marcado. Os textos das etapas e
 * dos motivos vêm do servidor. Sem nada a mostrar, nada aparece (não ocupa a linha).
 */
export function SelosDaVenda({ venda }: { venda: VendaResumo | null | undefined }) {
  if (!venda) return null;
  const etapa = venda.etapa !== "chegou" ? (venda.etapa_rotulo ?? null) : null;
  const algum = venda.anuncio || etapa || venda.qualificada || venda.perdida || venda.lembrete_em;
  if (!algum) return null;
  return (
    <span className="mt-1 flex flex-wrap items-center gap-1">
      {venda.anuncio ? (
        <Badge tone="blue">
          <Megaphone className="mr-0.5 h-3 w-3" aria-hidden />
          Anúncio
        </Badge>
      ) : null}
      {etapa ? <Badge tone={venda.etapa === "orcamento" || venda.etapa === "formulario" ? "accent" : "green"}>{etapa}</Badge> : null}
      {venda.qualificada && !venda.perdida ? <Badge tone="gold">Qualificada</Badge> : null}
      {venda.perdida ? <Badge tone="red">Perdida: {venda.perdida.rotulo}</Badge> : null}
      {venda.lembrete_em ? (
        <span className="inline-flex items-center gap-0.5 text-[11px] text-muted" title={`Lembrete ${quandoDoLembrete(venda.lembrete_em)}`}>
          <BellRing className="h-3 w-3" aria-hidden />
          <span className="sr-only">Lembrete </span>
          {quandoDoLembrete(venda.lembrete_em)}
        </span>
      ) : null}
    </span>
  );
}
