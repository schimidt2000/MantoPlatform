import { useMemo, useState } from "react";
import { Button, Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useAcervo3D, useAddEvent3DGift, type Acervo3DItem } from "../lib/impressoes3d";

/**
 * Formulário de vínculo de um Presente 3D a um evento (features 200/202).
 *
 * Fonte única do formulário (Princípio I): usado tanto pela seção do detalhe do evento
 * (`Presente3DSection`) quanto pelo Dialog "Vincular presente" da Fila de Impressão — o Artista
 * 3D resolve a pendência sem sair da fila.
 *
 * A seleção da peça usa obrigatoriamente o `Combobox` de `@manto/ui` com a miniatura **quadrada**
 * do modelo (Princípio X.1/X.2) — a escolha é visual, não por nome digitado.
 */

const INPUT_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Opções do Combobox com miniatura quadrada da peça. */
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

export interface AddPresente3DFormProps {
  eventId: number;
  /** Prazo sugerido (`YYYY-MM-DD`) — a Fila pré-preenche com a data do evento. */
  defaultDeadline?: string;
  /** Rótulo do botão de envio. */
  submitLabel?: string;
  /** Chamado após a API confirmar o vínculo. */
  onAdded?: () => void;
}

export function AddPresente3DForm({
  eventId,
  defaultDeadline = "",
  submitLabel = "Adicionar presente",
  onAdded,
}: AddPresente3DFormProps) {
  const acervo = useAcervo3D(true);
  const add = useAddEvent3DGift(eventId);
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [deadline, setDeadline] = useState(defaultDeadline);
  const [notes, setNotes] = useState("");

  const options = useMemo(() => acervoOptions(acervo.data?.items ?? []), [acervo.data]);
  const semPecas = !acervo.isLoading && !acervo.isError && options.length === 0;

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
          setDeadline(defaultDeadline);
          setNotes("");
          onAdded?.();
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <Combobox
        aria-label="Buscar peça do Acervo 3D"
        placeholder="🔍 Buscar peça do Acervo 3D…"
        emptyMessage="Nenhuma peça encontrada no Acervo."
        options={options}
        loading={acervo.isLoading}
        value={itemId}
        invalid={Boolean(add.error && !itemId)}
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
          {submitLabel}
        </Button>
        {acervo.isError && (
          <span className="text-sm text-red">Não foi possível carregar o Acervo 3D.</span>
        )}
        {semPecas && (
          <span className="text-sm text-muted">
            Nenhuma peça no Acervo ainda — cadastre uma em “Acervo 3D”.
          </span>
        )}
        {add.isError && <span className="text-sm text-red">{add.error?.message}</span>}
      </div>
    </form>
  );
}
