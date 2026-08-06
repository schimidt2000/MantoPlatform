import { useSyncExternalStore } from "react";

/** Tema visual escolhido pela pessoa, persistido por navegador. */
export type Theme = "claro" | "escuro";

/** Mesma chave lida pelo script anti-flash do `<head>` de cada app — não renomear sozinha. */
const CHAVE_ARMAZENAMENTO = "manto-tema";
const CLASSE_ESCURO = "dark";
/** Deve bater com a duração declarada em `theme.css` para o fallback de crossfade. */
const DURACAO_TROCA_MS = 300;
const CLASSE_TRANSICAO = "tema-em-transicao";

/** Ponto de onde o revelar circular nasce, em coordenadas de viewport. */
export interface RevealOrigin {
  x: number;
  y: number;
}

const ouvintes = new Set<() => void>();

/**
 * Lê o tema do próprio `<html>`, e não de um `useState`.
 *
 * O DOM é a única fonte confiável aqui por dois motivos: o script anti-flash já resolveu
 * localStorage + `prefers-color-scheme` antes do React existir, e o switch é montado DUAS vezes
 * ao mesmo tempo (sidebar do desktop + drawer do mobile). Dois `useState` independentes
 * dessincronizariam na primeira troca.
 */
function lerTema(): Theme {
  if (typeof document === "undefined") return "claro";
  return document.documentElement.classList.contains(CLASSE_ESCURO) ? "escuro" : "claro";
}

function assinar(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte);
  return () => {
    ouvintes.delete(ouvinte);
  };
}

/** Tema atual, reativo — todas as instâncias montadas do switch se atualizam juntas. */
export function useTheme(): Theme {
  return useSyncExternalStore(assinar, lerTema, () => "claro" as Theme);
}

/**
 * Aplica o tema no documento e persiste a escolha.
 *
 * @param tema Tema a passar a valer.
 */
function gravarTema(tema: Theme): void {
  const raiz = document.documentElement;
  raiz.classList.toggle(CLASSE_ESCURO, tema === "escuro");

  // O script anti-flash carimba um `background-color` INLINE no `<html>`, e estilo inline
  // sobrevive à troca de classe: sem reescrever aqui, a área de overscroll continuaria pintada
  // com o fundo do tema anterior. Lemos o token já computado em vez de repetir o HEX porque
  // cada app tem o seu (#f4f5f7 no interno, #f4f3f8 no portal).
  const fundo = getComputedStyle(raiz).getPropertyValue("--c-bg").trim();
  if (fundo) raiz.style.backgroundColor = `rgb(${fundo})`;

  try {
    localStorage.setItem(CHAVE_ARMAZENAMENTO, tema);
  } catch (erro) {
    // localStorage bloqueado (aba anônima/iframe de terceiro): o tema vale só para esta aba.
  }
  ouvintes.forEach((ouvinte) => ouvinte());
}

/** Raio que faz o círculo cobrir a tela inteira a partir da origem (canto mais distante). */
function raioAteCantoMaisDistante({ x, y }: RevealOrigin): number {
  return Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
}

/** Crossfade curto para browsers sem View Transitions — a classe sai sozinha ao fim da troca. */
function trocarComCrossfade(tema: Theme): void {
  const raiz = document.documentElement;
  raiz.classList.add(CLASSE_TRANSICAO);
  gravarTema(tema);
  window.setTimeout(() => raiz.classList.remove(CLASSE_TRANSICAO), DURACAO_TROCA_MS);
}

/**
 * Inverte o tema com um revelar circular que se expande a partir de `origem`.
 *
 * A View Transitions API congela um retrato da tela antiga, deixa o callback repintar tudo e
 * depois anima as duas camadas; animamos só o `clip-path` da camada NOVA para o tema novo
 * "inundar" a tela a partir de onde a pessoa clicou.
 *
 * @param origem Centro do revelar; sem ela cai no crossfade.
 * @param reduzirMovimento Resultado de `useReducedMotion()` — quando verdadeiro, troca seca.
 */
export function toggleTheme(origem?: RevealOrigin | null, reduzirMovimento?: boolean | null): void {
  const proximo: Theme = lerTema() === "escuro" ? "claro" : "escuro";

  // Movimento reduzido é decisão da pessoa, não degradação: troca instantânea (Princípio IX).
  if (reduzirMovimento) {
    gravarTema(proximo);
    return;
  }
  if (!origem || !("startViewTransition" in document)) {
    trocarComCrossfade(proximo);
    return;
  }

  const raiz = document.documentElement;
  const transicao = document.startViewTransition(() => gravarTema(proximo));
  transicao.ready
    .then(() => {
      const raio = raioAteCantoMaisDistante(origem);
      raiz.animate(
        {
          clipPath: [
            `circle(0px at ${origem.x}px ${origem.y}px)`,
            `circle(${raio}px at ${origem.x}px ${origem.y}px)`,
          ],
        },
        {
          duration: DURACAO_TROCA_MS,
          easing: "cubic-bezier(0.4, 0, 0.2, 1)",
          pseudoElement: "::view-transition-new(root)",
        },
      );
    })
    .catch(() => {
      // `ready` rejeita quando outra transição atropela esta (cliques repetidos). O tema já
      // trocou dentro do callback, então não há nada a desfazer — só o efeito é perdido.
    });
}
