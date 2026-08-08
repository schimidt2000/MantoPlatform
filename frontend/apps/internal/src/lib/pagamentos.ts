import { formatBRL } from "@manto/money";
import { formatShortDate } from "@manto/ui";
import type {
  BulkPaymentAction,
  PagamentoItem,
  PagamentoItemType,
  PaymentStatus,
} from "./financeiro";

/**
 * Vocabulário visual e de busca da Planilha de Pagamentos (feature 226).
 *
 * Estava tudo dentro de `PagamentosPage.tsx`; saiu para cá quando a planilha ganhou DUAS
 * apresentações do mesmo item — a tabela do desktop e o cartão do celular. Os dois precisam
 * ler a MESMA faixa, o MESMO rótulo e a MESMA cor, senão o cartão do telefone e a linha do
 * computador contariam histórias diferentes sobre o mesmo pagamento (Princípio I).
 */

export const TYPE_LABELS: Record<PagamentoItemType, string> = {
  cache: "Cachê",
  salary: "Salário",
  expense: "Gasto",
  bv: "BV",
  commission: "Comissão",
  recurring: "Recorrente",
};

export const TYPE_BADGE_CLASS: Record<PagamentoItemType, string> = {
  cache: "bg-surface-2 text-muted",
  salary: "bg-gold-soft text-gold-ink",
  expense: "bg-blue-soft text-blue",
  bv: "bg-accent-soft text-accent",
  commission: "bg-green-soft text-green",
  recurring: "bg-gold-soft text-gold-ink",
};

/** Tipos elegíveis para seleção/ação em massa (mesmo escopo de `bulk_payment_action`). */
export const SELECTABLE_TYPES: PagamentoItemType[] = ["cache", "salary", "expense", "commission"];

export function isSelectable(item: PagamentoItem): boolean {
  return SELECTABLE_TYPES.includes(item.type);
}

/**
 * Situações aceitas pelo backend por tipo de item (`_VALID_PAYMENT_STATUS` em
 * `app/api/financeiro_write.py`). Todos os tipos aceitam as mesmas 3 situações (feature 199).
 */
export const STATUS_OPTIONS_BY_TYPE: Record<PagamentoItemType, PaymentStatus[]> = {
  cache: ["nao_pago", "no_banco", "pago"],
  salary: ["nao_pago", "no_banco", "pago"],
  expense: ["nao_pago", "no_banco", "pago"],
  bv: ["nao_pago", "no_banco", "pago"],
  commission: ["nao_pago", "no_banco", "pago"],
  recurring: ["nao_pago", "no_banco", "pago"],
};

/**
 * As 4 faixas que o financeiro enxerga na planilha. É a MESMA classificação que o backend usa
 * para somar `totals` (`_pagamentos` em `app/api/financeiro_read.py`): "pendente" é o que já
 * venceu (`nao_pago` sem `is_future`) e "futuro" é o que ainda vai vencer. Derivar as duas do
 * `is_future` que a API já manda — em vez de recomparar datas no cliente — garante que o filtro
 * do card sempre bata com o valor exibido nele.
 */
export type PagamentoBucket = "pago" | "no_banco" | "pendente" | "futuro";

/** Filtro ativo dos cards de KPI; `null` = "Total no período" (nenhum filtro). */
export type PagamentoFilter = PagamentoBucket | null;

export interface BucketTone {
  /** Nuance de fundo da linha da tabela (e do cartão no celular) — "bate o olho e entende". */
  row: string;
  /** Card selecionado: borda grossa viva + fundo colorido. */
  cardActive: string;
  /** Cor do valor no card e do seletor de situação. */
  text: string;
  /** Seletor de situação da linha. */
  select: string;
}

/**
 * Paleta única por faixa — card de KPI, linha da tabela, cartão do celular e seletor de
 * situação saem daqui, então a cor que o operador clica no card é exatamente a cor das linhas
 * que aparecem.
 *
 * "Futuro" usa `gold` (cor de atenção do design system) e não `amber`: a paleta padrão do
 * Tailwind não combina com o dourado da marca — ver `@manto/ui/tailwind-preset`.
 *
 * As outras três faixas usavam paleta CRUA do Tailwind (`bg-green-50`, `bg-blue-50`,
 * `bg-rose-50`, `border-green-500`...), que é sempre clara e não acompanha o tema: no escuro a
 * tabela ficaria com linhas pastel berrantes sobre o painel escuro, e a faixa "Futuro" seria a
 * única a escurecer. As quatro saem do mesmo vocabulário de token; os valores do tema CLARO dos
 * degraus `-50` são exatamente os HEX que estavam aqui, então o claro não mudou.
 */
export const BUCKET_TONE: Record<PagamentoBucket, BucketTone> = {
  pago: {
    row: "bg-green-50",
    cardActive: "border-green bg-green-50/50 ring-2 ring-green/20",
    text: "text-green",
    select: "border-green bg-green-soft text-green",
  },
  no_banco: {
    row: "bg-blue-50",
    cardActive: "border-blue bg-blue-50/50 ring-2 ring-blue/20",
    text: "text-blue",
    select: "border-blue bg-blue-soft text-blue",
  },
  pendente: {
    row: "bg-red-50",
    cardActive: "border-red bg-red-50/50 ring-2 ring-red/20",
    text: "text-red",
    select: "border-red bg-red-soft text-red",
  },
  futuro: {
    row: "bg-gold-50",
    cardActive: "border-gold bg-gold-50/50 ring-2 ring-gold/20",
    text: "text-gold-ink",
    select: "border-gold bg-gold-soft text-gold-ink",
  },
};

export const BUCKET_LABELS: Record<PagamentoBucket, string> = {
  pago: "Pagos",
  no_banco: "No banco",
  pendente: "Pendentes",
  futuro: "Futuro",
};

/** Ordem dos cards de filtro, depois do card neutro "Total no período". */
export const BUCKET_ORDER: PagamentoBucket[] = ["pago", "no_banco", "pendente", "futuro"];

/** Rótulo do botão de cada ação em lote — a barra flutuante lê daqui. */
export const BULK_ACTION_LABELS: Record<Exclude<BulkPaymentAction, "delete">, string> = {
  pago: "Marcar pago",
  no_banco: "No banco",
  nao_pago: "Não pago",
};

/**
 * Rótulo curto das mesmas ações, para o celular.
 *
 * Com os rótulos longos os botões quebravam em três linhas e a barra fixa comia 146px dos
 * 812px da tela — mais que um cartão inteiro da lista.
 */
export const BULK_ACTION_SHORT_LABELS: Record<Exclude<BulkPaymentAction, "delete">, string> = {
  pago: "Pago",
  no_banco: "Banco",
  nao_pago: "Não pago",
};

export function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

// Vencimento e adiantamento chegam como data pura ("2026-08-05"); `formatShortDate` é a fonte
// única que a monta em horário local — `new Date(iso)` direto lia como UTC e exibia 04/08.
export const formatDate = formatShortDate;

export function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** Data de hoje em "YYYY-MM-DD" (horário local) — valor inicial do campo de adiantamento. */
export function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

/**
 * Mês vizinho no formato "YYYY-MM" — alimenta as setas ‹ › ao lado do campo de mês.
 *
 * A conta passa pelo `Date` de propósito (dia 1, horário local): ele já vira o ano sozinho
 * quando o mês estoura, então dezembro→janeiro não precisa de caso especial aqui.
 */
export function shiftMonth(month: string, delta: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  if (!year || !monthNumber) return month;
  const moved = new Date(year, monthNumber - 1 + delta, 1);
  return `${moved.getFullYear()}-${String(moved.getMonth() + 1).padStart(2, "0")}`;
}

/** "agosto de 2026" — o mês por extenso, para o celular, onde o `input[type=month]` é apertado. */
export function monthLabel(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);
  if (!year || !monthNumber) return month;
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
}

export function itemKey(item: PagamentoItem): string {
  return `${item.type}-${item.id}`;
}

/** Faixa a que o item pertence — fonte única do filtro, da cor da linha e do seletor. */
export function bucketOf(item: PagamentoItem): PagamentoBucket {
  if (item.status === "pago") return "pago";
  if (item.status === "no_banco") return "no_banco";
  return item.is_future ? "futuro" : "pendente";
}

/** Valor cru em formato "1234,56" — o que o operador cola no internet banking. */
export function rawAmount(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

/** Marcas de acento decompostas pelo `normalize("NFD")` (bloco Unicode Combining Diacriticals). */
const DIACRITICS = new RegExp("[\\u0300-\\u036f]", "g");

/** Remove acentos e caixa para a busca — "cachê" casa com "cache", "JOÃO" com "joao". */
export function normalizeSearch(text: string): string {
  return text.normalize("NFD").replace(DIACRITICS, "").toLowerCase();
}

/**
 * Texto pesquisável de um item — a caixa de busca varre isto, não o DOM.
 *
 * A versão Jinja montava o índice lendo o `textContent` das células (`buildRowIndex`), o que
 * amarrava a busca ao layout: a coluna que sumisse no responsivo sairia do índice junto. Aqui
 * o índice vem do DADO, então a mesma busca vale para a tabela do desktop e para o cartão do
 * celular, inclusive para o que o cartão resume.
 *
 * O valor entra duas vezes de propósito: formatado ("1.234,56", como o operador lê na tela) e
 * cru ("1234,56", como ele digita ao conferir o extrato do banco).
 */
export function searchIndexOf(
  item: PagamentoItem,
  statusLabels: Record<string, string>,
): string {
  return normalizeSearch(
    [
      formatDate(item.date),
      item.date ?? "",
      TYPE_LABELS[item.type],
      item.event_title ?? "",
      item.copy_label ?? "",
      item.sublabel ?? "",
      item.person_name ?? "",
      formatBRL(item.amount),
      rawAmount(item.amount),
      item.pix_key,
      item.pix_key_type,
      statusLabels[item.status] ?? item.status,
      item.is_future ? "futuro" : "",
    ].join(" "),
  );
}

/**
 * Termos da busca — cada palavra é uma restrição que se soma (E), não uma alternativa.
 *
 * A versão Jinja casava a frase inteira como substring, então "joao 1500" nunca achava nada
 * (nenhuma célula tem os dois grudados). Buscar por nome + valor é justamente como se confere
 * um pagamento, então aqui as palavras são independentes; com um termo só, o comportamento é
 * idêntico ao de antes.
 */
export function searchTerms(query: string): string[] {
  return normalizeSearch(query.trim()).split(/\s+/).filter(Boolean);
}

export function matchesSearch(index: string, terms: string[]): boolean {
  return terms.every((term) => index.includes(term));
}
