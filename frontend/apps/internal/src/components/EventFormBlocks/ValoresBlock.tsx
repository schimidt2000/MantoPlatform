import { Controller, useFormContext } from "react-hook-form";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MoneyInput, formatBRL } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import { FIELD, FIELD_ERROR, LABEL, FieldError, BlockCard } from "./shared";

const CHIP = "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors";
const CHIP_LIGADO = "border-accent bg-accent-soft text-accent-dark";
const CHIP_DESLIGADO = "border-line bg-panel text-ink";

export interface ValoresBlockProps {
  sellers: { id: number; name: string }[];
  /** Feature 299: o evento é outro evento de um grupo — a venda mora no principal. */
  satelite?: boolean;
  /** O principal do grupo, para o link (só no satélite). */
  principal?: { id: number; title: string } | null;
}

/**
 * No outro evento de um grupo, nada da venda é gravado (feature 299): a marca "Valor a definir"
 * vem marcada e travada, e o bloco aponta para o principal, onde a venda mora.
 */
function VendaNoPrincipal({ principal }: { principal: { id: number; title: string } | null }) {
  return (
    <BlockCard title="Valores e comissões" id="bloco-valores">
      <button type="button" disabled aria-pressed className={`${CHIP} ${CHIP_LIGADO} cursor-not-allowed`}>
        ✓ Valor a definir
      </button>
      <p className="text-sm text-muted">
        A venda deste grupo mora no evento principal
        {principal ? (
          <>
            :{" "}
            <Link to={`/events/${principal.id}?aba=comercial`} className="break-words text-blue underline">
              {principal.title}
            </Link>
          </>
        ) : null}
        . Aqui salvam só os dados deste evento.
      </p>
    </BlockCard>
  );
}

/** Bloco 4 — Valores e comissões (feature 184; "Valor a definir" na 299). */
export function ValoresBlock({ sellers, satelite = false, principal = null }: ValoresBlockProps) {
  const {
    register,
    watch,
    setValue,
    clearErrors,
    control,
    formState: { errors },
  } = useFormContext<EventFormValues>();
  const reduceMotion = useReducedMotion();

  const isCortesia = watch("is_cortesia_permuta");
  const aDefinir = watch("valor_a_definir");
  const withInvoice = watch("with_invoice");
  const gross = watch("sale_value_gross");
  const finalValue = watch("sale_value");
  const valorGravado = watch("valor_original");
  const discountPct = gross > 0 && finalValue < gross ? ((gross - finalValue) / gross) * 100 : 0;

  if (satelite) return <VendaNoPrincipal principal={principal} />;

  // Cortesia e "Valor a definir" são excludentes — no servidor a cortesia vence a marca.
  const alternarCortesia = () => {
    setValue("is_cortesia_permuta", !isCortesia);
    if (!isCortesia) setValue("valor_a_definir", false);
    clearErrors(["sale_value", "sale_value_gross"]);
  };
  const alternarADefinir = () => {
    setValue("valor_a_definir", !aDefinir);
    if (!aDefinir) setValue("is_cortesia_permuta", false);
    clearErrors(["sale_value", "sale_value_gross"]);
  };

  return (
    <BlockCard title="Valores e comissões" id="bloco-valores">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={alternarCortesia}
          className={`${CHIP} ${isCortesia ? CHIP_LIGADO : CHIP_DESLIGADO}`}
          aria-pressed={isCortesia}
        >
          {isCortesia ? "✓ " : ""}Cortesia / permuta (sem venda)
        </button>
        <button
          type="button"
          onClick={alternarADefinir}
          className={`${CHIP} ${aDefinir ? CHIP_LIGADO : CHIP_DESLIGADO}`}
          aria-pressed={aDefinir}
        >
          {aDefinir ? "✓ " : ""}Valor a definir
        </button>
      </div>
      {isCortesia && (
        <p className="text-xs text-muted">
          Evento sem venda em dinheiro — os valores abaixo não são necessários; a venda é
          registrada como R$ 0.
        </p>
      )}
      {aDefinir && (
        <div className="space-y-1 text-xs">
          <p className="text-muted">O evento fica em “Sem valor”, na Home, até alguém pôr o valor.</p>
          {/* Aviso no lugar (e não depois de salvar): marcar num evento que já tinha valor apaga o
              valor e cancela a comissão a pagar. A comissão já paga não muda. */}
          {valorGravado != null && valorGravado >= 1 && (
            <p className="text-red">
              O valor de R$ {formatBRL(valorGravado)} será apagado e a comissão a pagar, cancelada.
            </p>
          )}
        </div>
      )}

      <AnimatePresence initial={false}>
        {!isCortesia && !aDefinir && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="space-y-3 overflow-hidden"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              {/* `Controller` passa `id` e `ref` ao `MoneyInput`: sem eles o `setFocus` do erro não
                  chegava ao campo de valor (feature 299 — "o campo aponta e recebe o foco"). */}
              <div>
                <label className={LABEL} htmlFor="sale_value_gross">
                  Valor antes do desconto (R$) *
                </label>
                <Controller
                  name="sale_value_gross"
                  control={control}
                  render={({ field }) => (
                    <MoneyInput
                      id="sale_value_gross"
                      ref={field.ref}
                      name={field.name}
                      onBlur={field.onBlur}
                      className={errors.sale_value_gross ? FIELD_ERROR : FIELD}
                      value={field.value}
                      onValueChange={(v) => field.onChange(v)}
                    />
                  )}
                />
                <p className="mt-1 text-xs text-muted">Preço cheio, sem desconto.</p>
                <FieldError message={errors.sale_value_gross?.message} />
              </div>
              <div>
                <label className={LABEL} htmlFor="sale_value">
                  Valor de venda (R$) *
                </label>
                <Controller
                  name="sale_value"
                  control={control}
                  render={({ field }) => (
                    <MoneyInput
                      id="sale_value"
                      ref={field.ref}
                      name={field.name}
                      onBlur={field.onBlur}
                      className={errors.sale_value ? FIELD_ERROR : FIELD}
                      value={field.value}
                      onValueChange={(v) => field.onChange(v)}
                    />
                  )}
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
        className={`${CHIP} ${withInvoice ? CHIP_LIGADO : CHIP_DESLIGADO}`}
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
