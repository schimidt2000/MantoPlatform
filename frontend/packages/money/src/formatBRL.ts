/**
 * Formatação monetária no padrão brasileiro (fonte única — Princípio VII da constituição).
 *
 * Porta a lógica de `app/static/js/money-mask.js` para TypeScript. Milhar com `.`,
 * decimal com `,`, sempre duas casas. Ex.: 4000 -> "4.000,00", 1234.56 -> "1.234,56".
 */
const BRL_FORMATTER = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Formata um número no padrão brasileiro, sem o prefixo "R$".
 *
 * @param value Valor numérico (o valor "cru" que vive no backend/JSON).
 * @returns String formatada, ex.: "1.234,56".
 */
export function formatBRL(value: number): string {
  if (!Number.isFinite(value)) {
    return BRL_FORMATTER.format(0);
  }
  return BRL_FORMATTER.format(value);
}
