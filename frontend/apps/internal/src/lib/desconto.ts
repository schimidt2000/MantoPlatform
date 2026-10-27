/**
 * Feature 313 — o desconto negociado: o % como a proposta mostra e a leitura do cheio/PIX de um `Quote`.
 *
 * O texto do % do orçamento vem do servidor (`quote.desconto_pct_texto`, a fonte única); esta regra existe para quem
 * não tem esse texto — o selo "N% de desconto" do valor de venda no evento, que compara o cheio com a venda digitada.
 * É a mesma regra do servidor (`quote_ops.texto_do_percentual`): uma casa, PARA BAIXO, com vírgula e sem ",0" — a
 * proposta nunca promete mais desconto do que dá (4,96% → "4,9").
 */
import type { Quote } from "./orcamento";

export function textoDoPercentual(d: number): string | null {
  // O arredondamento a 6 casas antes do piso evita que 10% achado pelo valor (9,9999999…) vire "9,9".
  const piso = Math.floor(Math.round(d * 1e6) / 1e5) / 10;
  // Abaixo de 0,1% não há o que anunciar: "0% de desconto" é um selo que mente (converge, T055).
  if (piso <= 0) return null;
  const texto = piso.toFixed(1).replace(".", ",");
  return texto.endsWith(",0") ? texto.slice(0, -2) : texto;
}

/**
 * O % de desconto entre o cheio e a venda, ou `null` quando não há desconto (venda ≥ cheio ou cheio vazio).
 *
 * Os dois chegam arredondados ao centavo, e o % exato da proposta pode ficar até meio centavo para qualquer lado:
 * 3.571,43 com 5% vira venda 3.392,86, e a razão dá 4,99998% → "4,9" contra o "5" da proposta. Por isso o % é o
 * maior compatível com o centavo (venda − ½ centavo sobre cheio + ½ centavo) — o selo bate com a proposta, e numa
 * venda digitada à mão a diferença é de milésimos de ponto (converge, T051).
 */
export function percentualDoDesconto(bruto: number | null | undefined, venda: number | null | undefined): number | null {
  if (!bruto || venda == null || venda >= bruto) return null;
  return (1 - (venda - 0.005) / (bruto + 0.005)) * 100;
}

export type ColunaDoQuote = "1h" | "2h" | "3h" | "4h" | "custom";

function chave(prefixo: string, coluna: ColunaDoQuote): string {
  return `${prefixo}_${coluna}`;
}

/** O preço cheio de uma coluna; quote antigo (sem a chave) = o próprio total. */
export function brutoDe(quote: Quote, coluna: ColunaDoQuote): number | null {
  const total = (quote as unknown as Record<string, number | null | undefined>)[chave("total", coluna)];
  const bruto = (quote as unknown as Record<string, number | null | undefined>)[chave("bruto", coluna)];
  return bruto ?? total ?? null;
}

/** O PIX à vista de uma coluna, só quando o servidor mandou (quote antigo: `null` — a tela não faz a conta). */
export function pixDe(quote: Quote, coluna: ColunaDoQuote): number | null {
  return (quote as unknown as Record<string, number | null | undefined>)[chave("pix", coluna)] ?? null;
}

/** O BV a repassar (com o desconto) e no PIX, só quando o servidor mandou. */
export function bvDe(quote: Quote, coluna: ColunaDoQuote, noPix = false): number | null {
  return (quote as unknown as Record<string, number | null | undefined>)[chave(noPix ? "bv_pix" : "bv", coluna)] ?? null;
}

/** O orçamento tem BV? (pelos `bv_*` que o servidor mandou; quote antigo: não sabe, `false`.) */
export function temBv(quote: Quote): boolean {
  return (["1h", "2h", "3h", "4h", "custom"] as const).some((c) => bvDe(quote, c) != null);
}

/** As linhas do BV a repassar de uma coluna: com desconto e, quando o PIX dá outro valor, a do PIX. */
export function linhasDoBv(quote: Quote, coluna: ColunaDoQuote, brl: (v: number) => string): string[] {
  const bv = bvDe(quote, coluna);
  if (bv == null) return [];
  const noPix = bvDe(quote, coluna, true);
  return noPix != null && Math.abs(noPix - bv) >= 0.005
    ? [`BV a repassar: ${brl(bv)}`, `BV no PIX: ${brl(noPix)}`]
    : [`BV a repassar: ${brl(bv)}`];
}

/** Há desconto negociado neste quote? (quote antigo: não.) */
export function temDesconto(quote: Quote): boolean {
  return Boolean(quote.desconto_pct);
}
