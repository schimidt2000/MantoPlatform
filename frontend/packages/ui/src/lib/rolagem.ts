import { useEffect, useLayoutEffect, useRef } from "react";

/**
 * Restauração de rolagem das listas (feature 320).
 *
 * Os dois apps usam `BrowserRouter`, que não aceita o `<ScrollRestoration>` do React Router (só
 * existe com `createBrowserRouter`). O navegador até tenta restaurar sozinho no "voltar", mas faz
 * isso no `popstate`, quando a tela ainda é a do detalhe (curta) — a posição é cortada e a lista
 * volta no topo. Aqui a posição é guardada por entrada do histórico e reaplicada DEPOIS que a lista
 * aparece.
 *
 * Sem dependência do roteador de propósito: quem chama passa a chave da entrada
 * (`location.key`) e se a chegada foi um "voltar" (`navigationType === "POP"`).
 */

const CHAVE_ROLAGEM = "manto:rolagem";
const MAX_ENTRADAS = 50;
/** Quanto tempo insistir enquanto a página ainda é curta demais (fotos chegando, grade montando). */
const TEMPO_MAXIMO_MS = 1500;

type Posicoes = Record<string, number>;

function lerPosicoes(): Posicoes {
  try {
    const bruto = window.sessionStorage.getItem(CHAVE_ROLAGEM);
    return bruto ? (JSON.parse(bruto) as Posicoes) : {};
  } catch {
    return {};
  }
}

function gravarPosicao(chave: string, y: number): void {
  try {
    const posicoes = lerPosicoes();
    delete posicoes[chave];
    posicoes[chave] = y;
    // Objeto mantém a ordem de inserção: as primeiras chaves são as mais antigas.
    const chaves = Object.keys(posicoes);
    for (const velha of chaves.slice(0, Math.max(0, chaves.length - MAX_ENTRADAS))) {
      delete posicoes[velha];
    }
    window.sessionStorage.setItem(CHAVE_ROLAGEM, JSON.stringify(posicoes));
  } catch {
    // sessionStorage indisponível (aba privada antiga, cota): a lista só não volta no ponto.
  }
}

export interface OpcoesRestaurarRolagem {
  /** A pessoa chegou por "voltar"? Lido só na montagem — trocar depois não restaura de novo. */
  restaurar: boolean;
  /** A lista já está na tela (dados carregados)? A restauração espera por isto. */
  pronto: boolean;
}

/**
 * Guarda a rolagem da janela sob `chave` enquanto a lista está montada e, se a chegada foi um
 * "voltar", devolve a pessoa ao ponto salvo assim que `pronto` ficar verdadeiro.
 *
 * Trocar a `chave` com o componente montado (a busca reescreve o endereço com `replace`, e cada
 * escrita gera uma chave nova) só muda onde a posição é guardada.
 */
export function useRestaurarRolagem(chave: string, { restaurar, pronto }: OpcoesRestaurarRolagem): void {
  const chaveAtual = useRef(chave);
  chaveAtual.current = chave;
  const chaveDaChegada = useRef(chave);
  const deveRestaurar = useRef(restaurar);
  const jaRestaurou = useRef(false);
  const alvo = useRef(0);

  // Layout effect de propósito: a limpeza roda junto com a troca do DOM, ANTES de a página nova
  // rolar para o topo — senão esse "topo" chegaria aqui e sobrescreveria a posição da lista. E não
  // se grava nada ao desmontar: nessa hora o navegador já pode ter cortado a rolagem para a altura
  // da página nova.
  useLayoutEffect(() => {
    // O alvo é lido ANTES de assinar a rolagem: no "voltar", o navegador rola sozinho para uma
    // posição cortada, e esse evento gravaria por cima da posição boa.
    alvo.current = deveRestaurar.current ? (lerPosicoes()[chaveDaChegada.current] ?? 0) : 0;
    let quadro = 0;
    const aoRolar = () => {
      if (quadro) return;
      quadro = window.requestAnimationFrame(() => {
        quadro = 0;
        gravarPosicao(chaveAtual.current, Math.round(window.scrollY));
      });
    };
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => {
      window.removeEventListener("scroll", aoRolar);
      if (quadro) window.cancelAnimationFrame(quadro);
    };
  }, []);

  useEffect(() => {
    if (!pronto || jaRestaurou.current) return;
    jaRestaurou.current = true;
    const destino = alvo.current;
    if (!destino) return;

    let desistiu = false;
    const desistir = () => {
      desistiu = true;
    };
    // Se a pessoa já começou a rolar, a vontade dela vale mais que a posição antiga.
    window.addEventListener("wheel", desistir, { passive: true, once: true });
    window.addEventListener("touchstart", desistir, { passive: true, once: true });
    window.addEventListener("keydown", desistir, { once: true });

    const inicio = performance.now();
    let quadro = 0;
    const tentar = () => {
      if (desistiu) return;
      window.scrollTo(0, destino);
      const chegou = Math.abs(window.scrollY - destino) <= 2;
      if (!chegou && performance.now() - inicio < TEMPO_MAXIMO_MS) {
        quadro = window.requestAnimationFrame(tentar);
      }
    };
    tentar();
    return () => {
      window.cancelAnimationFrame(quadro);
      window.removeEventListener("wheel", desistir);
      window.removeEventListener("touchstart", desistir);
      window.removeEventListener("keydown", desistir);
    };
  }, [pronto]);
}
