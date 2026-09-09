import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch, ApiRequestError } from "@manto/api-client";
import { fieldErrorsFrom } from "./virtuais";

/** Produto (item do Acervo 3D) da tag — `null` quando o código não resolve. */
export interface NfcProduct {
  name: string;
  photo_url: string;
}

/**
 * Uma entrega anexada à tag (feature 261) — hoje só `kind: "video"`. `media_url` já vem pronta
 * para `assetUrl()`; passar por `/uploads` seria errado aqui, o arquivo mora fora dali de
 * propósito (ver `app/config.py: NFC_MEDIA_FOLDER`).
 *
 * Só chega aqui entrega com `processing_status = "pronto"` (feature 297): vídeo em conversão
 * simplesmente não existe para esta página.
 */
export interface NfcDelivery {
  kind: "video";
  /** `null` → a página usa a copy padrão ("Um vídeo especial para você"). */
  title: string | null;
  media_url: string;
  /**
   * Dimensões do arquivo já convertido (feature 297). Vêm no payload para a página reservar o
   * palco ANTES de o vídeo carregar os metadados — sem elas o layout pula quando o `<video>`
   * descobre sozinho que é retrato.
   */
  width: number;
  height: number;
}

/**
 * Resolução pública de um código de tag NFC — espelho de `contracts/nfc-api.md` (feature 255,
 * estendido na 261 e na 297).
 *
 * O endpoint responde SEMPRE 200 com este shape: código inexistente, tag desativada e tag sem
 * vídeo pronto são indistinguíveis (`product: null`, `deliveries: []`), então a página não tem
 * caminho de erro — só o modo genérico. `campaign` é o gancho do sistema futuro de campanhas:
 * hoje sempre `null`.
 *
 * `instagram_url`, `spotify_url` e `intro_video_url` viajam **também** no shape vazio: o menu
 * genérico precisa dos dois botões externos mesmo quando não há produto nenhum.
 */
export interface NfcResolution {
  product: NfcProduct | null;
  campaign: null;
  deliveries: NfcDelivery[];
  instagram_url: string;
  spotify_url: string;
  /**
   * Vídeo de abertura do sistema — o MESMO arquivo para todas as luminárias, já com o `?v=`
   * que fura o cache quando o dono troca o arquivo. `null` = nenhuma abertura cadastrada, e aí
   * a página abre direto no menu. Passa por `assetUrl()`, como qualquer arquivo do Flask.
   */
  intro_video_url: string | null;
  /** Liga a cena da mensagem — sem isso a página não oferece o formulário de recado. */
  aceita_recado: boolean;
}

/** Resolve o código no servidor — é o servidor quem decide TODO o conteúdo da página. */
export function useNfcResolution(code: string) {
  return useQuery<NfcResolution>({
    queryKey: ["nfc", code],
    queryFn: () => apiFetch<NfcResolution>(`/api/nfc/${encodeURIComponent(code)}`),
    retry: false,
    // A URL está gravada numa tag física: o conteúdo não muda durante a visita.
    staleTime: Infinity,
    // E não muda nem quando há vídeo em conversão: acompanhar processamento é trabalho do
    // gerenciador (`apps/internal`), não desta página — a cliente que encostou o celular vê o
    // que estava pronto no instante do toque, sem a tela se remontar no meio do vídeo.
  });
}

/* ------------------------------------------------------------------ *
 * Memória do aparelho: a abertura toca uma vez só
 * ------------------------------------------------------------------ */

const CHAVE_ABERTURA_VISTA = "manto_nfc_abertura_vista";

/**
 * A memória é GLOBAL — uma vez por aparelho, para QUALQUER tag, não uma por código.
 *
 * O vídeo de abertura é um arquivo só, o mesmo em todas as luminárias (`contracts/nfc-api.md`
 * §3). Guardar por código faria a mesma abertura tocar de novo a cada tag nova que a família
 * encostasse — exatamente o que a spec pede para não acontecer.
 */
function lerAberturaVista(): boolean {
  try {
    return window.localStorage.getItem(CHAVE_ABERTURA_VISTA) === "1";
  } catch {
    // localStorage indisponível (aba privada/cota) — vale "nunca viu": a abertura toca, que é o
    // pior caso aceitável. Nunca quebrar a página por causa da memória.
    return false;
  }
}

function gravarAberturaVista(): void {
  try {
    window.localStorage.setItem(CHAVE_ABERTURA_VISTA, "1");
  } catch {
    // Sem storage a marca se perde e a abertura repete na próxima visita — degrada em silêncio.
  }
}

/**
 * Este aparelho já viu a abertura? `true` → a página abre direto no menu, sem a capa.
 *
 * O `code` é aceito e ignorado de propósito: deixa a chamada explícita sobre qual tag está em
 * cena e permite trocar para memória por tag sem mexer em quem chama.
 */
export function aberturaJaVista(_code?: string): boolean {
  return lerAberturaVista();
}

/** Marca a abertura como vista — chamar quando ela termina OU quando a pessoa pula. */
export function marcarAberturaVista(): void {
  gravarAberturaVista();
}

/* ------------------------------------------------------------------ *
 * Recado da cliente
 * ------------------------------------------------------------------ */

/** Corpo de `POST /api/nfc/<code>/recados`. */
export interface RecadoInput {
  /** Obrigatório, até 1000 caracteres — o servidor é quem decide. */
  message: string;
  /** Opcional, até 120 caracteres: a cliente assina se quiser. */
  author_name?: string;
}

interface RecadoCriado {
  ok: true;
}

/** O que a cena da mensagem precisa para desenhar o formulário inteiro. */
export interface EnviarRecado {
  enviar: (input: RecadoInput) => void;
  /** Botão em estado de envio (desabilitado, texto trocado) até a resposta. */
  enviando: boolean;
  /** Já agradeceu — a cena troca para o agradecimento. */
  enviado: boolean;
  /**
   * Mensagem de erro que NÃO aponta campo (429, queda de rede). `null` quando há erro de campo,
   * para a tela não repetir a mesma queixa em dois lugares.
   */
  erroGeral: string | null;
  /** `{ campo: mensagem }` do envelope — hoje só a chave `message` (Princípio V). */
  camposComErro: Record<string, string>;
  /** Volta ao estado inicial, para a tela oferecer "escrever outro". */
  limpar: () => void;
}

function mensagemGeral(erro: unknown, campos: Record<string, string>): string | null {
  if (!erro) return null;
  // Erro de campo já aparece embaixo do campo culpado; no topo seria ruído.
  if (Object.keys(campos).length > 0) return null;
  // Falha de rede não passa pelo envelope do Flask e chega como `TypeError: Failed to fetch` —
  // texto em inglês que a cliente não pode ver.
  if (erro instanceof ApiRequestError) return erro.message;
  return "Não foi possível enviar agora. Tente de novo em instantes.";
}

/**
 * Envia o recado da cliente.
 *
 * O servidor responde 201 mesmo para código inexistente ou tag desativada (nada é gravado): é a
 * mesma indistinguibilidade da resolução, então `enviado` NUNCA revela se o código existe — a
 * cliente vê o agradecimento de qualquer jeito.
 */
export function useEnviarRecado(code: string): EnviarRecado {
  const mutation = useMutation<RecadoCriado, ApiRequestError, RecadoInput>({
    mutationFn: (input) =>
      apiFetch<RecadoCriado>(`/api/nfc/${encodeURIComponent(code)}/recados`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    // Sem retry automático: o 400 é do texto e o 429 é do limite de taxa — repetir sozinho
    // não corrige nenhum dos dois e ainda gasta a cota da pessoa.
    retry: false,
  });

  const camposComErro = useMemo(() => fieldErrorsFrom(mutation.error), [mutation.error]);

  return {
    enviar: (input) => mutation.mutate(input),
    enviando: mutation.isPending,
    enviado: mutation.isSuccess,
    erroGeral: mensagemGeral(mutation.error, camposComErro),
    camposComErro,
    limpar: mutation.reset,
  };
}
