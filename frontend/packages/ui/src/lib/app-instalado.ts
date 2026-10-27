/**
 * O sistema está aberto "como app" — pelo ícone na Tela de Início do iPhone ou instalado pelo
 * Chrome/Edge — e não numa aba comum do navegador (feature 320)?
 *
 * Nesse modo não há barra de endereço nem botão de voltar: um link que abre em outra aba vira uma
 * janela da qual a pessoa só sai fechando o app. `navigator.standalone` é o sinal do iOS;
 * `display-mode: standalone` é o dos outros.
 */
export function estaComoAppInstalado(): boolean {
  if (typeof window === "undefined") return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  if (nav.standalone === true) return true;
  return window.matchMedia?.("(display-mode: standalone)").matches ?? false;
}
