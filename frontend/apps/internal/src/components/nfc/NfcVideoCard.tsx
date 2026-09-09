import { motion, useReducedMotion } from "framer-motion";
import { RotateCcw } from "lucide-react";
import { Badge, Button, Card, CopyButton, formatShortDate } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  adminNfcVideoUrl,
  formatarDuracao,
  formatarPeso,
  useReprocessarNfcVideo,
  type NfcTag,
} from "../../lib/nfc";
import { publicUrl } from "./helpers";

export interface NfcVideoCardProps {
  /** Tag garantidamente com `video_delivery` — o chamador filtra antes. */
  tag: NfcTag;
  /** Abre o VideoDialog (substituir/remover/título) desta tag. */
  onManage: (tag: NfcTag) => void;
  /** Volta para a aba Tags com a linha desta tag em destaque. */
  onShowInTable: (tagId: number) => void;
  /** Abre os recados que a cliente deixou nesta tag (feature 297). */
  onVerRecados: (tagId: number) => void;
}

/**
 * Card de revisão de um vídeo NFC (feature 265): o player toca pelo espelho admin —
 * assistir aqui NÃO conta acesso e funciona até com a tag desativada, ao contrário do
 * link público. O contexto de evento vem do cabeçalho do grupo (ver `NfcVideosPanel`),
 * então o card carrega só o que identifica a tag: nº, código, produto e cliente.
 *
 * A 297 acrescentou o estado da conversão em fundo. O player só é MONTADO quando a entrega
 * está `pronto`: era exatamente isto que produzia o print do dono, dez cards dizendo "o arquivo
 * está corrompido" — o navegador recebia um arquivo ainda em conversão e culpava o vídeo em vez
 * do relógio. Enquanto não termina, a caixa mostra o selo de estado no lugar do player.
 */
export function NfcVideoCard({ tag, onManage, onShowInTable, onVerRecados }: NfcVideoCardProps) {
  const reduceMotion = useReducedMotion();
  const reprocessar = useReprocessarNfcVideo();

  const delivery = tag.video_delivery;
  if (!delivery) return null;

  const pronto = delivery.processing_status === "pronto";
  const falhou = delivery.processing_status === "falhou";

  return (
    <Card className="flex flex-col overflow-hidden">
      {/* 9:16 e não 16:9: os vídeos das tags são gravados em pé no celular, e a caixa deitada
          reduzia cada um a uma tirinha no meio de duas faixas pretas gigantes.
          `object-contain` (e nunca `object-cover`) pela mesma lição de `CharacterCard.tsx:35`:
          `cover` corta o que não couber, e aqui isso decapitaria a cliente num vídeo mais
          quadrado — pior ainda quando `has_frame`, porque a moldura da Manto é queimada nas
          BORDAS e é justamente a borda que o `cover` come. `bg-media` (e não `bg-ink`, que
          inverte com o tema) é o token de moldura de player do design system. */}
      <div className="relative flex aspect-[9/16] w-full items-center justify-center overflow-hidden bg-media">
        {pronto ? (
          /* `preload="metadata"`: num grid com N players montados, `auto` multiplicaria o
             incidente de 26/08 (download inteiro por thread) por N. */
          <video
            key={delivery.id}
            src={adminNfcVideoUrl(tag.id, delivery.id)}
            controls
            playsInline
            preload="metadata"
            className="h-full w-full object-contain"
          />
        ) : (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            {falhou ? (
              <Badge tone="red">Falhou</Badge>
            ) : (
              /* O pulso é indicador contínuo, não troca de estado: por isso 1,6 s e não os
                 150–350 ms da constituição — abaixo de ~1 s a respiração vira estrobo. */
              <motion.div
                animate={reduceMotion ? { opacity: 1 } : { opacity: [1, 0.5, 1] }}
                transition={
                  reduceMotion
                    ? { duration: 0 }
                    : { duration: 1.6, repeat: Infinity, ease: "easeInOut" }
                }
              >
                <Badge tone="blue">Preparando…</Badge>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <p className="text-sm font-medium text-ink">
          {delivery.title || <span className="text-muted">Sem título — a página usa a copy padrão</span>}
        </p>
        <p className="flex flex-wrap items-center gap-1.5">
          <span className="font-display text-base font-bold text-ink">nº {tag.sequence}</span>
          <code className="text-xs text-muted">{tag.code}</code>
          <CopyButton value={publicUrl(tag.code)} label={`Copiar link da tag nº ${tag.sequence}`} />
          {!tag.is_active && <Badge tone="neutral">Inativa</Badge>}
          {tag.messages_unread > 0 && (
            /* Dourado é a cor de atenção do design system; `neutral` some no meio dos outros
               selos e o recado da cliente ficaria sem quem o lesse. */
            <button
              type="button"
              onClick={() => onVerRecados(tag.id)}
              aria-label={`Ver os recados não lidos da tag nº ${tag.sequence}`}
              className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-panel"
            >
              <Badge tone="gold">
                {tag.messages_unread === 1
                  ? "1 recado novo"
                  : `${tag.messages_unread} recados novos`}
              </Badge>
            </button>
          )}
        </p>
        <p className="flex items-center gap-2">
          <img
            src={assetUrl(tag.item.photo_url)}
            alt=""
            loading="lazy"
            className="h-6 w-6 shrink-0 rounded object-cover"
          />
          <span className="truncate text-sm text-ink">{tag.item.name}</span>
        </p>
        {/* `formatarPeso`/`formatarDuracao` já devolvem "—" enquanto a conversão não mediu o
            arquivo — o traço é informação (ainda não se sabe), não um buraco no layout. */}
        <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-muted">
          <span>{tag.client_name ?? "Sem cliente vinculada"}</span>
          {delivery.created_at && (
            <>
              <span aria-hidden="true">·</span>
              <span>enviado em {formatShortDate(delivery.created_at)}</span>
            </>
          )}
          <span aria-hidden="true">·</span>
          <span>{formatarPeso(delivery.file_size_bytes)}</span>
          <span aria-hidden="true">·</span>
          <span>{formatarDuracao(delivery.duration_seconds)}</span>
          {delivery.has_frame && <Badge tone="neutral">com moldura</Badge>}
        </p>

        {falhou && (
          /* O motivo fica no card, não num tooltip: quem revisa precisa saber se o arquivo veio
             quebrado (nada a fazer aqui) ou se a conversão tropeçou (vale tentar de novo). */
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="rounded-md border border-red/40 bg-red-50 p-2"
          >
            <p className="text-xs text-red" role="alert">
              {delivery.processing_error ?? "A conversão falhou sem detalhar o motivo."}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              loading={reprocessar.isPending}
              onClick={() => reprocessar.mutate({ tagId: tag.id, deliveryId: delivery.id })}
            >
              {!reprocessar.isPending && <RotateCcw className="h-4 w-4" aria-hidden="true" />}
              {reprocessar.isPending ? "Recolocando na fila…" : "Tentar de novo"}
            </Button>
            {reprocessar.error && (
              /* 409 = a entrega já voltou para a fila (outra aba, ou clique duplo): a mensagem
                 do envelope explica isso melhor do que um segundo reprocessamento. */
              <p className="mt-2 text-xs text-red" role="alert">
                {reprocessar.error.message}
              </p>
            )}
          </motion.div>
        )}

        <div className="mt-auto flex items-center gap-1.5 pt-1">
          <Button variant="ghost" size="sm" onClick={() => onManage(tag)}>
            Gerenciar vídeo
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onShowInTable(tag.id)}>
            Ver na tabela
          </Button>
        </div>
      </div>
    </Card>
  );
}
