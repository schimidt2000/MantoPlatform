import { useRef, type ReactNode } from "react";
import { useFormContext } from "react-hook-form";
import { Button } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import type { PendingPaymentProof } from "../../lib/eventCreate";
import { FIELD, FIELD_ERROR, HELP, LABEL, FieldError, BlockCard } from "./shared";

const PAYMENT_METHODS = [
  { value: "avista", label: "À vista (PIX)" },
  { value: "pix_parcelado", label: "Dividido no PIX" },
  { value: "faturado", label: "Faturado" },
  { value: "cartao", label: "Cartão de Crédito" },
];

export interface PagamentoBlockProps {
  proofs: PendingPaymentProof[];
  onProofsChange: (next: PendingPaymentProof[]) => void;
  /** Resumo dos comprovantes já salvos (feature 184, edição) — gestão completa (editar valor,
   * excluir) continua na tela de detalhe do evento. */
  existingNote?: ReactNode;
}

/** Bloco 5 — Forma de pagamento e comprovantes (feature 184). */
export function PagamentoBlock({ proofs, onProofsChange, existingNote }: PagamentoBlockProps) {
  const {
    register,
    watch,
    setValue,
    formState: { errors },
  } = useFormContext<EventFormValues>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const paymentMethod = watch("payment_method");

  const addProofFile = (file: File | null) => {
    if (!file) return;
    onProofsChange([...proofs, { file, amount: 0 }]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const updateProofAmount = (index: number, amount: number) =>
    onProofsChange(proofs.map((p, i) => (i === index ? { ...p, amount } : p)));

  const removeProof = (index: number) => onProofsChange(proofs.filter((_, i) => i !== index));

  return (
    <BlockCard title="Forma de pagamento e comprovantes" id="bloco-pagamento">
      <div className="flex flex-wrap gap-2">
        {PAYMENT_METHODS.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => setValue("payment_method", m.value)}
            className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
              paymentMethod === m.value
                ? "border-accent bg-accent-soft text-accent-dark"
                : "border-line bg-panel text-ink"
            }`}
            aria-pressed={paymentMethod === m.value}
          >
            {m.label}
          </button>
        ))}
      </div>

      {paymentMethod === "pix_parcelado" && (
        <div>
          <label className={LABEL} htmlFor="payment_installments">
            Quantas parcelas? (2 a 12) *
          </label>
          <input
            id="payment_installments"
            type="number"
            min={2}
            max={12}
            className={errors.payment_installments ? FIELD_ERROR : FIELD}
            {...register("payment_installments")}
          />
          <FieldError message={errors.payment_installments?.message} />
        </div>
      )}
      {paymentMethod === "faturado" && (
        <div>
          <label className={LABEL} htmlFor="payment_due_date">
            Data de pagamento
          </label>
          <input
            id="payment_due_date"
            type="date"
            className={FIELD}
            {...register("payment_due_date")}
          />
        </div>
      )}

      <div className="border-t border-line pt-3">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
          Comprovantes de pagamento
        </p>
        {existingNote}
        {proofs.length > 0 && (
          <ul className="mb-2 space-y-2">
            {proofs.map((p, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-sm text-ink">{p.file.name}</span>
                <MoneyInput
                  className="h-9 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  value={p.amount}
                  onValueChange={(v) => updateProofAmount(i, v)}
                  aria-label="Valor R$"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeProof(i)}
                  aria-label="Remover comprovante"
                >
                  ✕
                </Button>
              </li>
            ))}
          </ul>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,image/jpeg,image/png"
          className="hidden"
          onChange={(e) => addProofFile(e.target.files?.[0] ?? null)}
        />
        <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
          + Adicionar comprovante
        </Button>
        <p className={HELP}>PDF, JPG ou PNG — máx. 20 MB por arquivo.</p>
      </div>
    </BlockCard>
  );
}
