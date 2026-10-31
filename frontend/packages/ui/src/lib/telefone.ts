/**
 * Máscara de telefone para digitação (feature 326): `(11) 98765-4321` enquanto se digita.
 *
 * O servidor normaliza só os dígitos (`app/clientes/importer.normalize_phone`: 10 ou 11 dígitos
 * ganham o 55; de 10 a 13 valem), então a máscara é só apresentação. Número de fora do Brasil
 * chega com `+` ou com mais de 11 dígitos: sem esse escape a máscara cortaria o `+351…` em 11
 * dígitos e gravaria outro telefone.
 */
export function mascaraTelefone(valor: string): string {
  const digitos = valor.replace(/\D/g, "");
  const comDdi = valor.trimStart().startsWith("+") || digitos.length > 11;
  if (!comDdi) return mascaraNacional(digitos);
  if (digitos.startsWith("55") && digitos.length > 2) {
    return `+55 ${mascaraNacional(digitos.slice(2))}`;
  }
  return `+${digitos.slice(0, 15)}`;
}

/** DDD + número: 8 dígitos (fixo) ou 9 (celular) depois do DDD. */
function mascaraNacional(digitos: string): string {
  const d = digitos.slice(0, 11);
  if (d.length > 10) return d.replace(/(\d{2})(\d{5})(\d{1,4})/, "($1) $2-$3");
  if (d.length > 6) return d.replace(/(\d{2})(\d{4})(\d{1,4})/, "($1) $2-$3");
  if (d.length > 2) return d.replace(/(\d{2})(\d+)/, "($1) $2");
  return d;
}
