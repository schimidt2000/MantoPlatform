import { maskCnpj, maskCpf, onlyDigits } from "./formularios";

/**
 * CPF e CNPJ pelos dígitos verificadores (feature 342). Mesma régua de `app/documentos.py`: a tela
 * avisa cedo, o servidor é quem decide.
 */

const CPF_DIGITOS = 11;
const CNPJ_DIGITOS = 14;
const PESOS_CNPJ_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
const PESOS_CNPJ_2 = [6, ...PESOS_CNPJ_1];

/** "000.000.000-00" e parecidos passam na conta, mas não existem. */
function repetido(d: string): boolean {
  return new Set(d).size === 1;
}

function cpfValido(d: string): boolean {
  if (d.length !== CPF_DIGITOS || repetido(d)) return false;
  for (const posicao of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < posicao; i += 1) soma += Number(d[i]) * (posicao + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[posicao])) return false;
  }
  return true;
}

function cnpjValido(d: string): boolean {
  if (d.length !== CNPJ_DIGITOS || repetido(d)) return false;
  const pares: [number[], number][] = [
    [PESOS_CNPJ_1, 12],
    [PESOS_CNPJ_2, 13],
  ];
  for (const [pesos, posicao] of pares) {
    const resto = pesos.reduce((soma, peso, i) => soma + Number(d[i]) * peso, 0) % 11;
    if ((resto < 2 ? 0 : 11 - resto) !== Number(d[posicao])) return false;
  }
  return true;
}

/** CPF (11 dígitos) ou CNPJ (14) com os verificadores corretos. */
export function docValido(valor: string): boolean {
  const d = onlyDigits(valor);
  return d.length === CPF_DIGITOS ? cpfValido(d) : cnpjValido(d);
}

/** O documento tem o tamanho de um CNPJ (não confere os verificadores). */
export function ehCnpj(valor: string | undefined): boolean {
  return onlyDigits(valor ?? "").length === CNPJ_DIGITOS;
}

/** Máscara que acompanha a digitação: até 11 dígitos é CPF, daí em diante CNPJ. */
export function maskCpfCnpj(digitsOnly: string): string {
  return digitsOnly.length <= CPF_DIGITOS ? maskCpf(digitsOnly) : maskCnpj(digitsOnly);
}

export const MENSAGEM_DOC_INVALIDO = "Confira o CNPJ ou CPF: o número não parece válido.";
