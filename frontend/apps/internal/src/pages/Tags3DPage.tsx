import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Link2Off, Nfc, Trash2, Upload } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  cn,
  Combobox,
  CopyButton,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  formatShortDate,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { useAgendaSearch } from "../lib/agenda";
import { useClientSearch } from "../lib/clientes";
import { useAcervo3D } from "../lib/impressoes3d";
import {
  useAtualizarNfcTag,
  useEnviarNfcVideo,
  useGerarLoteNfc,
  useNfcTags,
  useRemoverNfcVideo,
  type NfcTag,
} from "../lib/nfc";

/**
 * Tags NFC (`/3d/tags`, feature 255) — a ponte entre a tag física e o sistema.
 *
 * O fluxo real da equipe: gerar um lote, gravar as tagzinhas e anotar em cada uma o **Nº**
 * (1, 2, 3… por produto) — por isso o número é a primeira coluna e a mais forte da tabela.
 * Depois, na alocação, "nº X → evento/cliente Y" acontece aqui, pelo vínculo de evento.
 * Tag nunca é apagada (o código gravado é eterno): só desativar, que faz a página pública
 * responder o conteúdo genérico.
 */

/** Mensagem de campo devolvida pela API (400 com `fields`). */
function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

/** URL pública completa da tag — o que se grava na tag física e se copia daqui. */
function publicUrl(code: string): string {
  return `${window.location.origin}/nfc/${code}`;
}

interface AssociarDialogProps {
  tag: NfcTag | null;
  onClose: () => void;
}

/**
 * Vincular a tag a um evento OU direto a uma cliente (campanha/brinde sem show).
 *
 * Cada seleção num combobox SALVA na hora (PATCH) e fecha — sem botão "Salvar" que obrigaria a
 * lembrar de dois estados. Desvincular é ação explícita no rodapé. A cliente direta tem
 * precedência sobre a contratante do evento na lista.
 */
function AssociarDialog({ tag, onClose }: AssociarDialogProps) {
  const [eventQuery, setEventQuery] = useState("");
  const [clientQuery, setClientQuery] = useState("");
  const eventSearch = useAgendaSearch(eventQuery);
  const clientSearch = useClientSearch(clientQuery);
  const update = useAtualizarNfcTag();

  const eventOptions = useMemo(
    () =>
      (eventSearch.data?.items ?? []).map((ev) => ({
        value: String(ev.id),
        label: ev.start_at ? `${ev.title} — ${formatShortDate(ev.start_at)}` : ev.title,
        description: ev.client_name ?? undefined,
      })),
    [eventSearch.data],
  );
  const clientOptions = useMemo(
    () =>
      (clientSearch.data ?? []).map((cl) => ({
        value: String(cl.id),
        label: cl.name,
        description: cl.phone_display ?? undefined,
      })),
    [clientSearch.data],
  );

  function close() {
    setEventQuery("");
    setClientQuery("");
    update.reset();
    onClose();
  }

  function save(input: { event_id?: number | null; client_id?: number | null }) {
    if (tag) update.mutate({ id: tag.id, input }, { onSuccess: close });
  }

  return (
    <Dialog open={tag !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent open={tag !== null} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Vincular — tag nº {tag?.sequence} ({tag?.code})
          </DialogTitle>
          <DialogDescription>
            Show contratado: vincule o evento (a cliente vem de carona). Campanha ou brinde sem
            show: cadastre a pessoa em Clientes e vincule direto aqui. Escolher já salva; o
            código gravado na tag nunca muda.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm text-muted">
              Evento do show{tag?.event ? ` — atual: ${tag.event.title}` : ""}
            </span>
            <Combobox
              options={eventOptions}
              value={null}
              onChange={(value) => value !== null && save({ event_id: Number(value) })}
              onQueryChange={setEventQuery}
              placeholder="Buscar evento por título, cliente ou telefone…"
              aria-label="Buscar evento"
            />
            {fieldError(update.error, "event_id") && (
              <p className="mt-1 text-sm text-red" role="alert">
                {fieldError(update.error, "event_id")}
              </p>
            )}
          </label>

          <label className="block">
            <span className="mb-1 block text-sm text-muted">
              Cliente direta (sem show){tag?.client ? ` — atual: ${tag.client.name}` : ""}
            </span>
            <Combobox
              options={clientOptions}
              value={null}
              onChange={(value) => value !== null && save({ client_id: Number(value) })}
              onQueryChange={setClientQuery}
              placeholder="Buscar cliente por nome ou telefone…"
              aria-label="Buscar cliente"
            />
            {fieldError(update.error, "client_id") && (
              <p className="mt-1 text-sm text-red" role="alert">
                {fieldError(update.error, "client_id")}
              </p>
            )}
          </label>

          {(eventSearch.isFetching || clientSearch.isFetching) && (
            <p className="text-xs text-muted">Buscando…</p>
          )}
        </div>

        <DialogFooter>
          {tag?.event && (
            <Button
              variant="outline"
              loading={update.isPending}
              onClick={() => save({ event_id: null })}
            >
              <Link2Off className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Desvincular evento
            </Button>
          )}
          {tag?.client && (
            <Button
              variant="outline"
              loading={update.isPending}
              onClick={() => save({ client_id: null })}
            >
              <Link2Off className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Desvincular cliente
            </Button>
          )}
          <Button variant="ghost" onClick={close} disabled={update.isPending}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Extensões aceitas — espelha `NFC_DELIVERY_VIDEO_EXTENSIONS` de `app/constants.py`. */
const NFC_VIDEO_ACCEPT = ".mp4,.mov,.webm,.m4v";

interface VideoDialogProps {
  tag: NfcTag | null;
  onClose: () => void;
}

/**
 * Vídeo "Um vídeo especial para você" anexado à tag (feature 261).
 *
 * `tag` vem da lista viva (`tags.find`, não uma cópia local) — assim que o upload ou a remoção
 * invalidam a query, o diálogo continua aberto já mostrando o novo estado, sem fechar e reabrir.
 * Sem vídeo: escolhe o arquivo (a escolha já dispara o envio, mesmo padrão de
 * `FilaProducaoMidiaPage`). Com vídeo: nome + data do envio, Substituir (reabre o seletor) e
 * Remover (com confirmação). O campo de título aparece nos dois estados, pré-carregado com o
 * título salvo — Substituir reenvia o que estiver no campo, então nada some sem o admin ver.
 */
function VideoDialog({ tag, onClose }: VideoDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
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
    if (!window.confirm("Remover o vídeo desta tag? A cliente deixa de vê-lo ao encostar o celular.")) {
      return;
    }
    remover.mutate({ tagId: tag.id, deliveryId: delivery.id });
  }

  return (
    <Dialog open={tag !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent open={tag !== null} className="max-w-md">
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

          {delivery && (
            <div className="rounded-md border border-line bg-surface-2 p-3">
              <p className="text-sm font-medium text-ink">
                {delivery.title || "Sem título — a página usa a copy padrão"}
              </p>
              <p className="mt-1 text-xs text-muted">
                {delivery.file_name}
                {delivery.created_at && ` · enviado em ${formatShortDate(delivery.created_at)}`}
              </p>
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
          {remover.error && (
            <p className="text-sm text-red" role="alert">
              {remover.error.message}
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
                loading={remover.isPending}
                onClick={handleRemove}
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
    </Dialog>
  );
}

/** Formulário de lote: peça NFC + quantidade. As tags nascem sem evento (estoque). */
function GerarLoteForm() {
  const acervo = useAcervo3D();
  const gerar = useGerarLoteNfc();
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [geradas, setGeradas] = useState<number | null>(null);

  const nfcItems = useMemo(
    () => (acervo.data?.items ?? []).filter((i) => i.nfc_prefix !== null && i.is_active),
    [acervo.data],
  );
  const options = nfcItems.map((i) => ({
    value: String(i.id),
    label: `${i.name} (prefixo ${i.nfc_prefix})`,
  }));

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setGeradas(null);
    gerar.mutate(
      { item_id: Number(itemId), quantity: Number(quantity) || 0 },
      { onSuccess: (data) => setGeradas(data.tags.length) },
    );
  }

  if (!acervo.isLoading && nfcItems.length === 0) {
    return (
      <p className="text-sm text-muted">
        Nenhuma peça do Acervo está habilitada para NFC. Defina o “Prefixo NFC” de uma peça na
        tela Acervo 3D para começar a gerar tags.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <label className="min-w-56 flex-1">
        <span className="mb-1 block text-sm text-muted">Peça do Acervo (habilitada p/ NFC)</span>
        <Combobox
          options={options}
          value={itemId}
          onChange={setItemId}
          placeholder="Escolher peça…"
          aria-label="Peça do Acervo habilitada para NFC"
        />
        {fieldError(gerar.error, "item_id") && (
          <p className="mt-1 text-sm text-red" role="alert">
            {fieldError(gerar.error, "item_id")}
          </p>
        )}
      </label>
      <label className="w-28">
        <span className="mb-1 block text-sm text-muted">Quantidade</span>
        <Input
          type="number"
          min={1}
          max={999}
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          aria-invalid={Boolean(fieldError(gerar.error, "quantity"))}
          aria-label="Quantidade de tags"
        />
      </label>
      <Button type="submit" loading={gerar.isPending} disabled={itemId === null}>
        Gerar tags
      </Button>
      {fieldError(gerar.error, "quantity") && (
        <p className="w-full text-sm text-red" role="alert">
          {fieldError(gerar.error, "quantity")}
        </p>
      )}
      {geradas !== null && (
        <p className="w-full text-sm text-green" aria-live="polite">
          {geradas === 1 ? "1 tag gerada" : `${geradas} tags geradas`} — anote o Nº em cada
          tagzinha ao gravar.
        </p>
      )}
    </form>
  );
}

export function Tags3DPage() {
  const reduceMotion = useReducedMotion();
  const query = useNfcTags();
  const update = useAtualizarNfcTag();
  const [associando, setAssociando] = useState<NfcTag | null>(null);
  const [videoTagId, setVideoTagId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const tags = query.data?.tags ?? [];
  // Da lista viva, não uma cópia: assim o diálogo reflete o vídeo novo sem fechar (ver VideoDialog).
  const videoTag = tags.find((t) => t.id === videoTagId) ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Tags NFC"
        subtitle="Uma linha por tag física. O Nº é o rótulo para anotar na tag ao gravar; a URL copiada aqui é o que se grava — ela nunca muda."
        className="mb-0"
      />

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
          Nenhuma tag ainda. Elas nascem sozinhas quando um show ganha um presente 3D de peça
          habilitada para NFC — ou gere um lote acima.
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
                    <TableRow key={tag.id} className={tag.is_active ? undefined : "opacity-60"}>
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
        Tags não podem ser apagadas: o código gravado numa peça entregue é eterno. Desativar faz
        a página pública mostrar o conteúdo padrão.
      </p>

      <AssociarDialog tag={associando} onClose={() => setAssociando(null)} />
      <VideoDialog tag={videoTag} onClose={() => setVideoTagId(null)} />
    </div>
  );
}
