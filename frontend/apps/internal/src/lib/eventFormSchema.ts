import { z } from "zod";
import {
  MENSAGEM_DOC_INVALIDO,
  MENSAGEM_MUNICIPIO,
  dadosDoEvento,
  docValido,
  notaInput,
  type DadosDaNotaDoEvento,
  type NotaInput,
} from "./notaFiscal";

/** O que o campo de valor diz quando o valor não fecha uma venda (feature 299) — o texto do servidor. */
export const MENSAGEM_VALOR_A_DEFINIR = "Informe o valor de venda ou marque “Valor a definir”.";

interface RegraDeValor {
  is_cortesia_permuta: boolean;
  valor_a_definir: boolean;
  satelite: boolean;
  valor_original: number | null;
}

/**
 * O campo de valor aceita (feature 299, FR-014)? Cortesia, "Valor a definir" e o outro evento de
 * um grupo não pedem valor; fora isso, R$ 1,00 ou mais — o R$ 0,01 de "segurar a data" acabou.
 *
 * Exceção (R32), campo a campo e igual à do servidor: o evento que JÁ está com valor simbólico
 * salva outras mudanças mantendo o valor (vazio e zero contam como o mesmo) — a troca de título de
 * um evento antigo de R$ 0,01 não pode travar.
 */
function valorAceito(v: RegraDeValor, valor: number, original: number | null): boolean {
  if (v.is_cortesia_permuta || v.valor_a_definir || v.satelite || valor >= 1) return true;
  const simbolicoGravado = v.valor_original != null && v.valor_original > 0 && v.valor_original < 1;
  return simbolicoGravado && valor === (original ?? 0);
}

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
    seller_id: z.string(),
    sale_date: z.string(),
    payment_method: z.string(),
    payment_installments: z.string(),
    payment_due_date: z.string(),
    // Feature 323 — os dados da nota, planos (o nome é o do `fields` do servidor). Só valem com o
    // chip ligado, mas ficam no formulário ao desligar: religar recupera o que o cliente pediu.
    nota_tomador_doc: z.string(),
    nota_iss_retido: z.boolean(),
    nota_municipio: z.string(),
    nota_referencia: z.string(),
    nota_observacoes: z.string(),
    // Feature 299 — campos da tela, não do banco: a marca "Valor a definir" (vai no corpo, mas o
    // servidor não a grava), os valores que o evento já tinha (para a exceção do R32) e se o
    // evento é outro evento de um grupo (a venda mora no principal).
    valor_a_definir: z.boolean(),
    valor_original: z.number().nullable(),
    valor_original_bruto: z.number().nullable(),
    satelite: z.boolean(),
  })
  .refine((v) => valorAceito(v, v.sale_value_gross, v.valor_original_bruto), {
    message: MENSAGEM_VALOR_A_DEFINIR,
    path: ["sale_value_gross"],
  })
  .refine((v) => valorAceito(v, v.sale_value, v.valor_original), {
    message: MENSAGEM_VALOR_A_DEFINIR,
    path: ["sale_value"],
  })
  // O vendedor continua obrigatório com ou sem valor (FR-016) — menos no outro evento de um
  // grupo, onde nada da venda é gravado.
  .refine((v) => v.satelite || v.seller_id !== "", {
    message: "Selecione o vendedor responsável",
    path: ["seller_id"],
  })
  .refine(
    (v) =>
      v.payment_method !== "pix_parcelado" ||
      (Number(v.payment_installments) >= 2 && Number(v.payment_installments) <= 12),
    { message: "Informe o número de parcelas (2 a 12).", path: ["payment_installments"] },
  )
  .refine((v) => !v.with_invoice || docValido(v.nota_tomador_doc), {
    message: MENSAGEM_DOC_INVALIDO,
    path: ["nota_tomador_doc"],
  })
  .refine((v) => !v.with_invoice || !v.nota_iss_retido || v.nota_municipio.trim() !== "", {
    message: MENSAGEM_MUNICIPIO,
    path: ["nota_municipio"],
  })
  .refine((v) => v.start === "" || v.end === "" || v.start !== v.end, {
    message: "O horário de fim deve ser diferente do início.",
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
  nota_tomador_doc: "nota_tomador_doc",
  nota_municipio: "nota_municipio",
  nota_observacoes: "nota_observacoes",
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
  "nota_tomador_doc",
  "nota_municipio",
  "nota_observacoes",
  "seller_id",
  "payment_installments",
];

/**
 * O primeiro campo (na ordem da tela) apontado por um 400 do servidor — para o foco chegar até ele
 * (feature 299, Princípio V: bloquear em silêncio é proibido). `undefined` se nenhum é da tela.
 */
export function primeiroCampoDoErro(fields: Record<string, string>): keyof EventFormValues | undefined {
  const campos = new Set(Object.keys(fields).map((campo) => SERVER_FIELD_MAP[campo]));
  return FIELD_ORDER.find((campo) => campos.has(campo));
}

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
  nota_tomador_doc: "",
  nota_iss_retido: false,
  nota_municipio: "",
  nota_referencia: "",
  nota_observacoes: "",
  valor_a_definir: false,
  valor_original: null,
  valor_original_bruto: null,
  satelite: false,
};

/** Feature 323: os dados da nota gravados → os campos do formulário (vazio quando não há). */
export function camposDaNota(
  nota?: DadosDaNotaDoEvento | null,
): Pick<
  EventFormValues,
  "nota_tomador_doc" | "nota_iss_retido" | "nota_municipio" | "nota_referencia" | "nota_observacoes"
> {
  const d = dadosDoEvento(nota);
  return {
    nota_tomador_doc: d.tomador_doc,
    nota_iss_retido: d.iss_retido,
    nota_municipio: d.municipio,
    nota_referencia: d.referencia,
    nota_observacoes: d.observacoes,
  };
}

/**
 * Feature 323: a chave `nota` do corpo — só com o chip ligado. Sem a chave o servidor não mexe nos
 * dados gravados, e o campo escondido (chip desligado) nunca vira um 400 que a pessoa não vê.
 */
export function notaDoFormulario(v: EventFormValues): NotaInput | undefined {
  if (!v.with_invoice) return undefined;
  return notaInput({
    tomador_doc: v.nota_tomador_doc,
    iss_retido: v.nota_iss_retido,
    municipio: v.nota_municipio,
    referencia: v.nota_referencia,
    observacoes: v.nota_observacoes,
  });
}
