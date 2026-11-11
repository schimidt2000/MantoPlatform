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

const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** ISO naïve do backend lido como hora local (mesma regra do `@manto/ui/date`). */
function lerData(iso: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "sáb, 07/11/2026 · 15h30" — dia da semana ajuda a reconhecer a festa. */
function dataDoEvento(iso: string | null): string {
  const d = lerData(iso);
  if (!d) return "Sem data";
  const hora = d.getMinutes() ? `${d.getHours()}h${String(d.getMinutes()).padStart(2, "0")}` : `${d.getHours()}h`;
  return `${SEMANA[d.getDay()]}, ${formatShortDate(iso)} · ${hora}`;
}

/** Calendarinho da miniatura: dia grande e mês abreviado. */
function DiaDoEvento({ iso }: { iso: string | null }) {
  const d = lerData(iso);
  if (!d) return <span>?</span>;
  return (
    <span className="flex flex-col items-center leading-none">
      <span className="text-sm font-bold text-ink">{String(d.getDate()).padStart(2, "0")}</span>
      <span className="text-[9px] font-semibold">{MESES[d.getMonth()]}</span>
    </span>
  );
}

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
  // 336b: a tag se vincula antes da festa em quase todos os casos; o que já aconteceu só polui a
  // lista. Fica atrás de um botão para a exceção (vínculo atrasado, correção).
  const [comPassados, setComPassados] = useState(false);
  const eventSearch = useAgendaSearch(eventQuery, { futuros: !comPassados });
  const clientSearch = useClientSearch(clientQuery);
  const update = useAtualizarNfcTag();

  // Feature 336: o título tem cinco personagens e cortava a data do fim; as "iniciais" da
  // miniatura saíam "(R" ou meio emoji. Agora a miniatura é um calendarinho com o dia e a data
  // vai na linha de baixo, antes da cliente — o que a gente lembra de uma festa é o dia.
  const eventOptions = useMemo(
    () =>
      (eventSearch.data?.items ?? []).map((ev) => ({
        value: String(ev.id),
        label: ev.title,
        description:
          [dataDoEvento(ev.start_at), ev.client_name].filter(Boolean).join(" · ") || undefined,
        imageShape: "square" as const,
        fallbackIcon: <DiaDoEvento iso={ev.start_at} />,
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
    setComPassados(false);
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
            Show contratado: vincule o evento (a cliente é a do evento). Campanha ou brinde sem
            show: cadastre a pessoa em Clientes e vincule diretamente. Selecionar já salva; o
            código gravado na tag nunca muda.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm text-muted">
              Evento do show
              {tag?.event
                ? ` — atual: ${tag.event.title}${tag.event.start_at ? ` (${formatShortDate(tag.event.start_at)})` : ""}`
                : ""}
            </span>
            <Combobox
              options={eventOptions}
              value={null}
              onChange={(value) => value !== null && save({ event_id: Number(value) })}
              onQueryChange={setEventQuery}
              placeholder="Data (07/11), personagem, cliente ou telefone…"
              hintMessage={
                eventQuery.trim().length < 2
                  ? "Digite a data da festa, um personagem ou o nome da cliente."
                  : undefined
              }
              emptyMessage={
                comPassados
                  ? "Nenhum evento encontrado. Tente a data no formato 07/11."
                  : "Nenhum evento de hoje em diante. Tente a data (07/11) ou mostre os que já aconteceram."
              }
              aria-label="Buscar evento"
            />
            {fieldError(update.error, "event_id") && (
              <p className="mt-1 text-sm text-red" role="alert">
                {fieldError(update.error, "event_id")}
              </p>
            )}
          </label>
          <div className="-mt-2 flex flex-wrap items-center gap-x-2 text-xs text-muted">
            <span>
              {comPassados
                ? "Mostrando também eventos que já aconteceram."
                : "Mostrando eventos de hoje em diante."}
            </span>
            <button
              type="button"
              className="underline underline-offset-2 hover:text-ink"
              onClick={() => setComPassados((v) => !v)}
            >
              {comPassados ? "Só de hoje em diante" : "Mostrar os que já aconteceram"}
            </button>
          </div>

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
