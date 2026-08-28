import { useMemo, useState } from "react";
import { Button, Combobox, Input } from "@manto/ui";
import { useAcervo3D } from "../../lib/impressoes3d";
import { useGerarLoteNfc } from "../../lib/nfc";
import { fieldError } from "./helpers";

/** Formulário de lote: peça NFC + quantidade. As tags nascem sem evento (estoque). */
export function GerarLoteForm() {
  const acervo = useAcervo3D();
  const gerar = useGerarLoteNfc();
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [geradas, setGeradas] = useState<number | null>(null);

  const nfcItems = useMemo(
    () => (acervo.data?.items ?? []).filter((i) => i.nfc_prefix !== null && i.is_active),
    [acervo.data],
  );
  const options = nfcItems.map((i) => ({
    value: String(i.id),
    label: `${i.name} (prefixo ${i.nfc_prefix})`,
  }));

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setGeradas(null);
    gerar.mutate(
      { item_id: Number(itemId), quantity: Number(quantity) || 0 },
      { onSuccess: (data) => setGeradas(data.tags.length) },
    );
  }

  if (!acervo.isLoading && nfcItems.length === 0) {
    return (
      <p className="text-sm text-muted">
        Nenhuma peça do Acervo está habilitada para NFC. Defina o “Prefixo NFC” de uma peça na
        tela Acervo 3D para começar a gerar tags.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <label className="min-w-56 flex-1">
        <span className="mb-1 block text-sm text-muted">Peça do Acervo (habilitada p/ NFC)</span>
        <Combobox
          options={options}
          value={itemId}
          onChange={setItemId}
          placeholder="Escolher peça…"
          aria-label="Peça do Acervo habilitada para NFC"
        />
        {fieldError(gerar.error, "item_id") && (
          <p className="mt-1 text-sm text-red" role="alert">
            {fieldError(gerar.error, "item_id")}
          </p>
        )}
      </label>
      <label className="w-28">
        <span className="mb-1 block text-sm text-muted">Quantidade</span>
        <Input
          type="number"
          min={1}
          max={999}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          aria-invalid={Boolean(fieldError(gerar.error, "quantity"))}
          aria-label="Quantidade de tags"
        />
      </label>
      <Button type="submit" loading={gerar.isPending} disabled={itemId === null}>
        Gerar tags
      </Button>
      {fieldError(gerar.error, "quantity") && (
        <p className="w-full text-sm text-red" role="alert">
          {fieldError(gerar.error, "quantity")}
        </p>
      )}
      {geradas !== null && (
        <p className="w-full text-sm text-green" aria-live="polite">
          {geradas === 1 ? "1 tag gerada" : `${geradas} tags geradas`} — anote o Nº em cada
          tagzinha ao gravar.
        </p>
      )}
    </form>
  );
}
