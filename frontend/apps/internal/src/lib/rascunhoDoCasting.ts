/**
 * Rascunho do card do Casting (hotfix 356): o talento e o cachê digitados e ainda não salvos.
 *
 * Cada card tem o próprio "Salvar", e até aqui o que se digitava morava só no estado do componente:
 * trocar de aba (a aba Produção desmonta), ir para outra tela ou fechar o app apagava o valor sem
 * aviso nenhum. Foi o caso do evento 1516: o 850 nunca chegou ao servidor, e o dono achou que o
 * sistema tinha desfeito a alteração. O rascunho fica no `localStorage` (no iPhone com o sistema na
 * Tela de Início, o app fechado em segundo plano perde a memória da página) e só vale enquanto a
 * vaga no servidor continua como estava quando a pessoa começou a digitar (`base`): se alguém
 * salvou outra coisa depois, o rascunho velho é descartado em vez de desfazer o que foi salvo.
 */

/** O que o card mostra e envia no "Salvar". */
export interface ValoresDoCard {
  talentId: number | null;
  cache: number;
}

interface Rascunho extends ValoresDoCard {
  /** A vaga como estava no servidor quando a pessoa começou a digitar. */
  base: ValoresDoCard;
  /** `Date.now()` da última gravação — rascunho esquecido sai depois de `VALIDADE_MS`. */
  em: number;
}

const PREFIXO = "manto:casting-rascunho:";
const VALIDADE_MS = 7 * 24 * 60 * 60 * 1000;

function chave(roleId: number): string {
  return `${PREFIXO}${roleId}`;
}

function iguais(a: ValoresDoCard, b: ValoresDoCard): boolean {
  return a.talentId === b.talentId && a.cache === b.cache;
}

/**
 * O rascunho da vaga, se ainda vale contra o que o servidor tem hoje.
 *
 * O `localStorage` pode não existir (aba anônima, cota cheia, bloqueio do navegador): aí não há
 * rascunho, e o card funciona como antes.
 */
export function lerRascunho(roleId: number, base: ValoresDoCard): ValoresDoCard | null {
  try {
    const bruto = window.localStorage.getItem(chave(roleId));
    if (!bruto) return null;
    const r = JSON.parse(bruto) as Rascunho;
    if (!r?.base || !iguais(r.base, base) || Date.now() - (r.em ?? 0) > VALIDADE_MS) {
      window.localStorage.removeItem(chave(roleId));
      return null;
    }
    return { talentId: r.talentId ?? null, cache: Number(r.cache) || 0 };
  } catch {
    return null;
  }
}

/** Grava o rascunho, ou o apaga quando o card voltou a bater com o servidor (`valores` = `null`). */
export function gravarRascunho(
  roleId: number,
  valores: ValoresDoCard | null,
  base: ValoresDoCard,
): void {
  try {
    if (!valores || iguais(valores, base)) {
      window.localStorage.removeItem(chave(roleId));
      return;
    }
    const r: Rascunho = { ...valores, base, em: Date.now() };
    window.localStorage.setItem(chave(roleId), JSON.stringify(r));
  } catch {
    // Sem armazenamento o rascunho só não sobrevive à saída da tela — o aviso na tela continua.
  }
}
