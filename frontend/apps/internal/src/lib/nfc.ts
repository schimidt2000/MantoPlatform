import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE, ApiRequestError, apiFetch, assetUrl, type ApiErrorBody } from "@manto/api-client";

/**
 * Tags NFC das peças 3D (features 255, 261, 265 e 297) — tipos e hooks TanStack Query.
 *
 * Fonte única do contrato JSON de `/api/3d/nfc*` (`contracts/nfc-api.md`): a tela `/3d/tags`
 * consome daqui, nenhum `fetch` avulso. A tag nunca é apagada — o contrato só tem listagem,
 * lote e edição dos campos mutáveis (evento, situação, observações).
 *
 * A 297 trouxe a conversão em fundo: o upload responde assim que o arquivo está no disco e a
 * entrega nasce em `pendente`. Daí o polling da lista e as mutations de reprocessar, moldura e
 * abertura do sistema.
 */

export interface NfcTagItemRef {
  id: number;
  name: string;
  /** Passar por `assetUrl()` antes de exibir. */
  photo_url: string;
  nfc_prefix: string | null;
}

export interface NfcTagEventRef {
  id: number;
  title: string;
  start_at: string | null;
}

/**
 * Estado da conversão em fundo (feature 297). `pronto` é o único que a rota pública serve —
 * a página da tag nunca mostra vídeo meio convertido, e `falhou` só é visível aqui no ERP.
 */
export type NfcProcessingStatus = "pendente" | "processando" | "pronto" | "falhou";

/** Entrega de vídeo ativa da tag (feature 261) — `null` quando não há vídeo enviado ainda. */
export interface NfcTagVideoDelivery {
  id: number;
  kind: "video";
  title: string | null;
  /** Nome do arquivo em disco — só para exibir, nunca é URL (o arquivo é servido por código). */
  file_name: string | null;
  created_at: string | null;
  processing_status: NfcProcessingStatus;
  /** Motivo legível da falha, ou o aviso de quando a moldura não pôde ser aplicada. */
  processing_error: string | null;
  /** Metadados do arquivo ENTREGUE; `null` enquanto a conversão não terminou. */
  file_size_bytes: number | null;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  /** `true` = a moldura da Manto foi queimada no vídeo entregue. */
  has_frame: boolean;
}

/** Nome curto pedido pela 297; o shape é o mesmo que a lista de gestão já devolvia. */
export type NfcVideoDelivery = NfcTagVideoDelivery;

export interface NfcTag {
  id: number;
  /** Código gravado na tag física — imutável e eterno (`/nfc/<code>`). */
  code: string;
  /** Nº humano por produto (1, 2, 3…): o rótulo que a equipe anota na tagzinha ao gravar. */
  sequence: number;
  item: NfcTagItemRef;
  event: NfcTagEventRef | null;
  /** Cliente DIRETA da tag (campanha/brinde sem show) — independente do evento. */
  client: { id: number; name: string } | null;
  /** Nome resolvido pelo servidor: cliente direta quando houver, senão contratante do evento. */
  client_name: string | null;
  /** `true` = `client_name` veio do vínculo direto (editável na tag), não do evento. */
  client_direct: boolean;
  is_active: boolean;
  notes: string | null;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string | null;
  video_delivery: NfcTagVideoDelivery | null;
  /** Recados deixados pela cliente na página da tag (feature 297). */
  messages_count: number;
  messages_unread: number;
}

export interface NfcTagListResponse {
  tags: NfcTag[];
}

const NFC_KEY = ["nfc-tags"] as const;
const RECADOS_KEY = "nfc-recados";

/**
 * Upload multipart com progresso real, no molde de `apps/internal/src/lib/revisao.ts:53-89`.
 * A função de lá não é exportada, por isso a réplica em vez do import — o contrato de erro é o
 * mesmo do `apiFetch` de propósito: envelope da API vira `ApiRequestError` (a tela consegue
 * apontar o campo), resposta sem envelope vira a mensagem genérica.
 *
 * O `fetch` não expõe progresso de envio, e um vídeo de centenas de MB sobe por minutos — sem
 * barra, o silêncio parece conclusão e a aba é fechada no meio do envio.
 */
function uploadForm<T>(
  method: "POST" | "PUT",
  path: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, `${API_BASE}${path}`);
    xhr.withCredentials = true;
    xhr.responseType = "text";
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && e.total > 0) onProgress(e.loaded / e.total);
      };
    }
    xhr.onerror = () => reject(new Error("Falha de rede durante o envio. Tente novamente."));
    xhr.onload = () => {
      let parsed: unknown = null;
      try {
        parsed = JSON.parse(xhr.responseText || "null");
      } catch {
        parsed = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(parsed as T);
        return;
      }
      const envelope = (parsed as { error?: ApiErrorBody } | null)?.error;
      const body: ApiErrorBody =
        envelope && typeof envelope.message === "string"
          ? envelope
          : { message: "Ocorreu um erro inesperado. Tente novamente." };
      reject(new ApiRequestError(xhr.status, body));
    };
    xhr.send(form);
  });
}

/**
 * URL do vídeo para o player do ERP (feature 265) — NÃO usa a rota pública de propósito:
 * o espelho admin não conta acesso (revisar não pode inflar a métrica das clientes) e serve
 * inclusive tag desativada, que na rota pública devolve 404.
 */
export function adminNfcVideoUrl(tagId: number, deliveryId: number): string {
  // `assetUrl` só devolve `undefined` para path vazio — impossível aqui; o `?? ""` é só o tipo.
  return assetUrl(`/api/3d/nfc/${tagId}/entregas/${deliveryId}/media`) ?? "";
}

const STATUS_EM_FILA: readonly NfcProcessingStatus[] = ["pendente", "processando"];

/** `true` enquanto alguma tag da lista tiver vídeo esperando ou passando pela conversão. */
function temEntregaNaFila(data: NfcTagListResponse | undefined): boolean {
  return (data?.tags ?? []).some(
    (tag) =>
      tag.video_delivery !== null && STATUS_EM_FILA.includes(tag.video_delivery.processing_status),
  );
}

/**
 * Todas as tags, ordenadas por produto + nº sequencial.
 *
 * Polling de 3 s enquanto houver entrega em `pendente`/`processando`: a conversão roda numa
 * thread de fundo do Flask e não avisa ninguém quando termina, então sem isto o card ficaria
 * "preparando" até um F5. Ele para sozinho porque a condição olha o próprio payload — no ciclo
 * em que a última entrega vira `pronto` (ou `falhou`), `refetchInterval` devolve `false` e a
 * tela deixa de bater no servidor. Nenhum timer para limpar.
 */
export function useNfcTags() {
  return useQuery<NfcTagListResponse>({
    queryKey: NFC_KEY,
    queryFn: () => apiFetch<NfcTagListResponse>("/api/3d/nfc"),
    refetchInterval: (query) => (temEntregaNaFila(query.state.data) ? 3000 : false),
  });
}

/** Gera um lote avulso (estoque, sem evento) — o servidor numera e sorteia os códigos. */
export function useGerarLoteNfc() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { item_id: number; quantity: number }) =>
      apiFetch<NfcTagListResponse>("/api/3d/nfc/lote", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

export interface UpdateNfcTagInput {
  /** `null` desassocia do evento; omitido mantém. */
  event_id?: number | null;
  /** Cliente DIRETA (sem show): `null` desassocia; omitido mantém. */
  client_id?: number | null;
  is_active?: boolean;
  notes?: string;
}

/** Edita os únicos campos mutáveis de uma tag (código e nº nunca mudam). */
export function useAtualizarNfcTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateNfcTagInput }) =>
      apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

// ── Entregas (features 261 e 297) ────────────────────────────────────────────

export interface EnviarNfcVideoInput {
  tagId: number;
  file: File;
  title?: string;
  /**
   * Omitido equivale a `true`, o mesmo default do servidor — a caixinha "Aplicar a moldura da
   * Manto" nasce marcada, e o campo viaja sempre para que o valor não dependa de qual das duas
   * pontas decidiu.
   */
  comMoldura?: boolean;
  onProgress?: (fraction: number) => void;
}

/**
 * Envia (ou substitui) o vídeo da tag — multipart com progresso.
 *
 * A resposta chega assim que o arquivo está no disco, com a entrega em `pendente`: a conversão
 * (redução + moldura) roda depois, e quem mostra o andamento é o polling de `useNfcTags`.
 */
export function useEnviarNfcVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, file, title, comMoldura, onProgress }: EnviarNfcVideoInput) => {
      const form = new FormData();
      form.append("file", file);
      form.append("kind", "video");
      if (title) form.append("title", title);
      form.append("com_moldura", String(comMoldura ?? true));
      return uploadForm<{ tag: NfcTag }>(
        "POST",
        `/api/3d/nfc/${tagId}/entregas`,
        form,
        onProgress,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

export interface ReprocessarNfcVideoInput {
  tagId: number;
  deliveryId: number;
  /** Omitido mantém a escolha de moldura que a entrega já tinha. */
  comMoldura?: boolean;
}

/**
 * Recoloca a entrega na fila (botão "Tentar de novo" do card, e a troca de moldura).
 * Parte do mestre sem moldura, então reprocessar não empilha moldura sobre moldura.
 * O servidor devolve `409` quando a entrega já está na fila — a tela mostra a mensagem do
 * envelope em vez de criar uma segunda conversão para o mesmo vídeo.
 */
export function useReprocessarNfcVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, deliveryId, comMoldura }: ReprocessarNfcVideoInput) =>
      apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${tagId}/entregas/${deliveryId}/reprocessar`, {
        method: "POST",
        body: JSON.stringify(comMoldura === undefined ? {} : { com_moldura: comMoldura }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

/** Remove a entrega de vídeo da tag (linha + arquivo do disco). */
export function useRemoverNfcVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, deliveryId }: { tagId: number; deliveryId: number }) =>
      apiFetch<{ tag: NfcTag }>(`/api/3d/nfc/${tagId}/entregas/${deliveryId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

// ── Moldura e vídeo de abertura do sistema (feature 297) ─────────────────────

/**
 * Arquivos únicos, os mesmos para todas as tags. `null` nos dois campos = nada cadastrado —
 * é o que o `DELETE` devolve, e sem moldura cadastrada todo envio sai sem moldura.
 */
export interface NfcMolduraResponse {
  moldura_url: string | null;
  atualizada_em: string | null;
}

export interface NfcAberturaResponse {
  abertura_url: string | null;
  atualizada_em: string | null;
}

export interface SalvarArquivoSistemaInput {
  file: File;
  onProgress?: (fraction: number) => void;
}

/** Grava a moldura (PNG com transparência real; opaca é recusada com `fields.file`). */
export function useSalvarMolduraNfc() {
  return useMutation({
    mutationFn: ({ file, onProgress }: SalvarArquivoSistemaInput) => {
      const form = new FormData();
      form.append("file", file);
      return uploadForm<NfcMolduraResponse>("PUT", "/api/3d/nfc/moldura", form, onProgress);
    },
  });
}

/** Grava o vídeo de abertura — passa pela mesma conversão dos vídeos de tag, sem moldura. */
export function useSalvarAberturaNfc() {
  return useMutation({
    mutationFn: ({ file, onProgress }: SalvarArquivoSistemaInput) => {
      const form = new FormData();
      form.append("file", file);
      return uploadForm<NfcAberturaResponse>("PUT", "/api/3d/nfc/abertura", form, onProgress);
    },
  });
}

/** Apaga a moldura: os envios seguintes saem sem moldura, com aviso. */
export function useRemoverMolduraNfc() {
  return useMutation({
    mutationFn: () =>
      apiFetch<NfcMolduraResponse>("/api/3d/nfc/moldura", { method: "DELETE" }),
  });
}

/** Apaga a abertura: a página da tag passa a abrir direto no menu. */
export function useRemoverAberturaNfc() {
  return useMutation({
    mutationFn: () =>
      apiFetch<NfcAberturaResponse>("/api/3d/nfc/abertura", { method: "DELETE" }),
  });
}

// ── Recados da cliente (feature 297) ─────────────────────────────────────────

export interface NfcRecado {
  id: number;
  message: string;
  author_name: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NfcRecadosResponse {
  items: NfcRecado[];
  unread_count: number;
}

/**
 * Recados de UMA tag — carregados só quando a seção abre (`tagId` nulo = nada a buscar),
 * porque o selo de não lidos do card já vem em `messages_unread` na lista de gestão.
 */
export function useRecadosDaTag(tagId: number | null) {
  return useQuery<NfcRecadosResponse>({
    queryKey: [RECADOS_KEY, tagId],
    // `?? 0` nunca chega ao servidor: com `tagId` nulo a query está desligada.
    queryFn: () => apiFetch<NfcRecadosResponse>(`/api/3d/nfc/${tagId ?? 0}/recados`),
    enabled: tagId !== null,
  });
}

/** Marca todos os recados da tag como lidos e devolve quantos mudaram. */
export function useMarcarRecadosLidos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: number) =>
      apiFetch<{ marcados: number }>(`/api/3d/nfc/${tagId}/recados/lidos`, { method: "POST" }),
    onSuccess: (_resposta, tagId) => {
      void queryClient.invalidateQueries({ queryKey: [RECADOS_KEY, tagId] });
      // O selo de não lidos mora no card da lista (`messages_unread`), não na query dos recados.
      void queryClient.invalidateQueries({ queryKey: NFC_KEY });
    },
  });
}

// ── Formatação para os cards ─────────────────────────────────────────────────

const UMA_CASA = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const SEM_CASA = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Traço no lugar do número quando a conversão ainda não mediu o arquivo. */
const VAZIO = "—";

/**
 * Peso do arquivo em pt-BR: `"812 B"`, `"640 KB"`, `"12,4 MB"`, `"1,2 GB"`.
 * Uma casa decimal só de MB para cima — é onde a diferença entre antes e depois da conversão
 * (o motivo da 297) fica visível; em KB a casa decimal seria ruído.
 */
export function formatarPeso(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes < 0) return VAZIO;
  if (bytes < 1024) return `${SEM_CASA.format(bytes)} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${SEM_CASA.format(kb)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${UMA_CASA.format(mb)} MB`;
  return `${UMA_CASA.format(mb / 1024)} GB`;
}

/**
 * Duração falada em pt-BR: `"22 s"`, `"1 min 22 s"`, `"2 min"`, `"1 h 5 min"`.
 * Os vídeos das tags têm segundos ou poucos minutos, então a leitura corrida vale mais que o
 * relógio `00:01:22`.
 */
export function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || !Number.isFinite(segundos) || segundos < 0) {
    return VAZIO;
  }
  const total = Math.round(segundos);
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  const resto = total % 60;
  if (horas > 0) return minutos > 0 ? `${horas} h ${minutos} min` : `${horas} h`;
  if (minutos > 0) return resto > 0 ? `${minutos} min ${resto} s` : `${minutos} min`;
  return `${resto} s`;
}
