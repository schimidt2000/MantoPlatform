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

/** URL base da API. Em dev, o proxy do Vite roteia `/api` para o Flask (research.md §2). */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

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
 * Executa uma requisição JSON contra a API.
 *
 * @param path Caminho iniciando em `/api/...`.
 * @param options Opções do fetch (method, body já serializado, etc.).
 * @returns O corpo da resposta desserializado como `T`.
 * @throws {ApiRequestError} Quando a resposta não é 2xx.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
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
