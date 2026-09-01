import { useMemo, useState } from "react";
import { Link2Off } from "lucide-react";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  formatShortDate,
} from "@manto/ui";
import { useAgendaSearch } from "../../lib/agenda";
import { useClientSearch } from "../../lib/clientes";
import { useAtualizarNfcTag, type NfcTag } from "../../lib/nfc";
import { fieldError } from "./helpers";

export interface AssociarDialogProps {
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
export function AssociarDialog({ tag, onClose }: AssociarDialogProps) {
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
