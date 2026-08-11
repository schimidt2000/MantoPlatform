import type { PanInfo } from "framer-motion";

/**
 * Utilidades do arraste por ponteiro (`drag` do Framer Motion), compartilhadas pelo quadro de
 * Marketing e pela grade de fotos do catálogo.
 *
 * O padrão dos dois é o mesmo: o elemento arrastado segue o dedo/ponteiro e a zona de soltura é
 * descoberta pelo **empilhamento real de elementos** no ponto, não por `getBoundingClientRect`
 * medido a cada quadro.
 */

/**
 * Ponto do ponteiro em coordenadas de **viewport**, que é o que `elementsFromPoint` espera.
 *
 * `info.point` do Framer é coordenada de página; com a janela rolada, usá-lo direto erraria o
 * alvo. Mouse/pointer trazem `clientX/clientY`; no toque, o dedo que saiu está em
 * `changedTouches`.
 */
export function viewportPoint(
  event: MouseEvent | TouchEvent | PointerEvent,
  info: PanInfo,
): { x: number; y: number } {
  if ("clientX" in event) return { x: event.clientX, y: event.clientY };
  const touch = event.changedTouches?.[0] ?? event.touches?.[0];
  if (touch) return { x: touch.clientX, y: touch.clientY };
  return { x: info.point.x - window.scrollX, y: info.point.y - window.scrollY };
}

/**
 * Primeiro atributo de `attrs` encontrado na pilha de elementos do ponto (x, y), da frente para
 * o fundo.
 *
 * `elementsFromPoint` devolve a pilha inteira, então o item arrastado (que está por cima) não
 * esconde a zona de soltura que está embaixo dele. Uma varredura só resolve alvos de tipos
 * diferentes (ex.: "outra foto da grade" vs. "um personagem do elenco"), e a ordem de `attrs`
 * define quem ganha quando os dois estão sob o ponteiro.
 */
export function firstAttributeAtPoint(
  attrs: readonly string[],
  x: number,
  y: number,
): { attr: string; value: string } | null {
  for (const element of document.elementsFromPoint(x, y)) {
    for (const attr of attrs) {
      const value = element.getAttribute?.(attr);
      if (value !== null && value !== undefined) return { attr, value };
    }
  }
  return null;
}

/** Valor de um único atributo na pilha de elementos do ponto — atalho de `firstAttributeAtPoint`. */
export function attributeAtPoint(attr: string, x: number, y: number): string | null {
  return firstAttributeAtPoint([attr], x, y)?.value ?? null;
}
