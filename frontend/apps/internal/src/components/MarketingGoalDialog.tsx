import { useState } from "react";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  type ComboboxOption,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import {
  useCreateMarketingGoal,
  useMarketingOptions,
  useUpdateMarketingGoal,
  type MarketingCatalogItemRef,
  type MarketingGoal,
} from "../lib/marketing";

const INPUT_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Intervalos combinados em reunião — atalhos para não digitar o número mais comum. */
const INTERVAL_PRESETS = [7, 15, 30];

function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

function temaOptions(temas: MarketingCatalogItemRef[]): ComboboxOption[] {
  return temas.map((tema) => ({
    value: String(tema.id),
    label: tema.name,
    imageUrl: assetUrl(tema.cover_url) ?? null,
    imageShape: "square" as const,
    fallbackIcon: "🎭",
  }));
}

interface MarketingGoalFormProps {
  goal?: MarketingGoal;
  onSaved: () => void;
  onCancel: () => void;
}

/**
 * Formulário da meta de frequência.
 *
 * Vincular o **Tema do catálogo** é o que dá precisão ao motor: com Tema, o casamento com os
 * posts publicados é exato; sem Tema, o servidor cai no casamento pelo nome dentro do título do
 * post (bom para assuntos que não existem no catálogo, como "Bastidores").
 */
function MarketingGoalForm({ goal, onSaved, onCancel }: MarketingGoalFormProps) {
  const isEdit = goal !== undefined;
  const options = useMarketingOptions();
  const create = useCreateMarketingGoal();
  const update = useUpdateMarketingGoal();
  const mutation = isEdit ? update : create;
  const error = mutation.error;

  const [name, setName] = useState(goal?.name ?? "");
  const [interval, setInterval] = useState(String(goal?.target_interval_days ?? 15));
  const [temaId, setTemaId] = useState<string | null>(
    goal?.catalog_item_id ? String(goal.catalog_item_id) : null,
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const input = {
      name: name.trim(),
      target_interval_days: Number(interval),
      catalog_item_id: temaId ? Number(temaId) : null,
    };
    if (isEdit) {
      update.mutate({ id: goal.id, input }, { onSuccess: onSaved });
      return;
    }
    create.mutate(input, { onSuccess: onSaved });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-muted">Assunto da meta *</span>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ex.: Festa de 15 Anos"
          aria-invalid={Boolean(fieldError(error, "name"))}
          aria-label="Assunto da meta"
        />
        {fieldError(error, "name") && (
          <span className="mt-1 block text-sm text-red" role="alert">
            {fieldError(error, "name")}
          </span>
        )}
      </label>

      <label className="block">
        <span className="mb-1 block text-xs font-medium text-muted">
          Postar a cada quantos dias? *
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="number"
            min={1}
            className={`${INPUT_CLASS} max-w-[120px]`}
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            aria-invalid={Boolean(fieldError(error, "target_interval_days"))}
            aria-label="Intervalo alvo em dias"
          />
          {INTERVAL_PRESETS.map((preset) => (
            <Button
              key={preset}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInterval(String(preset))}
            >
              {preset} dias
            </Button>
          ))}
        </div>
        {fieldError(error, "target_interval_days") && (
          <span className="mt-1 block text-sm text-red" role="alert">
            {fieldError(error, "target_interval_days")}
          </span>
        )}
      </label>

      <label className="block">
        <span className="mb-1 block text-xs font-medium text-muted">
          Tema do catálogo (opcional, deixa o cálculo exato)
        </span>
        <Combobox
          aria-label="Buscar Tema do catálogo"
          placeholder="🔍 Buscar Tema do catálogo…"
          emptyMessage="Nenhum Tema encontrado."
          options={temaOptions(options.data?.temas ?? [])}
          loading={options.isLoading}
          value={temaId}
          invalid={Boolean(fieldError(error, "catalog_item_id"))}
          onChange={(next) => setTemaId(next)}
        />
        {fieldError(error, "catalog_item_id") && (
          <span className="mt-1 block text-sm text-red" role="alert">
            {fieldError(error, "catalog_item_id")}
          </span>
        )}
      </label>

      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        {mutation.isError && (
          <span className="mr-auto text-sm text-red" role="alert">
            {error instanceof Error ? error.message : "Não foi possível salvar a meta."}
          </span>
        )}
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={mutation.isPending}>
          {isEdit ? "Salvar meta" : "Criar meta"}
        </Button>
      </div>
    </form>
  );
}

export interface MarketingGoalDialogProps {
  /** Meta em edição; `null` com `open` = criação. */
  goal: MarketingGoal | null;
  open: boolean;
  onClose: () => void;
}

/** Dialog de criação/edição de uma meta de frequência (feature 204). */
export function MarketingGoalDialog({ goal, open, onClose }: MarketingGoalDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{goal ? "Editar meta de frequência" : "Nova meta de frequência"}</DialogTitle>
          <DialogDescription>
            A regra combinada em reunião — ex.: “Festa de 15 Anos a cada 15 dias”.
          </DialogDescription>
        </DialogHeader>
        {/* `key` remonta o formulário ao trocar de meta — zera o estado sem `useEffect`. */}
        <MarketingGoalForm
          key={goal?.id ?? "nova"}
          goal={goal ?? undefined}
          onSaved={onClose}
          onCancel={onClose}
        />
      </DialogContent>
    </Dialog>
  );
}
