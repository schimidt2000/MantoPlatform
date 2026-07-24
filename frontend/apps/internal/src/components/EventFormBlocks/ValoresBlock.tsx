import { useFormContext } from "react-hook-form";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MoneyInput } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import { FIELD, FIELD_ERROR, LABEL, FieldError, BlockCard } from "./shared";

export interface ValoresBlockProps {
  sellers: { id: number; name: string }[];
}

/** Bloco 4 — Valores e comissões (feature 184). */
export function ValoresBlock({ sellers }: ValoresBlockProps) {
  const {
    register,
    watch,
    setValue,
    formState: { errors },
  } = useFormContext<EventFormValues>();
  const reduceMotion = useReducedMotion();

  const isCortesia = watch("is_cortesia_permuta");
  const withInvoice = watch("with_invoice");
  const gross = watch("sale_value_gross");
  const finalValue = watch("sale_value");
  const discountPct = gross > 0 && finalValue < gross ? ((gross - finalValue) / gross) * 100 : 0;

  return (
    <BlockCard title="Valores e comissões" id="bloco-valores">
      <button
        type="button"
        onClick={() => setValue("is_cortesia_permuta", !isCortesia)}
        className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
          isCortesia
            ? "border-accent bg-accent-soft text-accent-dark"
            : "border-line bg-panel text-ink"
        }`}
        aria-pressed={isCortesia}
      >
        {isCortesia ? "✓ " : ""}Cortesia / permuta (sem venda)
      </button>
      {isCortesia && (
        <p className="text-xs text-muted">
          Evento sem venda em dinheiro — os valores abaixo não são necessários; a venda é
          registrada como R$ 0.
        </p>
      )}

      <AnimatePresence initial={false}>
        {!isCortesia && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="space-y-3 overflow-hidden"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Valor antes do desconto (R$) *</label>
                <MoneyInput
                  className={errors.sale_value_gross ? FIELD_ERROR : FIELD}
                  value={watch("sale_value_gross")}
                  onValueChange={(v) => setValue("sale_value_gross", v, { shouldValidate: true })}
                />
                <p className="mt-1 text-xs text-muted">Preço cheio, sem desconto.</p>
                <FieldError message={errors.sale_value_gross?.message} />
              </div>
              <div>
                <label className={LABEL}>Valor de venda (R$) *</label>
                <MoneyInput
                  className={errors.sale_value ? FIELD_ERROR : FIELD}
                  value={watch("sale_value")}
                  onValueChange={(v) => setValue("sale_value", v, { shouldValidate: true })}
                />
                <p className="mt-1 text-xs text-muted">Valor total cobrado do cliente.</p>
                <FieldError message={errors.sale_value?.message} />
              </div>
            </div>
            {discountPct > 0 && (
              <span className="inline-flex items-center rounded-full bg-green-soft px-2.5 py-1 text-xs font-medium text-green">
                {discountPct.toFixed(1)}% de desconto
              </span>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL}>Transporte (R$)</label>
          <MoneyInput
            className={FIELD}
            value={watch("transport_value")}
            onValueChange={(v) => setValue("transport_value", v)}
          />
          <p className="mt-1 text-xs text-muted">Separado para cálculo de comissão.</p>
        </div>
        <div>
          <label className={LABEL}>Acréscimo (R$)</label>
          <MoneyInput
            className={FIELD}
            value={watch("acrescimo_value")}
            onValueChange={(v) => setValue("acrescimo_value", v)}
          />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setValue("with_invoice", !withInvoice)}
        className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
          withInvoice
            ? "border-accent bg-accent-soft text-accent-dark"
            : "border-line bg-panel text-ink"
        }`}
        aria-pressed={withInvoice}
      >
        {withInvoice ? "✓ " : ""}Precisa de nota fiscal
      </button>

      <div>
        <label className={LABEL} htmlFor="seller_id">
          Vendedor responsável *
        </label>
        <select
          id="seller_id"
          className={errors.seller_id ? FIELD_ERROR : FIELD}
          {...register("seller_id")}
        >
          <option value="">— Selecionar —</option>
          {sellers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <FieldError message={errors.seller_id?.message} />
      </div>
      <div>
        <label className={LABEL} htmlFor="sale_date">
          Data da venda *
        </label>
        <input id="sale_date" type="date" className={FIELD} {...register("sale_date")} />
        <p className="mt-1 text-xs text-muted">Usada para calcular comissão do mês.</p>
      </div>
    </BlockCard>
  );
}
