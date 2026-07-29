import { useMemo, useState } from "react";
import { AvatarThumb, Badge, Button, Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  formatDeadline,
  GIFT_3D_STATUSES,
  GIFT_3D_STATUS_LABELS,
  GIFT_3D_STATUS_TONES,
  useAcervo3D,
  useAddEvent3DGift,
  useDeleteEvent3DGift,
  useUpdateEvent3DGift,
  type Acervo3DItem,
  type Event3DGift,
  type Gift3DStatus,
} from "../../lib/impressoes3d";
import { Empty, INPUT_CLASS, Panel } from "./parts";

/** Opções do Combobox com miniatura quadrada da peça (Princípio X.1/X.2). */
function acervoOptions(items: Acervo3DItem[]): ComboboxOption[] {
  return items.map((item) => ({
    value: String(item.id),
    label: item.name,
    description: item.usage_count > 0 ? `${item.usage_count} uso(s) em eventos` : undefined,
    imageUrl: assetUrl(item.photo_url) ?? null,
    imageShape: "square" as const,
    fallbackIcon: "🧊",
  }));
}

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

/** Formulário de vínculo de um presente novo — seleção visual obrigatória via `Combobox`. */
function AddGiftForm({ eventId }: { eventId: number }) {
  const acervo = useAcervo3D(true);
  const add = useAddEvent3DGift(eventId);
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [deadline, setDeadline] = useState("");
  const [notes, setNotes] = useState("");

  const options = useMemo(() => acervoOptions(acervo.data?.items ?? []), [acervo.data]);
  const invalidItem = Boolean(add.error && !itemId);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!itemId) return;
    add.mutate(
      {
        item_id: Number(itemId),
        quantity: Number(quantity) || 1,
        deadline_date: deadline || null,
        notes: notes.trim(),
      },
      {
        // Só limpa o formulário quando a API confirma (Princípio V).
        onSuccess: () => {
          setItemId(null);
          setQuantity("1");
          setDeadline("");
          setNotes("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 border-t border-line pt-3">
      <Combobox
        aria-label="Buscar peça do Acervo 3D"
        placeholder="🔍 Buscar peça do Acervo 3D…"
        emptyMessage="Nenhuma peça encontrada no Acervo."
        options={options}
        loading={acervo.isLoading}
        value={itemId}
        invalid={invalidItem}
        onChange={(next) => setItemId(next)}
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs text-muted">Quantidade</span>
          <input
            type="number"
            min={1}
            className={INPUT_CLASS}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-muted">Prazo de entrega</span>
          <input
            type="date"
            className={INPUT_CLASS}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </label>
      </div>
      <input
        className={INPUT_CLASS}
        placeholder="Observações (opcional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        aria-label="Observações do presente 3D"
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" loading={add.isPending} disabled={!itemId}>
          Adicionar presente
        </Button>
        {acervo.isError && (
          <span className="text-sm text-red">Não foi possível carregar o Acervo 3D.</span>
        )}
        {add.isError && <span className="text-sm text-red">{add.error?.message}</span>}
      </div>
    </form>
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
      {canManage && <AddGiftForm eventId={data.event.id} />}
    </Panel>
  );
}
