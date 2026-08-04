import { Badge, Button } from "@manto/ui";
import { Video } from "lucide-react";
import type { EventoDetalhe } from "../../lib/agenda";
import { AvisosFalhosBanner } from "../AvisosFalhosBanner";
import { Empty, Panel } from "./parts";

export interface PedidoVirtualSectionProps {
  data: EventoDetalhe;
}

/**
 * Ficha e acesso de uma venda da Loja de Interações Virtuais (feature 205, US3).
 *
 * É o que o talento precisa para executar a chamada: **quem** é a criança, **o que** a família
 * contou sobre ela e **por onde** entrar. Antes disso existir, o talento teria que abrir o pedido
 * na loja — a informação estava no sistema, mas não onde o trabalho acontece.
 *
 * Renderiza só em evento de venda virtual: o servidor só inclui `pedido_virtual` nesse caso
 * (mesmo padrão de `Presente3DSection`), e o tipo é reconferido aqui.
 *
 * As dicas da família aparecem em destaque de propósito — é o que transforma uma chamada genérica
 * numa que parece feita sob medida.
 */
export function PedidoVirtualSection({ data }: PedidoVirtualSectionProps) {
  const pedido = data.pedido_virtual;
  if (!pedido || data.event.event_type !== "VIRTUAL") return null;

  const aoVivo = pedido.modality === "ao_vivo";

  return (
    <Panel
      title="Interação virtual"
      actions={
        <Badge tone={aoVivo ? "accent" : "blue"}>
          {aoVivo ? "Chamada ao vivo" : "Vídeo gravado"}
        </Badge>
      }
    >
      <dl className="divide-y divide-line text-[13px]">
        <div className="flex justify-between gap-3 py-2">
          <dt className="text-muted">Criança</dt>
          <dd className="text-right font-medium text-ink">
            {pedido.child_name}, {pedido.child_age} anos
          </dd>
        </div>
        <div className="flex justify-between gap-3 py-2">
          <dt className="text-muted">Campanha</dt>
          <dd className="text-right text-ink">{pedido.campaign_title ?? "—"}</dd>
        </div>
        <div className="flex justify-between gap-3 py-2">
          <dt className="text-muted">Contato</dt>
          <dd className="text-right text-ink">
            <div>{pedido.contact_phone_display}</div>
            <div className="text-[11px] text-muted">{pedido.contact_email}</div>
          </dd>
        </div>
        {pedido.delivery_address && (
          <div className="flex justify-between gap-3 py-2">
            <dt className="text-muted">Entrega do presente</dt>
            <dd className="text-right text-ink">{pedido.delivery_address}</dd>
          </div>
        )}
        <div className="flex justify-between gap-3 py-2">
          <dt className="text-muted">Pedido</dt>
          <dd className="text-right font-mono text-[11px] text-muted">{pedido.order_nsu}</dd>
        </div>
      </dl>

      {pedido.behavior_notes ? (
        <div className="mt-3 rounded-lg border border-line bg-surface-2 p-3">
          <div className="text-[11px] font-bold uppercase tracking-wide text-muted">
            Dicas da família
          </div>
          <p className="mt-1 whitespace-pre-line text-[13px] text-ink">{pedido.behavior_notes}</p>
        </div>
      ) : (
        <Empty>A família não deixou dicas sobre a criança.</Empty>
      )}

      {aoVivo && (
        <div className="mt-3 border-t border-line pt-3">
          {pedido.meet_url ? (
            <Button asChild className="w-full">
              <a href={pedido.meet_url} target="_blank" rel="noopener noreferrer">
                <Video className="size-4" />
                Entrar na sala
              </a>
            </Button>
          ) : (
            // Só o caso "ainda tentando" fica aqui, em tom de espera. Quando a política se esgota,
            // quem fala é o banner vermelho abaixo — porque aí não é mais aviso, é cobrança.
            !pedido.meet_retry_esgotado && (
              <div className="rounded-lg border border-gold bg-gold-soft p-3 text-[12px] text-ink">
                A sala ainda não foi criada pelo Google. A venda está válida — a varredura continua
                tentando sozinha em segundo plano.
              </div>
            )
          )}
        </div>
      )}

      {/* Entregas automáticas que falharam (FR-039c, FR-056a). O painel do evento é onde a equipe
          abre quando a família liga — é aqui que a falha do e-mail precisa estar visível. */}
      <div className="mt-3 empty:mt-0">
        <AvisosFalhosBanner
          orderId={pedido.id}
          avisos={pedido.avisos_falhos ?? []}
          meetRetryEsgotado={pedido.meet_retry_esgotado ?? false}
          meetAttempts={pedido.meet_attempts ?? 0}
        />
      </div>
    </Panel>
  );
}
