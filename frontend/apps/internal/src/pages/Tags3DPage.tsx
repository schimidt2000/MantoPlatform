import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Nfc } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  cn,
  CopyButton,
  formatShortDate,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { AssociarDialog } from "../components/nfc/AssociarDialog";
import { GerarLoteForm } from "../components/nfc/GerarLoteForm";
import { NfcVideosPanel } from "../components/nfc/NfcVideosPanel";
import { VideoDialog } from "../components/nfc/VideoDialog";
import { publicUrl } from "../components/nfc/helpers";
import { useAtualizarNfcTag, useNfcTags, type NfcTag } from "../lib/nfc";

/**
 * Tags NFC (`/3d/tags`, feature 255) — a ponte entre a tag física e o sistema.
 *
 * O fluxo real da equipe: gerar um lote, gravar as tagzinhas e anotar em cada uma o **Nº**
 * (1, 2, 3… por produto) — por isso o número é a primeira coluna e a mais forte da tabela.
 * Depois, na alocação, "nº X → evento/cliente Y" acontece aqui, pelo vínculo de evento.
 * Tag nunca é apagada (o código gravado é eterno): só desativar, que faz a página pública
 * responder o conteúdo genérico.
 *
 * Feature 265: a página virou duas abas — "Tags" (gestão, a tabela de sempre) e "Vídeos"
 * (revisão: o Artista 3D acompanha o que tem vídeo ou não e assiste pelo espelho admin,
 * que não conta acesso). A aba mora na URL (`?aba=videos`), padrão de
 * `FigurinoProducaoListPage`: link compartilhável, F5 mantém, troca com `replace`.
 */

export function Tags3DPage() {
  const reduceMotion = useReducedMotion();
  const query = useNfcTags();
  const update = useAtualizarNfcTag();
  const [searchParams, setSearchParams] = useSearchParams();
  const [associando, setAssociando] = useState<NfcTag | null>(null);
  const [videoTagId, setVideoTagId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  // Linha a destacar na tabela ao vir de "Ver na tabela" — efêmero de propósito (não vai
  // para a URL): highlight fantasma depois de um F5 pareceria estado, não gesto.
  const [destaqueId, setDestaqueId] = useState<number | null>(null);

  const aba = searchParams.get("aba") === "videos" ? "videos" : "tags";

  const tags = query.data?.tags ?? [];
  // Da lista viva, não uma cópia: assim o diálogo reflete o vídeo novo sem fechar (ver VideoDialog).
  const videoTag = tags.find((t) => t.id === videoTagId) ?? null;

  function trocarAba(valor: string) {
    const proximo = new URLSearchParams(searchParams);
    if (valor === "videos") proximo.set("aba", "videos");
    else proximo.delete("aba");
    setSearchParams(proximo, { replace: true });
  }

  function verNaTabela(tagId: number) {
    trocarAba("tags");
    setDestaqueId(tagId);
  }

  // Scroll + highlight depois que a aba Tags montou (rAF espera o TabsContent renderizar).
  // `TableRow` não tem forwardRef — a linha é achada pelo `id` no `<tr>`.
  useEffect(() => {
    if (aba !== "tags" || destaqueId === null) return;
    const frame = requestAnimationFrame(() => {
      document.getElementById(`nfc-tag-row-${destaqueId}`)?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "center",
      });
    });
    const timer = window.setTimeout(() => setDestaqueId(null), 2200);
    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [aba, destaqueId, reduceMotion]);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Tags NFC"
        subtitle="Uma linha por tag física. O Nº é o rótulo para anotar na tag ao gravar; a URL copiada aqui é o que se grava — ela nunca muda."
        className="mb-0"
      />

      <Tabs value={aba} onValueChange={trocarAba}>
        <TabsList>
          <TabsTrigger value="tags">Tags</TabsTrigger>
          <TabsTrigger value="videos">Vídeos</TabsTrigger>
        </TabsList>

        <TabsContent value="tags" className="space-y-4">
          <Card>
            <CardContent className="p-4">
              <h2 className="mb-3 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
                Gerar lote (estoque — vincula o evento depois)
              </h2>
              <GerarLoteForm />
            </CardContent>
          </Card>

          {query.isLoading && <Skeleton className="h-64 w-full" />}
          {query.isError && (
            <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
              Não foi possível carregar as tags NFC.
            </div>
          )}
          {query.data && tags.length === 0 && (
            <p className="text-sm text-muted">
              Nenhuma tag ainda. Elas nascem sozinhas quando um show ganha um presente 3D de
              peça habilitada para NFC — ou gere um lote acima.
            </p>
          )}

          {tags.length > 0 && (
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <Card>
                <CardContent className="overflow-x-auto p-0">
                  <Table>
                    <thead>
                      <TableRow head>
                        <TableCell as="th">Nº</TableCell>
                        <TableCell as="th">Código</TableCell>
                        <TableCell as="th">Produto</TableCell>
                        <TableCell as="th">Evento</TableCell>
                        <TableCell as="th">Cliente</TableCell>
                        <TableCell as="th">Vídeo</TableCell>
                        <TableCell as="th" align="right">
                          Acessos
                        </TableCell>
                        <TableCell as="th">Situação</TableCell>
                        <TableCell as="th" align="right">
                          Ações
                        </TableCell>
                      </TableRow>
                    </thead>
                    <tbody>
                      {tags.map((tag) => (
                        <TableRow
                          key={tag.id}
                          id={`nfc-tag-row-${tag.id}`}
                          className={cn(
                            "transition-colors duration-500",
                            !tag.is_active && "opacity-60",
                            destaqueId === tag.id && "bg-gold-soft",
                          )}
                        >
                          <TableCell>
                            {/* O rótulo físico da equipe — proposital que grite mais que o código. */}
                            <span className="font-display text-lg font-bold text-ink">
                              {tag.sequence}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="flex items-center gap-1.5">
                              <code className="text-xs text-muted">{tag.code}</code>
                              <CopyButton
                                value={publicUrl(tag.code)}
                                label={`Copiar link da tag nº ${tag.sequence}`}
                              />
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="flex items-center gap-2">
                              <img
                                src={assetUrl(tag.item.photo_url)}
                                alt=""
                                loading="lazy"
                                className="h-8 w-8 shrink-0 rounded-md object-cover"
                              />
                              <span className="max-w-40 truncate text-sm text-ink">
                                {tag.item.name}
                              </span>
                            </span>
                          </TableCell>
                          <TableCell>
                            {tag.event ? (
                              <span className="block max-w-52">
                                <span className="block truncate text-sm text-ink">
                                  {tag.event.title}
                                </span>
                                {tag.event.start_at && (
                                  <span className="text-xs text-muted">
                                    {formatShortDate(tag.event.start_at)}
                                  </span>
                                )}
                              </span>
                            ) : (
                              <span className="text-sm text-muted">— estoque</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <span className="flex items-center gap-1.5">
                              <span className="text-sm text-ink">{tag.client_name ?? "—"}</span>
                              {tag.client_direct && (
                                <span title="Vínculo direto na tag (sem show)">
                                  <Badge tone="gold">direta</Badge>
                                </span>
                              )}
                            </span>
                          </TableCell>
                          <TableCell>
                            {tag.video_delivery ? (
                              <button
                                type="button"
                                onClick={() => setVideoTagId(tag.id)}
                                aria-label={`Assistir o vídeo da tag nº ${tag.sequence}`}
                                title="Assistir sem contar acesso"
                              >
                                <Badge tone="blue">com vídeo</Badge>
                              </button>
                            ) : (
                              <Badge tone="neutral">sem vídeo</Badge>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            <span
                              className="text-sm text-muted"
                              title={
                                tag.last_accessed_at
                                  ? `Último acesso: ${formatShortDate(tag.last_accessed_at)}`
                                  : "Nunca acessada"
                              }
                            >
                              {tag.access_count}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge tone={tag.is_active ? "green" : "neutral"}>
                              {tag.is_active ? "Ativa" : "Inativa"}
                            </Badge>
                          </TableCell>
                          <TableCell align="right">
                            <span className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setAssociando(tag)}
                                aria-label={`Vincular evento ou cliente à tag nº ${tag.sequence}`}
                              >
                                {tag.event || tag.client ? "Editar vínculos" : "Vincular"}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setVideoTagId(tag.id)}
                                aria-label={`Vídeo da tag nº ${tag.sequence}`}
                              >
                                {tag.video_delivery ? "Editar vídeo" : "Vídeo"}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                loading={update.isPending && togglingId === tag.id}
                                className={cn(!tag.is_active && "text-green")}
                                onClick={() => {
                                  setTogglingId(tag.id);
                                  update.mutate({
                                    id: tag.id,
                                    input: { is_active: !tag.is_active },
                                  });
                                }}
                              >
                                {tag.is_active ? "Desativar" : "Reativar"}
                              </Button>
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </tbody>
                  </Table>
                </CardContent>
              </Card>
            </motion.div>
          )}

          <p className="flex items-center gap-1.5 text-xs text-muted">
            <Nfc className="h-3.5 w-3.5" aria-hidden="true" />
            Tags não podem ser apagadas: o código gravado numa peça entregue é eterno. Desativar
            faz a página pública mostrar o conteúdo padrão.
          </p>
        </TabsContent>

        <TabsContent value="videos">
          {query.isLoading && <Skeleton className="h-64 w-full" />}
          {query.isError && (
            <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
              Não foi possível carregar as tags NFC.
            </div>
          )}
          {query.data && (
            <NfcVideosPanel
              tags={tags}
              onManage={(tag) => setVideoTagId(tag.id)}
              onShowInTable={verNaTabela}
            />
          )}
        </TabsContent>
      </Tabs>

      <AssociarDialog tag={associando} onClose={() => setAssociando(null)} />
      <VideoDialog tag={videoTag} onClose={() => setVideoTagId(null)} />
    </div>
  );
}
