import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Frame } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  DenseCard,
  type DenseCardStat,
  formatShortDate,
  Input,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import type { NfcProcessingStatus, NfcTag } from "../../lib/nfc";
import { MolduraDialog } from "./MolduraDialog";
import { NfcVideoCard } from "./NfcVideoCard";
import { RecadosDaTag } from "./RecadosDaTag";

export interface NfcVideosPanelProps {
  tags: NfcTag[];
  /** Abre o VideoDialog da tag (enviar, substituir, remover). */
  onManage: (tag: NfcTag) => void;
  /** Volta para a aba Tags com a linha da tag em destaque. */
  onShowInTable: (tagId: number) => void;
}

/** Grupo de cards: um evento, as clientes diretas ou o estoque. */
interface VideoGroup {
  key: string;
  title: string;
  subtitle?: string;
  tags: NfcTag[];
}

/** Entrega que ainda não virou vídeo entregável — o que o KPI "Preparando" conta (feature 297). */
const STATUS_PREPARANDO: readonly NfcProcessingStatus[] = ["pendente", "processando"];

function normaliza(texto: string): string {
  return texto.toLowerCase();
}

function combinaBusca(tag: NfcTag, busca: string): boolean {
  if (!busca) return true;
  const alvo = normaliza(
    [tag.code, String(tag.sequence), tag.item.name, tag.event?.title ?? "", tag.client_name ?? ""].join(" "),
  );
  return alvo.includes(normaliza(busca));
}

/**
 * Aba "Vídeos" de `/3d/tags` (feature 265) — o painel de revisão do Artista 3D.
 *
 * KPIs em cima (sobre TODAS as tags, a busca não mexe neles), cards com player agrupados por
 * evento (data desc) → clientes diretas → estoque, e no fim a lista do que ainda FALTA:
 * tags ativas sem vídeo, cada uma com o botão de enviar direto. Os grupos espelham a
 * precedência que a tabela já usa (evento > cliente direta > estoque). Tags inativas com
 * vídeo continuam visíveis (badge "Inativa") — auditáveis por dentro, invisíveis lá fora.
 *
 * A 297 acrescentou o KPI da fila de conversão ("Preparando", que só aparece quando há fila),
 * os recados de uma tag e os arquivos únicos do sistema (moldura e vídeo de abertura).
 */
export function NfcVideosPanel({ tags, onManage, onShowInTable }: NfcVideosPanelProps) {
  const reduceMotion = useReducedMotion();
  const [busca, setBusca] = useState("");
  /** Tag cujos recados estão abertos; `null` = nenhum painel aberto (a query nem dispara). */
  const [tagRecados, setTagRecados] = useState<number | null>(null);
  const [molduraAberta, setMolduraAberta] = useState(false);

  /**
   * Abre os recados de uma tag. Aceita a tag inteira ou só o id porque os dois formatos
   * convivem nos callbacks desta tela (`onManage` recebe a tag, `onShowInTable` recebe o id) —
   * o card chama do jeito que for natural para ele e o painel guarda sempre o id.
   */
  function abrirRecados(alvo: NfcTag | number): void {
    setTagRecados(typeof alvo === "number" ? alvo : alvo.id);
  }

  const kpis = useMemo(() => {
    const ativas = tags.filter((t) => t.is_active);
    return {
      ativas: ativas.length,
      comVideo: ativas.filter((t) => t.video_delivery).length,
      semVideo: ativas.filter((t) => !t.video_delivery).length,
      nuncaAcessadas: ativas.filter((t) => t.access_count === 0).length,
      // Sobre TODAS as tags, e não só as ativas: a fila é a da conversão em fundo, e uma tag
      // desativada com vídeo em processamento ocupa a mesma fila — sumir com ela aqui faria o
      // painel dizer "nada preparando" enquanto o servidor ainda converte.
      preparando: tags.filter(
        (t) => t.video_delivery !== null && STATUS_PREPARANDO.includes(t.video_delivery.processing_status),
      ).length,
    };
  }, [tags]);

  const stats: DenseCardStat[] = [
    { label: "Tags ativas", value: kpis.ativas },
    { label: "Com vídeo", value: kpis.comVideo },
    { label: "Sem vídeo", value: kpis.semVideo },
    { label: "Nunca acessadas", value: kpis.nuncaAcessadas },
  ];
  if (kpis.preparando > 0) {
    stats.push({
      label: "Preparando",
      // O KPI só existe enquanto há fila, então ele ENTRA na faixa no meio da leitura (o polling
      // de `useNfcTags` remonta a lista sozinho). A transição vive no valor porque a célula é
      // desenhada pelo DenseCard — sem ela o número simplesmente aparece do nada.
      value: (
        <motion.span
          initial={reduceMotion ? false : { opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="inline-block"
        >
          {kpis.preparando}
        </motion.span>
      ),
    });
  }

  const { grupos, semVideo } = useMemo(() => {
    const visiveis = tags.filter((t) => combinaBusca(t, busca));
    const comVideo = visiveis.filter((t) => t.video_delivery);

    const porEvento = new Map<number, VideoGroup>();
    const diretas: NfcTag[] = [];
    const estoque: NfcTag[] = [];
    for (const tag of comVideo) {
      if (tag.event) {
        const grupo = porEvento.get(tag.event.id);
        if (grupo) {
          grupo.tags.push(tag);
        } else {
          porEvento.set(tag.event.id, {
            key: `evento-${tag.event.id}`,
            title: tag.event.title,
            subtitle: tag.event.start_at ? formatShortDate(tag.event.start_at) : undefined,
            tags: [tag],
          });
        }
      } else if (tag.client) {
        diretas.push(tag);
      } else {
        estoque.push(tag);
      }
    }

    // Eventos mais recentes primeiro (é neles que a revisão acontece); sem data por último.
    const eventos = [...porEvento.values()].sort((a, b) => {
      const dataA = startAtDe(a);
      const dataB = startAtDe(b);
      if (dataA === dataB) return 0;
      if (dataA === null) return 1;
      if (dataB === null) return -1;
      return dataA < dataB ? 1 : -1;
    });

    const resultado: VideoGroup[] = [...eventos];
    if (diretas.length > 0) {
      resultado.push({ key: "diretas", title: "Clientes diretas (sem show)", tags: diretas });
    }
    if (estoque.length > 0) {
      resultado.push({ key: "estoque", title: "Estoque", tags: estoque });
    }

    return {
      grupos: resultado,
      semVideo: visiveis.filter((t) => t.is_active && !t.video_delivery),
    };

    function startAtDe(grupo: VideoGroup): string | null {
      return grupo.tags[0]?.event?.start_at ?? null;
    }
  }, [tags, busca]);

  const nadaComVideo = grupos.length === 0;

  return (
    <div className="space-y-4">
      <DenseCard
        title="Vídeos das tags"
        headerRight={
          <Button variant="outline" size="sm" onClick={() => setMolduraAberta(true)}>
            <Frame className="h-4 w-4" aria-hidden="true" />
            Moldura e abertura
          </Button>
        }
        stats={stats}
      />

      <Input
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        placeholder="Buscar por código, nº, produto, evento ou cliente…"
        aria-label="Buscar tag"
        className="max-w-md"
      />

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
        className="space-y-6"
      >
        {nadaComVideo && (
          <p className="text-sm text-muted">
            {busca
              ? "Nenhum vídeo encontrado para essa busca."
              : "Nenhuma tag tem vídeo ainda — use a lista abaixo para enviar o primeiro."}
          </p>
        )}

        {grupos.map((grupo) => (
          <section key={grupo.key} aria-label={grupo.title}>
            <div className="mb-2 flex flex-wrap items-baseline gap-2">
              <h3 className="text-sm font-semibold text-ink">{grupo.title}</h3>
              {grupo.subtitle && <span className="text-xs text-muted">{grupo.subtitle}</span>}
              <Badge tone="blue">
                {grupo.tags.length === 1 ? "1 vídeo" : `${grupo.tags.length} vídeos`}
              </Badge>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {grupo.tags.map((tag) => (
                <NfcVideoCard
                  key={tag.id}
                  tag={tag}
                  onManage={onManage}
                  onShowInTable={onShowInTable}
                  onVerRecados={abrirRecados}
                />
              ))}
            </div>
          </section>
        ))}

        <section aria-label="Tags sem vídeo">
          <div className="mb-2 flex flex-wrap items-baseline gap-2">
            <h3 className="text-sm font-semibold text-ink">Sem vídeo</h3>
            <span className="text-xs text-muted">tags ativas aguardando o vídeo da cliente</span>
          </div>
          {semVideo.length === 0 ? (
            <p className="text-sm text-green">
              {busca ? "Nenhuma tag sem vídeo nessa busca." : "Todas as tags ativas têm vídeo."}
            </p>
          ) : (
            <Card>
              <CardContent className="overflow-x-auto p-0">
                <Table>
                  <thead>
                    <TableRow head>
                      <TableCell as="th">Nº</TableCell>
                      <TableCell as="th">Código</TableCell>
                      <TableCell as="th">Produto</TableCell>
                      <TableCell as="th">Evento / cliente</TableCell>
                      <TableCell as="th" align="right">
                        Ações
                      </TableCell>
                    </TableRow>
                  </thead>
                  <tbody>
                    {semVideo.map((tag) => (
                      <TableRow key={tag.id}>
                        <TableCell>
                          <span className="font-display text-base font-bold text-ink">{tag.sequence}</span>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs text-muted">{tag.code}</code>
                        </TableCell>
                        <TableCell>
                          <span className="max-w-40 truncate text-sm text-ink">{tag.item.name}</span>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-muted">
                            {tag.event?.title ?? tag.client_name ?? "— estoque"}
                          </span>
                        </TableCell>
                        <TableCell align="right">
                          <span className="flex items-center justify-end gap-1.5">
                            <Button variant="ghost" size="sm" onClick={() => onManage(tag)}>
                              Enviar vídeo
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => onShowInTable(tag.id)}>
                              Ver na tabela
                            </Button>
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              </CardContent>
            </Card>
          )}
        </section>
      </motion.div>

      {/* Montado só com tag escolhida: é o `tagId` que liga a query de recados (`useRecadosDaTag`). */}
      {tagRecados !== null && (
        <RecadosDaTag tagId={tagRecados} onFechar={() => setTagRecados(null)} />
      )}

      <MolduraDialog aberto={molduraAberta} onFechar={() => setMolduraAberta(false)} />
    </div>
  );
}
