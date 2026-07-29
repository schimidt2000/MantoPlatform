import { AvatarThumb, Badge, Button } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  formatDeadline,
  GIFT_3D_STATUSES,
  GIFT_3D_STATUS_LABELS,
  GIFT_3D_STATUS_TONES,
  useDeleteEvent3DGift,
  useUpdateEvent3DGift,
  type Event3DGift,
  type Gift3DStatus,
} from "../../lib/impressoes3d";
import { AddPresente3DForm } from "../AddPresente3DForm";
import { Empty, INPUT_CLASS, Panel } from "./parts";

interface GiftRowProps {
  gift: Event3DGift;
  canManage: boolean;
}

/** Linha de um presente já vinculado: miniatura, quantidade, prazo, status e remoção. */
function GiftRow({ gift, canManage }: GiftRowProps) {
  const update = useUpdateEvent3DGift();
  const remove = useDeleteEvent3DGift();

  return (
    <li className="flex flex-wrap items-center gap-2 py-2">
      <AvatarThumb
        src={assetUrl(gift.item?.photo_url)}
        name={gift.item?.name}
        shape="square"
        size="md"
        fallbackIcon="🧊"
      />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm text-ink">
          {gift.item?.name ?? "Peça removida do Acervo"}
          <span className="text-muted"> · {gift.quantity}x</span>
        </div>
        <div className="text-xs text-muted">
          Prazo: {gift.deadline_date ? formatDeadline(gift.deadline_date) : "sem prazo"}
          {gift.notes ? ` · ${gift.notes}` : ""}
        </div>
      </div>
      {canManage ? (
        <select
          className={`${INPUT_CLASS} w-auto`}
          value={gift.status}
          disabled={update.isPending}
          aria-label={`Status do presente ${gift.item?.name ?? ""}`}
          onChange={(e) =>
            update.mutate({
              eventId: gift.event_id,
              giftId: gift.id,
              input: { status: e.target.value as Gift3DStatus },
            })
          }
        >
          {GIFT_3D_STATUSES.map((status) => (
            <option key={status} value={status}>
              {GIFT_3D_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      ) : (
        <Badge tone={GIFT_3D_STATUS_TONES[gift.status]}>
          {GIFT_3D_STATUS_LABELS[gift.status]}
        </Badge>
      )}
      {canManage && (
        <Button
          variant="ghost"
          size="sm"
          loading={remove.isPending}
          aria-label={`Remover ${gift.item?.name ?? "presente"}`}
          onClick={() => {
            if (window.confirm("Remover este presente 3D do evento?")) {
              remove.mutate({ eventId: gift.event_id, giftId: gift.id });
            }
          }}
        >
          ✕
        </Button>
      )}
    </li>
  );
}

export interface Presente3DSectionProps {
  data: EventoDetalhe;
}

/**
 * Presentes 3D do evento (feature 200) — coluna esquerda (logística) do detalhe do evento.
 *
 * Renderiza apenas em eventos do tipo SHOW: o servidor só inclui `presentes_3d` no payload
 * nesse caso, e o tipo é reconferido aqui para a seção nunca aparecer fora de contexto. A
 * edição é restrita ao Artista 3D/Superadmin (`flags.can_manage_3d`); os demais papéis leem a
 * lista para saber o que foi combinado.
 */
export function Presente3DSection({ data }: Presente3DSectionProps) {
  const gifts = data.presentes_3d;
  if (gifts === undefined || data.event.event_type !== "SHOW") return null;

  const canManage = Boolean(data.flags.can_manage_3d);

  return (
    <Panel
      title="Presentes 3D"
      actions={
        gifts.length > 0 ? (
          <Badge tone="neutral">{gifts.length} peça(s)</Badge>
        ) : undefined
      }
    >
      {gifts.length === 0 ? (
        <Empty>Nenhum presente 3D vinculado a este evento.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {gifts.map((gift) => (
            <GiftRow key={gift.id} gift={gift} canManage={canManage} />
          ))}
        </ul>
      )}
      {canManage && (
        <div className="border-t border-line pt-3">
          <AddPresente3DForm eventId={data.event.id} />
        </div>
      )}
    </Panel>
  );
}
