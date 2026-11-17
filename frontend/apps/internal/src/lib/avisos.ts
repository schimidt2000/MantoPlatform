import { useQuery } from "@tanstack/react-query";
import { ApiRequestError, apiFetch } from "@manto/api-client";

/**
 * Avisos no celular (feature 332) — Web Push do navegador.
 *
 * Contrato em `specs/332-crm-avisos-no-celular/contracts/api.md`. O aparelho se registra pelo
 * service worker `/sw.js` (em `public/`), que mostra o aviso e abre a conversa ao tocar. No iPhone
 * o navegador só oferece avisos com a Plataforma instalada na Tela de Início (iOS 16.4+): numa aba
 * do Safari, `PushManager` nem existe.
 */

export type EstadoDosAvisos =
  | "desligado"
  | "sem_suporte"
  | "iphone_fora_da_tela_de_inicio"
  | "negado"
  | "inativo"
  | "ativo";

interface ChaveDosAvisos {
  ligado: boolean;
  chave_publica: string | null;
}

export function useChaveDosAvisos(habilitado: boolean) {
  return useQuery({
    queryKey: ["push", "chave"],
    queryFn: () => apiFetch<ChaveDosAvisos>("/api/push/chave"),
    enabled: habilitado,
    staleTime: 5 * 60_000,
  });
}

/** O navegador recusou a permissão: o pedido não reaparece sozinho (spec, casos de borda). */
export class AvisosNegados extends Error {}

function eIphone(): boolean {
  // iPadOS se apresenta como Mac; o toque denuncia.
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function instalado(): boolean {
  const naTelaDeInicio = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return naTelaDeInicio || window.matchMedia("(display-mode: standalone)").matches;
}

function temSuporte(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

async function assinaturaAtual(): Promise<PushSubscription | null> {
  const registro = await navigator.serviceWorker.getRegistration("/");
  return (await registro?.pushManager.getSubscription()) ?? null;
}

/**
 * O estado deste aparelho. "Ativo" só com o servidor confirmando: a assinatura local é registrada
 * de novo (passa a ser de quem está logado — outra pessoa pode ter usado o mesmo navegador). A
 * assinatura feita com outro par de chaves (a Plataforma trocou) ou recusada pelo servidor não
 * recebe nada: inativo. Falha de rede levanta (a tela oferece "Tentar novamente").
 */
export async function estadoDosAvisos(chavePublica: string | null): Promise<EstadoDosAvisos> {
  if (!chavePublica) return "desligado";
  if (!temSuporte()) return eIphone() && !instalado() ? "iphone_fora_da_tela_de_inicio" : "sem_suporte";
  if (Notification.permission === "denied") return "negado";
  const assinatura = await assinaturaAtual();
  if (!assinatura || !mesmaChave(assinatura, chaveEmBytes(chavePublica))) return "inativo";
  try {
    await registrarNoServidor(assinatura);
  } catch (erro) {
    if (erro instanceof ApiRequestError && erro.status >= 400 && erro.status < 500) {
      await assinatura.unsubscribe().catch(() => undefined);
      return "inativo";
    }
    throw erro;
  }
  return "ativo";
}

/** A chave VAPID em base64url, como o `pushManager.subscribe` pede (bytes). */
function chaveEmBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = (base64url + "=".repeat((4 - (base64url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const binario = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(binario.length));
  for (let i = 0; i < binario.length; i += 1) bytes[i] = binario.charCodeAt(i);
  return bytes;
}

function mesmaChave(assinatura: PushSubscription, chave: Uint8Array): boolean {
  const atual = assinatura.options.applicationServerKey;
  if (!atual) return false;
  const bytes = new Uint8Array(atual);
  return bytes.length === chave.length && bytes.every((b, i) => b === chave[i]);
}

async function registrarNoServidor(assinatura: PushSubscription): Promise<void> {
  await apiFetch("/api/push/aparelhos", { method: "POST", body: JSON.stringify(assinatura.toJSON()) });
}

/**
 * Pede a permissão, assina e registra este aparelho para quem está logado. A permissão vem
 * primeiro, ainda no gesto do toque: o iPhone recusa o pedido feito depois de outra espera.
 */
export async function ativarAvisos(chavePublica: string): Promise<void> {
  const permissao = await Notification.requestPermission();
  if (permissao !== "granted") throw new AvisosNegados();
  await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  const registro = await navigator.serviceWorker.ready;
  const chave = chaveEmBytes(chavePublica);
  let assinatura = await registro.pushManager.getSubscription();
  if (assinatura && !mesmaChave(assinatura, chave)) {
    // A Plataforma trocou o par de chaves: a assinatura velha não recebe mais nada.
    await assinatura.unsubscribe();
    assinatura = null;
  }
  assinatura ??= await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: chave });
  try {
    await registrarNoServidor(assinatura);
  } catch (erro) {
    // Sem o registro no servidor, nada toca: o aparelho não pode parecer ativado depois.
    await assinatura.unsubscribe().catch(() => undefined);
    throw erro;
  }
}

/** Para de tocar neste aparelho primeiro; o servidor é avisado depois (se falhar, o 410 limpa). */
export async function desativarAvisos(): Promise<void> {
  const assinatura = await assinaturaAtual();
  if (!assinatura) return;
  const { endpoint } = assinatura;
  await assinatura.unsubscribe();
  await apiFetch("/api/push/aparelhos", { method: "DELETE", body: JSON.stringify({ endpoint }) });
}

/**
 * "Sair" desliga os avisos deste aparelho: o aviso traz o nome e o trecho da cliente, e o
 * navegador pode ficar com outra pessoa. Nunca segura a saída: no máximo 3 s, e a falha é ignorada
 * (o servidor apaga o aparelho quando o serviço responder 410).
 */
export async function desativarAoSair(): Promise<void> {
  if (!temSuporte()) return;
  const limite = new Promise<void>((resolve) => setTimeout(resolve, 3000));
  await Promise.race([desativarAvisos().catch(() => undefined), limite]);
}
