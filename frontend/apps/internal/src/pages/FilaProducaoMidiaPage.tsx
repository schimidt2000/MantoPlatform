import { useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, MessageCircle, Upload, Video } from "lucide-react";
import {
  AvatarThumb,
  Badge,
  Button,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { AvisosFalhosBanner } from "../components/AvisosFalhosBanner";
import {
  PRODUCAO_STATUSES,
  PRODUCAO_STATUS_LABELS,
  PRODUCAO_STATUS_TONES,
  useAtualizarStatusEntrega,
  useEnviarVideo,
  useFilaProducao,
  type ProducaoStatus,
  type VirtualDelivery,
} from "../lib/virtuais";

/**
 * Fila de Produção de Mídia (feature 205, US5) — espelha a arquitetura da Fila 3D (feature 200).
 *
 * Tabela densa, **uma linha por entrega**, com os quatro blocos que o talento precisa na mesma
 * altura (FR-046): horário/modalidade, criança, dicas da família e o presente 3D. Sem isso, quem
 * grava teria que abrir três telas para montar uma chamada de 10 minutos.
 *
 * Os únicos estados são `pendente`, `gravando` e `finalizado` (FR-048a). Enviar o vídeo é a
 * **ação** que permite chegar a `finalizado` — por isso o botão de envio fica na própria linha, e
 * finalizar sem vídeo é recusado pelo servidor.
 */

function formatarQuando(delivery: VirtualDelivery): string {
  if (delivery.start_at) {
    return new Date(delivery.start_at).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  if (delivery.due_date) {
    return `até ${new Date(delivery.due_date).toLocaleDateString("pt-BR")}`;
  }
  return "—";
}

function DeliveryRow({ delivery }: { delivery: VirtualDelivery }) {
  const atualizar = useAtualizarStatusEntrega();
  const enviarVideo = useEnviarVideo();
  const inputArquivo = useRef<HTMLInputElement>(null);
  const [erro, setErro] = useState<string | null>(null);

  const gravado = delivery.modality === "gravado";

  return (
    <TableRow className={delivery.prazo_vencido ? "bg-red-soft/40" : undefined}>
      {/* Horário e modalidade */}
      <TableCell>
        <div className="font-medium text-ink">{formatarQuando(delivery)}</div>
        <div className="flex items-center gap-1 text-[11px] text-muted">
          {gravado ? "Vídeo gravado" : "Ao vivo"}
          {delivery.prazo_vencido && (
            <span className="inline-flex items-center gap-0.5 text-red">
              <AlertTriangle className="size-3" />
              vencido
            </span>
          )}
          {!delivery.prazo_vencido && delivery.prazo_proximo && (
            <span className="text-gold">· vence logo</span>
          )}
        </div>
      </TableCell>

      {/* Criança */}
      <TableCell>
        <div className="font-medium text-ink">{delivery.child_name}</div>
        <div className="text-[11px] text-muted">
          {delivery.child_age} anos · {delivery.campaign_title}
        </div>
      </TableCell>

      {/* Dicas da família — é o que faz a interação parecer sob medida. */}
      <TableCell className="max-w-xs">
        {delivery.behavior_notes ? (
          <p className="whitespace-pre-line text-[12px] text-ink">{delivery.behavior_notes}</p>
        ) : (
          <span className="text-[12px] text-muted">— sem dicas —</span>
        )}
      </TableCell>

      {/* Presente 3D */}
      <TableCell>
        {delivery.gift?.item ? (
          <div className="flex items-center gap-2">
            <AvatarThumb
              src={assetUrl(delivery.gift.item.photo_url)}
              name={delivery.gift.item.name}
              shape="square"
              size="sm"
              fallbackIcon="🎁"
            />
            <div className="min-w-0">
              <div className="truncate text-[12px] text-ink">{delivery.gift.item.name}</div>
              <Badge tone={delivery.gift.status === "entregue" ? "green" : "neutral"}>
                {delivery.gift.status}
              </Badge>
            </div>
          </div>
        ) : (
          <span className="text-[12px] text-muted">sem presente</span>
        )}
      </TableCell>

      {/* Situação */}
      <TableCell>
        <div className="flex flex-col gap-1">
          <Badge tone={PRODUCAO_STATUS_TONES[delivery.status]}>
            {PRODUCAO_STATUS_LABELS[delivery.status]}
          </Badge>
          <select
            aria-label={`Situação de ${delivery.child_name}`}
            className="rounded border border-line bg-surface px-1 py-0.5 text-[11px] text-ink"
            value={delivery.status}
            disabled={atualizar.isPending}
            onChange={(e) => {
              setErro(null);
              atualizar.mutate(
                { id: delivery.id, status: e.target.value as ProducaoStatus },
                { onError: (err) => setErro(err.message) },
              );
            }}
          >
            {PRODUCAO_STATUSES.map((s) => (
              <option key={s} value={s}>
                {PRODUCAO_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          {(erro || delivery.last_upload_error) && (
            <span className="text-[11px] text-red">{erro ?? delivery.last_upload_error}</span>
          )}
          {/* Aviso que não chegou à família (FR-039c). Fica na coluna do status, e não nas ações,
              porque é informação sobre a entrega — a ação vem dentro do próprio banner. */}
          <AvisosFalhosBanner
            orderId={delivery.order_id}
            avisos={delivery.avisos_falhos}
            meetRetryEsgotado={delivery.meet_retry_esgotado}
            meetAttempts={delivery.meet_attempts}
            whatsappUrl={delivery.whatsapp_url}
            compacto
          />
        </div>
      </TableCell>

      {/* Ações: sala (ao vivo), envio do vídeo (gravado) e reforço por WhatsApp */}
      <TableCell align="right">
        <div className="flex items-center justify-end gap-1">
          {!gravado &&
            (delivery.meet_url ? (
              <Button size="sm" variant="outline" asChild>
                <a href={delivery.meet_url} target="_blank" rel="noopener noreferrer">
                  <Video className="size-4" />
                  Sala
                </a>
              </Button>
            ) : (
              // "pendente" e "desistiu" pedem reações opostas: a primeira é esperar, a segunda é
              // agir agora. Um badge só para os dois casos esconderia exatamente o que urge.
              <Badge tone={delivery.meet_retry_esgotado ? "red" : "gold"}>
                {delivery.meet_retry_esgotado ? "sala falhou" : "sala pendente"}
              </Badge>
            ))}

          {gravado && (
            <>
              <input
                ref={inputArquivo}
                type="file"
                accept="video/mp4,video/quicktime,video/webm"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setErro(null);
                  enviarVideo.mutate(
                    { id: delivery.id, file },
                    { onError: (err) => setErro(err.message) },
                  );
                  e.target.value = "";
                }}
              />
              <Button
                size="sm"
                variant={delivery.has_video ? "outline" : "default"}
                loading={enviarVideo.isPending}
                onClick={() => inputArquivo.current?.click()}
              >
                <Upload className="size-4" />
                {delivery.has_video ? "Substituir" : "Enviar vídeo"}
              </Button>
            </>
          )}

          {delivery.whatsapp_url && (
            <Button size="sm" variant="ghost" asChild>
              <a href={delivery.whatsapp_url} target="_blank" rel="noopener noreferrer">
                <MessageCircle className="size-4" />
              </a>
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

export function FilaProducaoMidiaPage() {
  const reduceMotion = useReducedMotion();
  const [status, setStatus] = useState<ProducaoStatus | "">("");
  const [date, setDate] = useState("");

  const { data, isLoading, isError, isFetching } = useFilaProducao({
    status: status || null,
    date: date || null,
  });
  const deliveries = data?.deliveries ?? [];

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Fila de Produção de Mídia"
        subtitle="O que precisa ser gravado e entregue — uma linha por interação vendida."
        filters={
          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Filtrar por situação"
              className="min-h-[36px] rounded-lg border border-line bg-surface px-2 text-[13px] text-ink"
              value={status}
              onChange={(e) => setStatus(e.target.value as ProducaoStatus | "")}
            >
              <option value="">Todas as situações</option>
              {PRODUCAO_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {PRODUCAO_STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <Input
              type="date"
              aria-label="Filtrar por data"
              className="max-w-40"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            {(status || date) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setStatus("");
                  setDate("");
                }}
              >
                Limpar
              </Button>
            )}
            {isFetching && <span className="text-[12px] text-muted">atualizando…</span>}
          </div>
        }
      />

      {isLoading && <Skeleton className="h-32 w-full" />}

      {isError && (
        <div className="rounded-lg border border-red/30 bg-red-soft p-4 text-sm text-red">
          Não foi possível carregar a fila.
        </div>
      )}

      {!isLoading && !isError && deliveries.length === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-line p-10 text-center">
          <Video className="size-8 text-muted" />
          <p className="text-sm text-muted">Nenhuma entrega nesta seleção.</p>
        </div>
      )}

      {!isLoading && !isError && deliveries.length > 0 && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Table>
            <thead>
              <TableRow head>
                <TableCell as="th">Quando</TableCell>
                <TableCell as="th">Criança</TableCell>
                <TableCell as="th">Dicas da família</TableCell>
                <TableCell as="th">Presente 3D</TableCell>
                <TableCell as="th">Situação</TableCell>
                <TableCell as="th" align="right">
                  Ações
                </TableCell>
              </TableRow>
            </thead>
            <tbody>
              {deliveries.map((delivery) => (
                <DeliveryRow key={delivery.id} delivery={delivery} />
              ))}
            </tbody>
          </Table>
        </motion.div>
      )}
    </div>
  );
}
