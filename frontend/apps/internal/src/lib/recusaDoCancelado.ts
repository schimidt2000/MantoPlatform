import { useEffect, useSyncExternalStore } from "react";

/**
 * A frase da última recusa `codigo: "cancelado"` (feature 312, FR-022 — converge).
 *
 * Quem abriu a aba antes do cancelamento e clica numa ação recebe o 409; o `aoRecusarMutacao` do
 * `main.tsx` recarrega o evento e a tela vira só consulta — e com isso o formulário que mostraria o
 * erro desmonta, ou o item do menu some. A frase fica guardada aqui e a caixa do cancelado
 * (`EventHeader`) a mostra, para a pessoa saber que o que pediu não foi feito e por quê.
 */
let frase: string | null = null;
const ouvintes = new Set<() => void>();

function avisar() {
  for (const ouvinte of ouvintes) ouvinte();
}

export function guardarRecusaDoCancelado(texto: string) {
  frase = texto;
  avisar();
}

function esquecer() {
  if (frase === null) return;
  frase = null;
  avisar();
}

/**
 * A frase guardada (ou `null`) e o "dispensar". Ao sair da tela — ou trocar de evento nela, que não
 * desmonta o componente — a frase é esquecida: a recusa de outro evento não aparece neste.
 */
export function useRecusaDoCancelado(eventId: number): [string | null, () => void] {
  const atual = useSyncExternalStore(
    (ouvinte) => {
      ouvintes.add(ouvinte);
      return () => ouvintes.delete(ouvinte);
    },
    () => frase,
  );
  useEffect(() => esquecer, [eventId]);
  return [atual, esquecer];
}
