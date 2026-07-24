import { z } from "zod";

/** Schema Zod compartilhado entre `EventCreatePage` e `EventEditPage` (feature 184) — os campos
 * escalares dos Blocos 2, 4 e 5. Blocos de lista (cliente, elenco, comprovantes, observações) têm
 * validação própria fora do react-hook-form (ver `blockErrors` nas páginas). */
export const eventSchema = z
  .object({
    title: z.string().min(1, "Título obrigatório"),
    event_type: z.string(),
    date: z.string().min(1, "Data obrigatória"),
    start: z.string().min(1, "Informe o horário de início"),
    end: z.string().min(1, "Informe o horário de fim"),
    location: z.string(),
    description: z.string(),
    needs_rehearsal: z.boolean(),
    is_cortesia_permuta: z.boolean(),
    sale_value: z.number(),
    sale_value_gross: z.number(),
    transport_value: z.number(),
    acrescimo_value: z.number(),
    with_invoice: z.boolean(),
    seller_id: z.string().min(1, "Selecione o vendedor responsável"),
    sale_date: z.string(),
    payment_method: z.string(),
    payment_installments: z.string(),
    payment_due_date: z.string(),
  })
  .refine((v) => v.is_cortesia_permuta || v.sale_value_gross > 0, {
    message: "Informe o valor antes do desconto.",
    path: ["sale_value_gross"],
  })
  .refine((v) => v.is_cortesia_permuta || v.sale_value > 0, {
    message: "Informe o valor de venda.",
    path: ["sale_value"],
  })
  .refine(
    (v) =>
      v.payment_method !== "pix_parcelado" ||
      (Number(v.payment_installments) >= 2 && Number(v.payment_installments) <= 12),
    { message: "Informe o número de parcelas (2 a 12).", path: ["payment_installments"] },
  )
  .refine((v) => v.start === "" || v.end === "" || v.start !== v.end, {
    message: "Horário de fim deve ser diferente do início.",
    path: ["end"],
  });

export type EventFormValues = z.infer<typeof eventSchema>;

/** Mapa campo-do-servidor → campo do formulário React, para destacar erros de validação (400). */
export const SERVER_FIELD_MAP: Partial<Record<string, keyof EventFormValues>> = {
  title: "title",
  event_date: "date",
  event_time: "start",
  sale_value_gross: "sale_value_gross",
  sale_value: "sale_value",
  seller_id: "seller_id",
  payment_installments: "payment_installments",
};

/** Ordem visual dos campos obrigatórios, do Bloco 2 ao Bloco 5 — usada para achar o primeiro erro
 * ao falhar o envio (feature 184, US2: auto-scroll). Só os campos escalares validados por
 * `eventSchema` têm regra de obrigatoriedade nesta feature; os blocos de lista (cliente, elenco,
 * comprovantes, observações) não têm mínimo exigido pela spec. */
export const FIELD_ORDER: (keyof EventFormValues)[] = [
  "title",
  "date",
  "start",
  "end",
  "sale_value_gross",
  "sale_value",
  "seller_id",
  "payment_installments",
];

export const DEFAULT_EVENT_FORM_VALUES: EventFormValues = {
  title: "",
  event_type: "",
  date: "",
  start: "",
  end: "",
  location: "",
  description: "",
  needs_rehearsal: false,
  is_cortesia_permuta: false,
  sale_value: 0,
  sale_value_gross: 0,
  transport_value: 0,
  acrescimo_value: 0,
  with_invoice: false,
  seller_id: "",
  sale_date: "",
  payment_method: "",
  payment_installments: "",
  payment_due_date: "",
};
