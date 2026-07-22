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
}

/** Erro lançado quando a API responde com status fora da faixa 2xx. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly fields?: Record<string, string>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.fields = body.fields;
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
export function assetUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path}`;
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
