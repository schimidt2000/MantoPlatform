import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";
import {
  Badge,
  Button,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  formatShortDate,
  Input,
} from "@manto/ui";
import {
  adminNfcVideoUrl,
  formatarDuracao,
  formatarPeso,
  useEnviarNfcVideo,
  useRemoverNfcVideo,
  useReprocessarNfcVideo,
  type NfcTag,
} from "../../lib/nfc";
import { UploadProgressBar } from "../UploadProgressBar";
import { fieldError, NFC_VIDEO_ACCEPT } from "./helpers";

export interface VideoDialogProps {
  tag: NfcTag | null;
  onClose: () => void;
}

/**
 * Cópia do arquivo em memória, desligada do disco — réplica de `snapshotFile`
 * (`packages/ui/src/components/file-upload.tsx:60`), que não é exportado; mesma situação do
 * `uploadForm` replicado em `lib/nfc.ts`.
 *
 * O `<input type="file">` guarda só uma REFERÊNCIA: o navegador anota tamanho e data de
 * modificação no momento da escolha e reabre o arquivo na hora de enviar — se qualquer um dos
 * dois mudou, ele aborta com `ERR_UPLOAD_FILE_CHANGED` sem mandar um byte e joga uma tela de
 * erro do próprio navegador no lugar do diálogo. Aqui isso é o caso comum, não a exceção: o
 * vídeo acabou de ser filmado no celular, e o Google Fotos/Drive reescreve o arquivo temporário
 * que entregou enquanto a pessoa ainda está na tela.
 *
 * Lendo os bytes agora, o `FormData` passa a apontar para memória e o navegador nunca mais volta
 * ao disco. O teto de 24 MB do componente original NÃO se aplica: lá ele protege o Acervo 3D,
 * que é upload de desktop e não sofre com arquivo reescrito; aqui um vídeo tem 150 MB e vem
 * justamente do aparelho onde ele se mexe sozinho — segurar esses bytes na RAM por alguns
 * minutos custa menos que perder o envio inteiro no fim.
 */
async function snapshotFile(file: File): Promise<File> {
  const bytes = await file.arrayBuffer();
  return new File([bytes], file.name, { type: file.type, lastModified: file.lastModified });
}

/** Arquivo que nem deu para ler — falha AQUI, com a escolha fresca, e não no fim do envio. */
const ERRO_LEITURA =
  "Não foi possível ler este arquivo. Se ele veio do Google Fotos ou do Drive, salve na galeria do aparelho e escolha de novo.";

/**
 * Vídeo "Um vídeo especial para você" anexado à tag (features 261, 265 e 297).
 *
 * `tag` vem da lista viva (`tags.find`, não uma cópia local) — assim que o upload, o
 * reprocessamento ou a remoção invalidam a query, o diálogo continua aberto já mostrando o novo
 * estado, sem fechar e reabrir; o polling de `useNfcTags` é quem faz a conversão em fundo
 * aparecer terminando sozinha.
 *
 * Escolher o arquivo JÁ dispara o envio (mesmo padrão de `FilaProducaoMidiaPage`, sem botão de
 * confirmar). Por isso tudo que muda o resultado — título e moldura — fica ACIMA do seletor e é
 * decidido antes: descobrir depois custaria 150 MB de upload de novo.
 */
export function VideoDialog({ tag, onClose }: VideoDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [comMoldura, setComMoldura] = useState(true);
  /** `null` esconde a barra; `0..1` vem do `xhr.upload.onprogress` via `onProgress`. */
  const [progresso, setProgresso] = useState<number | null>(null);
  /** Cópia dos bytes em andamento (ver `snapshotFile`) — ainda não subiu nada. */
  const [preparando, setPreparando] = useState(false);
  const [erroLeitura, setErroLeitura] = useState<string | null>(null);
  const [confirmandoRemocao, setConfirmandoRemocao] = useState(false);
  const reduceMotion = useReducedMotion();
  const enviar = useEnviarNfcVideo();
  const reprocessar = useReprocessarNfcVideo();
  const remover = useRemoverNfcVideo();
  const delivery = tag?.video_delivery ?? null;
  const status = delivery?.processing_status ?? null;
  const emFila = status === "pendente" || status === "processando";
  /** Um só estado de "ocupado enviando": copiar os bytes e subi-los são a mesma espera. */
  const enviando = preparando || enviar.isPending;
  const erroEnvio = enviar.error
    ? (fieldError(enviar.error, "file") ?? enviar.error.message)
    : null;
  const erroTitulo = fieldError(enviar.error, "title");
  const erroMoldura = fieldError(enviar.error, "com_moldura");

  // Pré-carrega o título salvo ao abrir (e ao trocar de tag/vídeo): Substituir manda o campo
  // junto com o arquivo novo — sem isso, o título personalizado sumiria da página pública.
  useEffect(() => {
    setTitle(tag?.video_delivery?.title ?? "");
  }, [tag?.id, tag?.video_delivery?.id, tag?.video_delivery?.title]);

  // A moldura só volta a marcada ao trocar de TAG, não a cada entrega nova: quem acabou de
  // enviar sem moldura e vai substituir de novo não pode ter a caixinha remarcada nas costas.
  useEffect(() => {
    setComMoldura(true);
  }, [tag?.id]);

  function close() {
    setTitle("");
    setComMoldura(true);
    setProgresso(null);
    setPreparando(false);
    setErroLeitura(null);
    setConfirmandoRemocao(false);
    enviar.reset();
    reprocessar.reset();
    remover.reset();
    onClose();
  }

  async function handleFile(escolhido: File) {
    if (!tag) return;
    // O id sai do `tag` ANTES do await: a cópia dos bytes demora, e o diálogo pode ter trocado
    // de tag no meio — o envio tem que pousar na tag que a pessoa estava vendo ao escolher.
    const tagId = tag.id;
    setErroLeitura(null);
    enviar.reset();
    setPreparando(true);

    let arquivo: File;
    try {
      arquivo = await snapshotFile(escolhido);
    } catch {
      setPreparando(false);
      setErroLeitura(ERRO_LEITURA);
      return;
    }

    setPreparando(false);
    // Zero antes do primeiro `onprogress`: a barra nasce na hora, e não depois do primeiro chunk.
    setProgresso(0);
    enviar.mutate(
      {
        tagId,
        file: arquivo,
        title: title.trim() || undefined,
        comMoldura,
        onProgress: setProgresso,
      },
      { onSettled: () => setProgresso(null) },
    );
  }

  function handleReprocessar() {
    if (!tag || !delivery) return;
    // Manda a caixinha junto: ela está visível na mesma tela, então "Tentar de novo" tem que
    // produzir o que ela promete — e não a escolha da tentativa que falhou.
    reprocessar.mutate({ tagId: tag.id, deliveryId: delivery.id, comMoldura });
  }

  function handleRemove() {
    if (!tag || !delivery) return;
    remover.mutate(
      { tagId: tag.id, deliveryId: delivery.id },
      { onSuccess: () => setConfirmandoRemocao(false) },
    );
  }

  return (
    <Dialog open={tag !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent open={tag !== null} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Vídeo — tag nº {tag?.sequence} ({tag?.code})
          </DialogTitle>
          <DialogDescription>
            A cliente vê este vídeo ao encostar o celular na peça, antes do link do Instagram.
            Fica fora de <code>/uploads</code> — só sai por este link público.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <input
            ref={inputRef}
            type="file"
            accept={NFC_VIDEO_ACCEPT}
            className="hidden"
            aria-label="Arquivo de vídeo"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void handleFile(file);
            }}
          />

          {/* Painel de estado da entrega. A `key` inclui o status: cada transição da conversão
              remonta o bloco, o que anima a troca e faz o leitor de tela anunciar o novo estado. */}
          <AnimatePresence initial={false} mode="wait">
            {tag && delivery && (
              <motion.div
                key={`${delivery.id}-${delivery.processing_status}`}
                initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="space-y-2"
              >
                {emFila ? (
                  <div
                    role="status"
                    className="flex items-start gap-3 rounded-md border border-line bg-surface-2 p-3"
                  >
                    <Loader2 className="mt-0.5 h-4 w-4 flex-none animate-spin text-accent" aria-hidden="true" />
                    <div>
                      <p className="text-sm font-medium text-ink">
                        Preparando o vídeo… pode fechar esta janela.
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {status === "pendente"
                          ? "O arquivo já está no servidor, na fila de conversão."
                          : "Convertendo agora (redução e moldura)."}{" "}
                        A lista de vídeos se atualiza sozinha quando terminar.
                      </p>
                    </div>
                  </div>
                ) : status === "falhou" ? (
                  <div className="rounded-md border border-line bg-red-50 p-3">
                    <p className="flex items-center gap-2 text-sm font-medium text-red" role="alert">
                      <AlertTriangle className="h-4 w-4 flex-none" aria-hidden="true" />
                      A conversão falhou — a cliente ainda não vê nada.
                    </p>
                    <p className="mt-1 text-xs text-ink">
                      {delivery.processing_error ?? "O servidor não informou o motivo."}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      loading={reprocessar.isPending}
                      onClick={handleReprocessar}
                    >
                      <RefreshCw className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Tentar de novo
                    </Button>
                    {reprocessar.error && (
                      <p className="mt-2 text-xs text-red" role="alert">
                        {reprocessar.error.message}
                      </p>
                    )}
                  </div>
                ) : (
                  <>
                    {/* `key` remonta o player quando Substituir troca a entrega (src novo, buffer
                        limpo). `preload="metadata"` é inegociável — ver o incidente documentado em
                        `revisao/VideoPlayer.tsx`: `auto` baixa o arquivo inteiro por thread.
                        Retrato e não `aspect-video`: os vídeos das tags são sempre em pé, e o
                        quadro deitado os espremia numa faixa central. */}
                    <video
                      key={delivery.id}
                      src={adminNfcVideoUrl(tag.id, delivery.id)}
                      controls
                      playsInline
                      preload="metadata"
                      className="mx-auto aspect-[9/16] w-full max-w-[15rem] rounded-md bg-black object-contain"
                    />
                    <div className="rounded-md border border-line bg-surface-2 p-3">
                      <p className="text-sm font-medium text-ink">
                        {delivery.title || "Sem título — a página usa a copy padrão"}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {formatarPeso(delivery.file_size_bytes)} ·{" "}
                        {formatarDuracao(delivery.duration_seconds)}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {delivery.file_name}
                        {delivery.created_at &&
                          ` · enviado em ${formatShortDate(delivery.created_at)}`}
                      </p>
                      <Badge tone={delivery.has_frame ? "accent" : "neutral"} className="mt-2">
                        {delivery.has_frame ? "Com a moldura da Manto" : "Sem moldura"}
                      </Badge>
                    </div>
                    {/* Entrega pronta COM aviso: a conversão terminou, mas a moldura não pôde ser
                        aplicada (é o único caso em que `processing_error` convive com `pronto`). */}
                    {delivery.processing_error && (
                      <p
                        role="status"
                        className="rounded-md border border-line bg-gold-soft p-2 text-xs text-gold-ink"
                      >
                        {delivery.processing_error}
                      </p>
                    )}
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <label className="block">
            <span className="mb-1 block text-sm text-muted">Título (opcional)</span>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Um vídeo especial para você"
              aria-label="Título do vídeo"
              aria-invalid={erroTitulo !== undefined}
            />
            {erroTitulo && (
              <span className="mt-1 block text-xs text-red" role="alert">
                {erroTitulo}
              </span>
            )}
            <span className="mt-1 block text-xs text-muted">
              Formatos aceitos: MP4, MOV, WEBM, M4V.
              {delivery && " Substituir grava o título acima junto com o vídeo novo."}
            </span>
          </label>

          {/* Acima do seletor de propósito: escolher o arquivo já começa o envio, então esta é a
              última chance de decidir a moldura. O aviso diz isso com todas as letras — antes,
              descobrir depois significava refazer minutos de upload. */}
          <div className="rounded-md border border-line bg-surface-2 p-3">
            <label className="flex cursor-pointer items-start gap-3 py-0.5 text-sm text-ink">
              <input
                type="checkbox"
                checked={comMoldura}
                disabled={enviando}
                onChange={(e) => setComMoldura(e.target.checked)}
                className="mt-0.5 h-5 w-5 flex-none rounded border-line accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface-2 disabled:opacity-60"
              />
              <span>
                <span className="font-medium">Aplicar a moldura da Manto</span>
                <span className="mt-0.5 block text-xs text-muted">
                  Ela é queimada no vídeo durante a conversão.{" "}
                  <strong className="font-medium text-ink">Decida antes de escolher o arquivo</strong>{" "}
                  — a escolha já começa o envio, não há botão de confirmar depois.
                  {status === "falhou" && " Vale também para o “Tentar de novo” acima."}
                </span>
              </span>
            </label>
            {erroMoldura && (
              <p className="mt-2 text-xs text-red" role="alert">
                {erroMoldura}
              </p>
            )}
          </div>

          {/* Minutos de espera para um arquivo de 150 MB: sem número na tela o silêncio parece
              conclusão e a janela é fechada no meio do envio. */}
          <AnimatePresence initial={false}>
            {preparando && (
              <motion.p
                key="preparando"
                role="status"
                initial={reduceMotion ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={reduceMotion ? undefined : { opacity: 0 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className="text-xs text-muted"
              >
                Preparando o arquivo para envio…
              </motion.p>
            )}
            {progresso !== null && (
              <motion.div
                key="progresso"
                initial={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
                className="overflow-hidden"
              >
                <UploadProgressBar fraction={progresso} />
              </motion.div>
            )}
          </AnimatePresence>

          {erroLeitura && (
            <p className="text-sm text-red" role="alert">
              {erroLeitura}
            </p>
          )}
          {erroEnvio && (
            <p className="text-sm text-red" role="alert">
              {erroEnvio}
            </p>
          )}
        </div>

        <DialogFooter>
          {delivery ? (
            <>
              <Button variant="outline" loading={enviando} onClick={() => inputRef.current?.click()}>
                <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Substituir
              </Button>
              <Button
                variant="outline"
                className="text-red"
                disabled={enviando}
                onClick={() => setConfirmandoRemocao(true)}
              >
                <Trash2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Remover
              </Button>
            </>
          ) : (
            <Button loading={enviando} onClick={() => inputRef.current?.click()}>
              <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Enviar vídeo
            </Button>
          )}
          <Button variant="ghost" onClick={close} disabled={enviando || remover.isPending}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>

      {/* Fora do DialogContent de propósito: diálogos irmãos, não aninhados (cada um com seu
          portal Radix). Erro da remoção aparece DENTRO da confirmação, que fica aberta. */}
      <ConfirmDialog
        open={confirmandoRemocao}
        title={`Remover o vídeo da tag nº ${tag?.sequence}`}
        description="A cliente deixa de ver o vídeo ao encostar o celular na peça — a página pública volta ao conteúdo padrão. O arquivo é apagado do servidor."
        confirmLabel="Remover vídeo"
        destructive
        pending={remover.isPending}
        error={remover.error?.message ?? null}
        onConfirm={handleRemove}
        onOpenChange={(open) => {
          setConfirmandoRemocao(open);
          if (!open) remover.reset();
        }}
      />
    </Dialog>
  );
}
