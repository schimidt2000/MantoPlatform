import { Badge, Button, Card, CopyButton, formatShortDate } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { adminNfcVideoUrl, type NfcTag } from "../../lib/nfc";
import { publicUrl } from "./helpers";

export interface NfcVideoCardProps {
  /** Tag garantidamente com `video_delivery` — o chamador filtra antes. */
  tag: NfcTag;
  /** Abre o VideoDialog (substituir/remover/título) desta tag. */
  onManage: (tag: NfcTag) => void;
  /** Volta para a aba Tags com a linha desta tag em destaque. */
  onShowInTable: (tagId: number) => void;
}

/**
 * Card de revisão de um vídeo NFC (feature 265): o player toca pelo espelho admin —
 * assistir aqui NÃO conta acesso e funciona até com a tag desativada, ao contrário do
 * link público. O contexto de evento vem do cabeçalho do grupo (ver `NfcVideosPanel`),
 * então o card carrega só o que identifica a tag: nº, código, produto e cliente.
 */
export function NfcVideoCard({ tag, onManage, onShowInTable }: NfcVideoCardProps) {
  const delivery = tag.video_delivery;
  if (!delivery) return null;

  return (
    <Card className="flex flex-col overflow-hidden">
      {/* `preload="metadata"`: num grid com N players montados, `auto` multiplicaria o
          incidente de 26/08 (download inteiro por thread) por N. */}
      <video
        key={delivery.id}
        src={adminNfcVideoUrl(tag.id, delivery.id)}
        controls
        playsInline
        preload="metadata"
        className="aspect-video w-full bg-black"
      />
      <div className="flex flex-1 flex-col gap-2 p-3">
        <p className="text-sm font-medium text-ink">
          {delivery.title || <span className="text-muted">Sem título — a página usa a copy padrão</span>}
        </p>
        <p className="flex flex-wrap items-center gap-1.5">
          <span className="font-display text-base font-bold text-ink">nº {tag.sequence}</span>
          <code className="text-xs text-muted">{tag.code}</code>
          <CopyButton value={publicUrl(tag.code)} label={`Copiar link da tag nº ${tag.sequence}`} />
          {!tag.is_active && <Badge tone="neutral">Inativa</Badge>}
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
        <p className="text-xs text-muted">
          {tag.client_name ?? "Sem cliente vinculada"}
          {delivery.created_at && ` · enviado em ${formatShortDate(delivery.created_at)}`}
        </p>
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
