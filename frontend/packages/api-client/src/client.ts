/**
 * Cliente HTTP tipado — fonte única de acesso à API JSON do Flask (Princípio I).
 *
 * Sempre envia o cookie de sessão (`credentials: "include"`, Q3: sessão HttpOnly). Traduz o
 * envelope de erro padrão (`contracts/api-conventions.md`) em `ApiRequestError`, para o
 * frontend distinguir campo inválido (400 com `fields`) de falha genérica.
 */

/** Corpo do envelope de erro definido em contracts/api-conventions.md. */
export interface ApiErrorBody {
  message: string;
  fields?: Record<string, string>;
  /** Chaves adicionais que o endpoint anexa ao erro — ver `details` em `ApiRequestError`. */
  [chave: string]: unknown;
}

/** Erro lançado quando a API responde com status fora da faixa 2xx. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly fields?: Record<string, string>;
  /**
   * O corpo do erro inteiro, para quando o endpoint manda mais que uma mensagem.
   *
   * Nem todo erro é um beco: um 409 de "isto vai apagar dados" devolve a lista do que será
   * apagado, para a tela abrir a confirmação com nomes e valores; um 409 de "este evento é
   * satélite" devolve o `leader_id`, para a tela oferecer o caminho até o principal. Sem guardar
   * o corpo, essas chaves eram descartadas aqui e o front teria que adivinhar por texto.
   */
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.fields = body.fields;
    this.details = body;
  }
}

/**
 * URL base da API. Em produção, aponta para o domínio do Flask (ex.:
 * `https://app.mantoproducoes.com.br`), injetada no build via `VITE_API_BASE_URL`. Em dev,
 * fica vazia e o proxy do Vite roteia `/api` para o Flask local (research.md §2). O `/` final
 * é removido para não gerar `//api/...`.
 */
export const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(
  /\/+$/,
  "",
);

/**
 * Monta a URL absoluta de um arquivo servido pelo Flask (ex.: `/uploads/...`). Em produção
 * prefixa a base do Flask (`API_BASE`); em dev fica o path puro e o proxy do Vite roteia. Fonte
 * única da base — o frontend não concatena origem à mão. `null`/vazio → `undefined`.
 *
 * Alguns registros legados (fotos de talento/figurino importadas do Google Drive — feature
 * 154) já guardam uma URL absoluta em vez de um path relativo; prefixar `API_BASE` nesse caso
 * quebraria a URL em produção. Detecta `http://`/`https://` e devolve sem prefixar.
 */
export function assetUrl(
  path: string | null | undefined,
  options?: AssetUrlOptions,
): string | undefined {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path)) return path;
  const caminho = options?.largura ? comVariante(path, options.largura) : path;
  return `${API_BASE}${caminho}`;
}

/** Larguras de miniatura que o Flask gera (feature 270) — allowlist fechada dos dois lados. */
export type LarguraMiniatura = 128 | 320 | 480 | 640;

export interface AssetUrlOptions {
  /**
   * Pede a variante desta largura em vez do arquivo original. Só existe para fotos do catálogo
   * (`/catalogo/midia/<arquivo>`) e fotos de talento (`/uploads/talent_photos/<arquivo>`); para
   * qualquer outro caminho — ou URL absoluta legada — devolve o original, sem quebrar nada.
   */
  largura?: LarguraMiniatura;
}

const VARIANTE_CATALOGO = /^\/catalogo\/midia\/([^/]+)$/;
const VARIANTE_TALENTO = /^\/uploads\/talent_photos\/([^/]+)$/;

/**
 * Reescreve o caminho para a rota de variante (`.../t/<largura>/<arquivo>`). É a MESMA regra de
 * `pastas_da_variante` em `app/catalogo/og_ops.py`: os dois lados precisam concordar sobre quem
 * tem miniatura, senão o `<img>` pede uma URL que o Flask responde com 404.
 */
function comVariante(path: string, largura: LarguraMiniatura): string {
  const catalogo = VARIANTE_CATALOGO.exec(path);
  if (catalogo) return `/catalogo/midia/t/${largura}/${catalogo[1]}`;
  const talento = VARIANTE_TALENTO.exec(path);
  if (talento) return `/uploads/t/${largura}/talent_photos/${talento[1]}`;
  return path;
}

/**
 * `srcset` pronto com as variantes pedidas (`"…/t/320/x.jpg 320w, …/t/640/x.jpg 640w"`), ou
 * `undefined` quando o caminho não tem variante — aí o `<img>` fica só com o `src`, e o
 * navegador se comporta exatamente como antes da feature 270.
 */
export function assetSrcSet(
  path: string | null | undefined,
  larguras: readonly LarguraMiniatura[],
): string | undefined {
  if (!path || /^https?:\/\//i.test(path)) return undefined;
  if (comVariante(path, larguras[0] ?? 320) === path) return undefined;
  return larguras.map((w) => `${assetUrl(path, { largura: w })} ${w}w`).join(", ");
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    const data = (await response.json()) as { error?: ApiErrorBody };
    if (data.error && typeof data.error.message === "string") {
      return data.error;
    }
  } catch {
    // resposta sem corpo JSON — cai no fallback abaixo
  }
  return { message: "Ocorreu um erro inesperado. Tente novamente." };
}

/**
 * Executa uma requisição JSON (ou multipart, quando `options.body` é `FormData`) contra a API.
 *
 * Upload de arquivo (feature 153, `contracts/upload-endpoints.md`) usa `FormData` como corpo —
 * nesse caso o header `Content-Type` é omitido de propósito: o `fetch` nativo gera sozinho o
 * `boundary` do multipart, que um `Content-Type: application/json` forçado quebraria.
 *
 * @param path Caminho iniciando em `/api/...`.
 * @param options Opções do fetch (method, body já serializado ou `FormData`, etc.).
 * @returns O corpo da resposta desserializado como `T`.
 * @throws {ApiRequestError} Quando a resposta não é 2xx.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, await parseErrorBody(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/**
 * Executa uma requisição contra a API e devolve o corpo como `Blob`, para download binário
 * (ex.: CSV/PDF) — em vez de `.json()` como `apiFetch`. Primeiro uso: exportação de CSV da
 * Planilha de Pagamentos (feature 160); reaproveitável pelas fatias futuras de PDF (orçamento,
 * EducaManto).
 *
 * @param path Caminho iniciando em `/api/...`.
 * @param options Opções do fetch.
 * @returns O corpo da resposta como `Blob`.
 * @throws {ApiRequestError} Quando a resposta não é 2xx.
 */
export async function apiFetchBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, await parseErrorBody(response));
  }

  return await response.blob();
}
