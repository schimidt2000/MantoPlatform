import { Controller, useFormContext } from "react-hook-form";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { MoneyInput, formatBRL } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import { percentualDoDesconto, textoDoPercentual } from "../../lib/desconto";
import type { DadosDaNota } from "../../lib/notaFiscal";
import { DadosDaNotaCampos } from "./DadosDaNotaCampos";
import { FIELD, FIELD_ERROR, LABEL, FieldError, BlockCard } from "./shared";

/** Campo da tela → campo do formulário (os nomes do formulário são os do `fields` do servidor). */
const CAMPO_DA_NOTA = {
  tomador_doc: "nota_tomador_doc",
  iss_retido: "nota_iss_retido",
  municipio: "nota_municipio",
  referencia: "nota_referencia",
  observacoes: "nota_observacoes",
} as const;

const CHIP = "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors";
const CHIP_LIGADO = "border-accent bg-accent-soft text-accent-dark";
const CHIP_DESLIGADO = "border-line bg-panel text-ink";

export interface ValoresBlockProps {
  sellers: { id: number; name: string }[];
  /** Feature 299: o evento é outro evento de um grupo — a venda mora no principal. */
  satelite?: boolean;
  /** O principal do grupo, para o link (só no satélite). */
  principal?: { id: number; title: string } | null;
  /**
   * Hotfix 215b: o evento já tem vendedor e quem edita não pode trocá-lo (só Financeiro e
   * Superadmin). O nome aparece no lugar do seletor; o valor gravado segue no formulário.
   */
  vendedorTravado?: string | null;
  /** Feature 323: o CNPJ/CPF do cadastro do cliente, que vale com o campo do tomador em branco. */
  docDoCliente?: string | null;
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
        . Neste formulário, só os dados deste evento são salvos.
      </p>
    </BlockCard>
  );
}

/** Bloco 4 — Valores e comissões (feature 184; "Valor a definir" na 299). */
export function ValoresBlock({
  sellers,
  satelite = false,
  principal = null,
  vendedorTravado = null,
  docDoCliente = null,
}: ValoresBlockProps) {
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
  const dadosDaNota: DadosDaNota = {
    tomador_doc: watch("nota_tomador_doc"),
    iss_retido: watch("nota_iss_retido"),
    municipio: watch("nota_municipio"),
    referencia: watch("nota_referencia"),
    observacoes: watch("nota_observacoes"),
  };
  const alterarNota = (patch: Partial<DadosDaNota>) => {
    for (const [chave, valor] of Object.entries(patch) as [keyof DadosDaNota, string | boolean][]) {
      const campo = CAMPO_DA_NOTA[chave];
      setValue(campo, valor as never, { shouldDirty: true });
      clearErrors(campo);
    }
  };
  const gross = watch("sale_value_gross");
  const finalValue = watch("sale_value");
  const valorGravado = watch("valor_original");
  // Feature 313 (FR-022): o % pela mesma regra da proposta (uma casa, para baixo) — 4,96% sai "4,9", nunca "5,0".
  const discountPct = percentualDoDesconto(gross, finalValue) ?? 0;

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
          <p className="text-muted">O evento fica em “Sem valor”, na Home, até alguém inserir o valor.</p>
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
                <p className="mt-1 text-xs text-muted">Valor total cobrado da cliente.</p>
                <FieldError message={errors.sale_value?.message} />
              </div>
            </div>
            {discountPct > 0 && textoDoPercentual(discountPct) && (
              <span className="inline-flex items-center rounded-full bg-green-soft px-2.5 py-1 text-xs font-medium text-green">
                {textoDoPercentual(discountPct)}% de desconto
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

      {/* Feature 323: o pedido da nota leva o que a emissão precisa. */}
      <AnimatePresence initial={false}>
        {withInvoice && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <DadosDaNotaCampos
              valor={dadosDaNota}
              onChange={alterarNota}
              erros={{
                nota_tomador_doc: errors.nota_tomador_doc?.message,
                nota_municipio: errors.nota_municipio?.message,
                nota_observacoes: errors.nota_observacoes?.message,
              }}
              docDoCliente={docDoCliente}
              refDoc={register("nota_tomador_doc").ref}
              refMunicipio={register("nota_municipio").ref}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <div>
        <label className={LABEL} htmlFor="seller_id">
          Vendedor responsável *
        </label>
        {vendedorTravado ? (
          // Sem `register`: o campo desabilitado chegaria vazio no envio e a API recusaria a troca.
          // O valor gravado continua nos `defaultValues` do formulário e vai igual.
          <>
            <p id="seller_id" className={`${FIELD} flex items-center bg-surface-2 text-muted`}>
              {vendedorTravado}
            </p>
            <p className="mt-1 text-xs text-muted">
              Só o Financeiro ou o Superadmin troca o vendedor.
            </p>
          </>
        ) : (
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
        )}
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
