import { useEffect, useRef, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import {
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
  useEnviarNfcVideo,
  useRemoverNfcVideo,
  type NfcTag,
} from "../../lib/nfc";
import { fieldError, NFC_VIDEO_ACCEPT } from "./helpers";

export interface VideoDialogProps {
  tag: NfcTag | null;
  onClose: () => void;
}

/**
 * Vídeo "Um vídeo especial para você" anexado à tag (feature 261).
 *
 * `tag` vem da lista viva (`tags.find`, não uma cópia local) — assim que o upload ou a remoção
 * invalidam a query, o diálogo continua aberto já mostrando o novo estado, sem fechar e reabrir.
 * Sem vídeo: escolhe o arquivo (a escolha já dispara o envio, mesmo padrão de
 * `FilaProducaoMidiaPage`). Com vídeo: player de revisão (feature 265 — toca pelo espelho
 * admin, que não conta acesso), nome + data do envio, Substituir (reabre o seletor) e Remover
 * (ConfirmDialog, Princípio V). O campo de título aparece nos dois estados, pré-carregado com
 * o título salvo — Substituir reenvia o que estiver no campo, então nada some sem o admin ver.
 */
export function VideoDialog({ tag, onClose }: VideoDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [confirmandoRemocao, setConfirmandoRemocao] = useState(false);
  const enviar = useEnviarNfcVideo();
  const remover = useRemoverNfcVideo();
  const delivery = tag?.video_delivery ?? null;

  // Pré-carrega o título salvo ao abrir (e ao trocar de tag/vídeo): Substituir manda o campo
  // junto com o arquivo novo — sem isso, o título personalizado sumiria da página pública.
  useEffect(() => {
    setTitle(tag?.video_delivery?.title ?? "");
  }, [tag?.id, tag?.video_delivery?.id, tag?.video_delivery?.title]);

  function close() {
    setTitle("");
    setConfirmandoRemocao(false);
    enviar.reset();
    remover.reset();
    onClose();
  }

  function handleFile(file: File) {
    if (!tag) return;
    enviar.mutate({ tagId: tag.id, file, title: title.trim() || undefined });
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
              if (file) handleFile(file);
            }}
          />

          {tag && delivery && (
            <div className="space-y-2">
              {/* `key` remonta o player quando Substituir troca a entrega (src novo, buffer
                  limpo). `preload="metadata"` é inegociável — ver o incidente documentado em
                  `revisao/VideoPlayer.tsx`: `auto` baixa o arquivo inteiro por thread. */}
              <video
                key={delivery.id}
                src={adminNfcVideoUrl(tag.id, delivery.id)}
                controls
                playsInline
                preload="metadata"
                className="aspect-video w-full rounded-md bg-black"
              />
              <div className="rounded-md border border-line bg-surface-2 p-3">
                <p className="text-sm font-medium text-ink">
                  {delivery.title || "Sem título — a página usa a copy padrão"}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {delivery.file_name}
                  {delivery.created_at && ` · enviado em ${formatShortDate(delivery.created_at)}`}
                </p>
              </div>
            </div>
          )}

          <label className="block">
            <span className="mb-1 block text-sm text-muted">Título (opcional)</span>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Um vídeo especial para você"
              aria-label="Título do vídeo"
            />
            <span className="mt-1 block text-xs text-muted">
              Formatos aceitos: MP4, MOV, WEBM, M4V.
              {delivery && " Substituir grava o título acima junto com o vídeo novo."}
            </span>
          </label>

          {enviar.error && (
            <p className="text-sm text-red" role="alert">
              {fieldError(enviar.error, "file") ?? enviar.error.message}
            </p>
          )}
        </div>

        <DialogFooter>
          {delivery ? (
            <>
              <Button
                variant="outline"
                loading={enviar.isPending}
                onClick={() => inputRef.current?.click()}
              >
                <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Substituir
              </Button>
              <Button
                variant="outline"
                className="text-red"
                onClick={() => setConfirmandoRemocao(true)}
              >
                <Trash2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                Remover
              </Button>
            </>
          ) : (
            <Button loading={enviar.isPending} onClick={() => inputRef.current?.click()}>
              <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Enviar vídeo
            </Button>
          )}
          <Button variant="ghost" onClick={close} disabled={enviar.isPending || remover.isPending}>
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
