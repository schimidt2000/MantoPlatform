import { apiFetch } from "@manto/api-client";

/**
 * De onde veio esta visita, para a venda (feature 348).
 *
 * O clique num anúncio do Google (ou num link de campanha) chega aqui com `gclid`/`utm_*` na URL, mas o
 * botão de WhatsApp leva a pessoa para o `wa.me` e o clique ficaria para trás. Então, no primeiro
 * carregamento com marcador, o site guarda os marcadores (90 dias, neste navegador) e pede ao servidor um
 * código curto; o botão de WhatsApp põe "Código do site: #A7K2Q" no fim da mensagem pronta, e a conversa
 * liga o clique à venda. Sem marcador, nada é guardado e a mensagem fica como sempre.
 *
 * Nada aqui atrasa a página: o pedido do código não é esperado, e qualquer falha (storage bloqueado, rede)
 * só faz a mensagem sair sem o código. A loja virtual (`/v`, `alo.`) tem contagem própria (344) e fica de
 * fora.
 */

const CHAVE = "manto_origem";
const VALIDADE_MS = 90 * 24 * 60 * 60 * 1000;
const MARCADORES = [
  "gclid",
  "gbraid",
  "wbraid",
  "fbclid",
  "gad_campaignid",
  "utm_id",
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
] as const;

interface OrigemGuardada {
  marcadores: Record<string, string>;
  pagina: string;
  procedencia: string | null;
  capturadoEm: number;
  codigo: string | null;
  /** O texto que vai na mensagem pronta, como o servidor mandou. */
  linha: string | null;
}

interface CodigoCriado {
  codigo: string;
  linha: string;
}

function ler(): OrigemGuardada | null {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const origem = JSON.parse(bruto) as OrigemGuardada;
    if (!origem || typeof origem.capturadoEm !== "number") return null;
    return Date.now() - origem.capturadoEm > VALIDADE_MS ? null : origem;
  } catch {
    return null;
  }
}

function gravar(origem: OrigemGuardada): void {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(origem));
  } catch {
    // Aba anônima com storage bloqueado: segue sem código.
  }
}

function naLoja(): boolean {
  const caminho = window.location.pathname.replace(/^\/catalogo/, "");
  return window.location.hostname.startsWith("alo.") || caminho === "/v" || caminho.startsWith("/v/");
}

/** Só o host de quem mandou a visita, e só se for outro site (navegar aqui dentro não é procedência). */
function procedenciaExterna(): string | null {
  try {
    if (!document.referrer) return null;
    const host = new URL(document.referrer).hostname.toLowerCase();
    return host && host !== window.location.hostname ? host : null;
  } catch {
    return null;
  }
}

function mesmosMarcadores(a: Record<string, string>, b: Record<string, string>): boolean {
  const chaves = new Set([...Object.keys(a), ...Object.keys(b)]);
  return [...chaves].every((chave) => a[chave] === b[chave]);
}

// O StrictMode monta duas vezes em desenvolvimento: um pedido só por carregamento.
let pedindo = false;

async function pedirCodigo(origem: OrigemGuardada): Promise<void> {
  if (pedindo) return;
  pedindo = true;
  try {
    const criado = await apiFetch<CodigoCriado>("/api/origem/codigo", {
      method: "POST",
      body: JSON.stringify({
        ...origem.marcadores,
        pagina: origem.pagina,
        procedencia: origem.procedencia,
      }),
    });
    // Outro clique pode ter trocado a origem enquanto o pedido voltava: o código é desta.
    const atual = ler();
    if (atual && atual.capturadoEm === origem.capturadoEm) {
      gravar({ ...atual, codigo: criado.codigo, linha: criado.linha });
    }
  } catch {
    // Sem código: a mensagem sai como antes. O próximo carregamento tenta de novo.
  } finally {
    pedindo = false;
  }
}

/** Lê os marcadores da URL e garante o código. Chamada uma vez, no carregamento do app público. */
export function capturarOrigem(): void {
  if (naLoja()) return;
  const params = new URLSearchParams(window.location.search);
  const marcadores: Record<string, string> = {};
  for (const nome of MARCADORES) {
    const valor = params.get(nome)?.trim();
    if (valor) marcadores[nome] = valor.slice(0, 512);
  }
  const anterior = ler();
  if (Object.keys(marcadores).length === 0 || (anterior && mesmosMarcadores(anterior.marcadores, marcadores))) {
    // Sem clique novo: vale o anterior (90 dias); se o código dele falhou, tenta de novo.
    if (anterior && !anterior.codigo) void pedirCodigo(anterior);
    return;
  }
  const nova: OrigemGuardada = {
    marcadores,
    pagina: window.location.pathname,
    procedencia: procedenciaExterna(),
    capturadoEm: Date.now(),
    codigo: null,
    linha: null,
  };
  gravar(nova);
  void pedirCodigo(nova);
}

/** O código guardado, para o formulário mandar junto (o servidor põe a linha na mensagem). */
export function codigoDoSite(): string | null {
  return ler()?.codigo ?? null;
}

/** A linha "Código do site: #XXXXX" para a mensagem montada no navegador (lista de desejos). */
export function linhaDoCodigo(): string | null {
  return ler()?.linha ?? null;
}
