/**
 * Parsing do padrão brasileiro de volta para número (fonte única — Princípio VII).
 *
 * A máscara é só de apresentação; o valor enviado no corpo JSON é sempre numérico.
 */

/**
 * Converte uma string mascarada em pt-BR ("1.234,56") para número (1234.56).
 *
 * Tolerante a entrada parcial durante a digitação; retorna 0 para entrada vazia.
 *
 * @param masked String formatada no padrão brasileiro.
 * @returns Valor numérico.
 */
export function parseBRL(masked: string): number {
  if (!masked) {
    return 0;
  }
  const normalized = masked
    .replace(/\s/g, "")
    .replace(/\./g, "")
    .replace(",", ".")
    .replace(/[^0-9.-]/g, "");
  const value = Number.parseFloat(normalized);
  return Number.isFinite(value) ? value : 0;
}

/**
 * Interpreta uma sequência de dígitos como centavos (comportamento de máscara ao digitar).
 *
 * "123456" -> 1234.56. É o modo "os dois últimos dígitos são os centavos" usado pela
 * máscara que formata enquanto o usuário digita, sem exigir que ele digite os separadores.
 *
 * @param raw String qualquer; apenas os dígitos são considerados.
 * @returns Valor numérico com duas casas decimais.
 */
export function digitsToNumber(raw: string): number {
  const digits = raw.replace(/\D/g, "");
  if (!digits) {
    return 0;
  }
  return Number.parseInt(digits, 10) / 100;
}
