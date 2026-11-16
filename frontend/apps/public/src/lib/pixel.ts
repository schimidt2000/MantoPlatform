/**
 * Pixel da Meta na loja de conversas (feature 344).
 *
 * Regra: **nada da Meta carrega sem o "Aceitar"** do aviso de cookies, e só existe aviso quando o
 * Superadmin preencheu o ID nas Configurações. Nenhum dado pessoal vai para a Meta — sem
 * "correspondência avançada" (nome, e-mail, telefone): só a visita, o início da compra e a compra,
 * com valor em reais.
 *
 * A escolha fica em `localStorage` (vale para as próximas visitas); a marca de "compra já enviada"
 * também, por pedido — recarregar a página do pedido pago não manda a compra de novo.
 */

type Fbq = ((...args: unknown[]) => void) & {
  callMethod?: (...args: unknown[]) => void;
  queue?: unknown[];
  push?: unknown;
  loaded?: boolean;
  version?: string;
};

declare global {
  interface Window {
    fbq?: Fbq;
    _fbq?: Fbq;
  }
}

export type Consentimento = "aceito" | "recusado" | null;

const CHAVE_CONSENTIMENTO = "manto_loja_cookies";
const PREFIXO_COMPRA = "manto_loja_compra_";

export function lerConsentimento(): Consentimento {
  try {
    const valor = localStorage.getItem(CHAVE_CONSENTIMENTO);
    return valor === "aceito" || valor === "recusado" ? valor : null;
  } catch {
    return null;
  }
}

export function gravarConsentimento(valor: "aceito" | "recusado"): void {
  try {
    localStorage.setItem(CHAVE_CONSENTIMENTO, valor);
  } catch {
    // storage bloqueado: a escolha vale só nesta página
  }
}

/** Desfaz a escolha (o aviso volta a aparecer). Com o pixel já carregado, recarrega a página. */
export function esquecerConsentimento(): void {
  try {
    localStorage.removeItem(CHAVE_CONSENTIMENTO);
  } catch {
    // nada a desfazer
  }
  window.location.reload();
}

let pixelCarregado: string | null = null;

/** Injeta o snippet oficial da Meta e inicia o pixel. Idempotente. */
export function carregarPixel(id: string): void {
  if (pixelCarregado === id || typeof window === "undefined") return;
  if (!window.fbq) {
    const fbq: Fbq = function (...args: unknown[]) {
      if (fbq.callMethod) fbq.callMethod(...args);
      else fbq.queue?.push(args);
    } as Fbq;
    fbq.push = fbq;
    fbq.loaded = true;
    fbq.version = "2.0";
    fbq.queue = [];
    window.fbq = fbq;
    window._fbq = fbq;
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://connect.facebook.net/en_US/fbevents.js";
    document.head.appendChild(script);
  }
  window.fbq("init", id);
  pixelCarregado = id;
  // A página do pedido pode ter visto o "pago" antes do pixel carregar (o efeito do filho roda
  // antes do efeito do layout, e o ID chega por uma consulta).
  if (compraPendente) {
    const { token, valor } = compraPendente;
    compraPendente = null;
    enviarCompraUmaVez(token, valor);
  }
}

let compraPendente: { token: string; valor: number } | null = null;

/** Manda um evento padrão — só se o pixel foi carregado (aceite + ID). Senão, não faz nada. */
export function eventoPixel(
  nome: "PageView" | "InitiateCheckout" | "Purchase",
  dados?: { value: number; currency: "BRL" },
): void {
  if (!pixelCarregado || !window.fbq) return;
  if (dados) window.fbq("track", nome, dados);
  else window.fbq("track", nome);
}

/** Compra de um pedido vai para a Meta uma vez só, mesmo recarregando a página. */
export function enviarCompraUmaVez(token: string, valor: number): void {
  if (!pixelCarregado) {
    // Guarda para quando (e se) o pixel carregar; sem aceite, nunca sai daqui.
    compraPendente = { token, valor };
    return;
  }
  const chave = `${PREFIXO_COMPRA}${token}`;
  try {
    if (localStorage.getItem(chave)) return;
    localStorage.setItem(chave, "1");
  } catch {
    // sem storage não há como garantir "uma vez": melhor não mandar do que mandar em dobro
    return;
  }
  eventoPixel("Purchase", { value: valor, currency: "BRL" });
}
