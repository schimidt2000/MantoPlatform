/**
 * Peças puras das listas comerciais da Home (features 298 e 299): Formulários, Cobranças e Sem
 * valor usam a MESMA escala de cor e a mesma distância em palavras — o dono pediu "uma escala de
 * cor só, igual nas três listas".
 */

/** Vermelho = agir já; amarelo = atenção; cinza = informação (não conta no total). */
export type Severidade = "vermelho" | "amarelo" | "cinza";

export const SEVERIDADE_TOM: Record<Severidade, "red" | "gold" | "neutral"> = {
  vermelho: "red",
  amarelo: "gold",
  cinza: "neutral",
};

/** Tokens de fundo que acompanham o tema escuro (`theme.css`); cinza não pinta a linha. */
export const SEVERIDADE_FUNDO: Record<Severidade, string> = {
  vermelho: "bg-red-50",
  amarelo: "bg-gold-50",
  cinza: "",
};

/** `01/06` a partir de uma data AAAA-MM-DD (o corte, o vencimento). */
export function diaMes(iso: string | null | undefined): string | null {
  const [, mes, dia] = (iso ?? "").slice(0, 10).split("-");
  return mes && dia ? `${dia}/${mes}` : null;
}

/**
 * Distância até uma data, em palavras — a urgência nunca é dita só pela cor.
 *
 * Os dias vêm calculados no servidor pelo "hoje" de São Paulo. Não é o `formatRelativeDay` da
 * `@manto/ui`: ele diz "ontem/há N dias" e usa o relógio do navegador. `passado` é o verbo do que
 * já aconteceu: "passou" (formulário), "aconteceu" (evento sem valor), "venceu" (cobrança).
 */
export function distanciaDaData(
  dias: number | null | undefined,
  { passado = "passou" }: { passado?: string } = {},
): string | null {
  if (dias == null) return null;
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  if (dias > 1) return `em ${dias} dias`;
  const quantos = Math.abs(dias);
  return `${passado} há ${quantos} dia${quantos !== 1 ? "s" : ""}`;
}
