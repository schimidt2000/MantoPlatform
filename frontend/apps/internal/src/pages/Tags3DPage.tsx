import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Link2, Link2Off, Nfc } from "lucide-react";
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
import { useAcervo3D } from "../lib/impressoes3d";
import {
  useAtualizarNfcTag,
  useGerarLoteNfc,
  useNfcTags,
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

/** Vincular/trocar o evento de uma tag — busca textual da agenda (título, cliente, telefone). */
function AssociarDialog({ tag, onClose }: AssociarDialogProps) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const search = useAgendaSearch(query);
  const update = useAtualizarNfcTag();

  const options = useMemo(
    () =>
      (search.data?.items ?? []).map((ev) => ({
        value: String(ev.id),
        label: ev.start_at
          ? `${ev.title} — ${formatShortDate(ev.start_at)}`
          : ev.title,
        description: ev.client_name ?? undefined,
      })),
    [search.data],
  );

  function close() {
    setQuery("");
    setSelectedId(null);
    update.reset();
    onClose();
  }

  return (
    <Dialog open={tag !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent open={tag !== null} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Vincular evento — tag nº {tag?.sequence} ({tag?.code})
          </DialogTitle>
          <DialogDescription>
            O cliente vem junto do evento. A associação pode ser trocada a qualquer momento; o
            código gravado na tag nunca muda.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Combobox
            options={options}
            value={selectedId}
            onChange={(value) => setSelectedId(value)}
            onQueryChange={setQuery}
            placeholder="Buscar evento por título, cliente ou telefone…"
            aria-label="Buscar evento"
          />
          {search.isFetching && <p className="text-xs text-muted">Buscando…</p>}
          {fieldError(update.error, "event_id") && (
            <p className="text-sm text-red" role="alert">
              {fieldError(update.error, "event_id")}
            </p>
          )}
        </div>

        <DialogFooter>
          {tag?.event && (
            <Button
              variant="outline"
              loading={update.isPending}
              onClick={() =>
                tag &&
                update.mutate(
                  { id: tag.id, input: { event_id: null } },
                  { onSuccess: close },
                )
              }
            >
              <Link2Off className="mr-1.5 h-4 w-4" aria-hidden="true" />
              Desvincular
            </Button>
          )}
          <Button variant="ghost" onClick={close} disabled={update.isPending}>
            Cancelar
          </Button>
          <Button
            loading={update.isPending}
            disabled={selectedId === null}
            onClick={() =>
              tag &&
              selectedId !== null &&
              update.mutate(
                { id: tag.id, input: { event_id: Number(selectedId) } },
                { onSuccess: close },
              )
            }
          >
            <Link2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Vincular
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
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const tags = query.data?.tags ?? [];

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
                        <span className="text-sm text-ink">{tag.client_name ?? "—"}</span>
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
                            aria-label={`Vincular evento à tag nº ${tag.sequence}`}
                          >
                            {tag.event ? "Trocar evento" : "Vincular evento"}
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
    </div>
  );
}
