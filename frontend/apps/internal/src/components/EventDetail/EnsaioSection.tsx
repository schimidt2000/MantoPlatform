import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import { useAgendaSearch } from "../../lib/agenda";
import {
  useAssignPresenca,
  useCreateEnsaio,
  useDeleteEnsaio,
  useDeleteEnsaioFromShow,
  useEditEnsaio,
  useVincularEnsaio,
} from "../../lib/eventDetail";
import { useTalents } from "../../lib/casting";
import { Empty, INPUT_CLASS, Panel } from "./parts";

const LABEL = "mb-1 block text-xs font-medium text-muted";

function formatEnsaioLabel(startAt: string | null, endAt: string | null): string {
  if (!startAt) return "Sem data";
  const start = new Date(startAt);
  const day = start.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  const startTime = start.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const endTime = endAt
    ? new Date(endAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : "";
  return endTime ? `${day} · ${startTime}–${endTime}` : `${day} · ${startTime}`;
}

/** Formulário de agendamento — usado no show (criar) e na página do ensaio (editar). */
function EnsaioForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
}: {
  initial?: { date: string; start: string; end: string; description: string; location: string };
  submitLabel: string;
  pending: boolean;
  error: string | null;
  onSubmit: (values: {
    date: string;
    start: string;
    end: string;
    description: string;
    location_type: "manto" | "outro";
    location: string;
  }) => void;
}) {
  const [date, setDate] = useState(initial?.date ?? "");
  const [start, setStart] = useState(initial?.start ?? "");
  const [end, setEnd] = useState(initial?.end ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [locationType, setLocationType] = useState<"manto" | "outro">(
    initial?.location ? "outro" : "manto",
  );
  const [location, setLocation] = useState(initial?.location ?? "");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ date, start, end, description, location_type: locationType, location });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-md border border-dashed border-line p-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div>
          <label className={LABEL}>Data</label>
          <input
            type="date"
            className={INPUT_CLASS}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>
        <div>
          <label className={LABEL}>Início</label>
          <input
            type="time"
            className={INPUT_CLASS}
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
        </div>
        <div>
          <label className={LABEL}>Fim</label>
          <input
            type="time"
            className={INPUT_CLASS}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </div>
      </div>
      <div>
        <label className={LABEL}>Observações (opcional)</label>
        <input
          className={INPUT_CLASS}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Ex.: levar figurino completo"
        />
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <label className={LABEL}>Local</label>
          <select
            className={INPUT_CLASS}
            value={locationType}
            onChange={(e) => setLocationType(e.target.value as "manto" | "outro")}
          >
            <option value="manto">Manto Produções</option>
            <option value="outro">Outro endereço…</option>
          </select>
        </div>
        {locationType === "outro" && (
          <div>
            <label className={LABEL}>Endereço</label>
            <input
              className={INPUT_CLASS}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Rua…"
            />
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red">{error}</p>}
      <Button type="submit" variant="outline" size="sm" loading={pending}>
        {submitLabel}
      </Button>
    </form>
  );
}

/** Seletor da vaga "Técnico de Som (Presença)" — tarefa da equipe de ensaio. */
function PresencaControl({ data, canEdit }: { data: EventoDetalhe; canEdit: boolean }) {
  const presenca = data.presenca;
  const talents = useTalents();
  const assign = useAssignPresenca(data.event.id);
  if (!presenca) return null;

  if (!canEdit) {
    return (
      <p className="text-sm text-muted">
        Técnico de Som (Presença):{" "}
        <span className={presenca.talent_name ? "font-medium text-ink" : "text-red"}>
          {presenca.talent_name ?? "não definido"}
        </span>
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="text-sm text-muted" htmlFor="presenca-select">
        Técnico de Som (Presença):
      </label>
      <select
        id="presenca-select"
        className={`${INPUT_CLASS} w-auto min-w-48`}
        value={presenca.talent_id ?? ""}
        disabled={assign.isPending || !talents.data}
        onChange={(e) => assign.mutate(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">— sem técnico definido —</option>
        {(talents.data?.items ?? []).map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      {!presenca.talent_id && <span className="text-xs text-red">⚠ pendente</span>}
    </div>
  );
}

/** Painel do ensaio quando o evento aberto É um ensaio: pai/órfão + editar + excluir. */
function EnsaioOwnPanel({ data, canEdit }: { data: EventoDetalhe; canEdit: boolean }) {
  const parent = data.ensaio_pai;
  const edit = useEditEnsaio();
  const remove = useDeleteEnsaio();
  const vincular = useVincularEnsaio(data.event.id);
  const [showEdit, setShowEdit] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [linkQuery, setLinkQuery] = useState("");
  const search = useAgendaSearch(linkQuery);
  const [error, setError] = useState<string | null>(null);

  const startIso = data.event.start_at;
  const initial = {
    date: startIso ? startIso.slice(0, 10) : "",
    start: startIso ? startIso.slice(11, 16) : "",
    end: data.event.end_at ? data.event.end_at.slice(11, 16) : "",
    description: data.event.description ?? "",
    location: data.event.location ?? "",
  };

  return (
    <Panel
      title="Ensaio"
      actions={
        canEdit ? (
          <>
            <Button variant="outline" size="sm" onClick={() => setShowEdit((v) => !v)}>
              {showEdit ? "Fechar edição" : "Editar horário"}
            </Button>
            {confirmingDelete ? (
              <>
                <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(false)}>
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  loading={remove.isPending}
                  onClick={() => remove.mutate(data.event.id)}
                >
                  Confirmar cancelamento
                </Button>
              </>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setConfirmingDelete(true)}>
                Cancelar ensaio
              </Button>
            )}
          </>
        ) : undefined
      }
    >
      {parent ? (
        <p className="text-sm text-muted">
          Ensaio do show{" "}
          <Link to={`/events/${parent.id}`} className="font-medium text-accent hover:underline">
            {parent.title}
          </Link>
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-red">
            ⚠ Ensaio órfão — o show original não existe mais. Vincule a um show ou cancele.
          </p>
          {canEdit && (
            <div className="space-y-2">
              <input
                className={INPUT_CLASS}
                placeholder="Buscar show para vincular…"
                value={linkQuery}
                onChange={(e) => setLinkQuery(e.target.value)}
              />
              {linkQuery.trim().length >= 2 && (
                <ul className="max-h-48 divide-y divide-line overflow-y-auto rounded-md border border-line">
                  {(search.data?.items ?? [])
                    .filter((ev) => ev.event_type !== "ENSAIO" && ev.id !== data.event.id)
                    .slice(0, 8)
                    .map((ev) => (
                      <li key={ev.id} className="flex items-center justify-between gap-2 p-2 text-sm">
                        <span className="min-w-0 truncate text-ink">{ev.title}</span>
                        <Button
                          variant="outline"
                          size="sm"
                          loading={vincular.isPending}
                          onClick={() => vincular.mutate(ev.id)}
                        >
                          Vincular
                        </Button>
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {showEdit && canEdit && (
        <div className="mt-3">
          <EnsaioForm
            initial={initial}
            submitLabel="Salvar alterações"
            pending={edit.isPending}
            error={error}
            onSubmit={(values) => {
              setError(null);
              edit.mutate(
                {
                  ensaioId: data.event.id,
                  date: values.date,
                  start: values.start,
                  end: values.end,
                  description: values.description,
                  location: values.location_type === "outro" ? values.location : "",
                },
                {
                  onSuccess: () => setShowEdit(false),
                  onError: (err) => {
                    if (err instanceof ApiRequestError) setError(err.message);
                  },
                },
              );
            }}
          />
        </div>
      )}
    </Panel>
  );
}

export interface EnsaioSectionProps {
  data: EventoDetalhe;
}

/**
 * Painel de Ensaio (restaurado na 206 — o agendamento vivia só nas páginas Jinja).
 *
 * No SHOW: lista os ensaios agendados, agenda novos e define o Técnico de Som (Presença).
 * No próprio ENSAIO: mostra o show pai (ou o estado órfão com vínculo), edita e cancela.
 * Edição gated por `flags.show_ensaio` (Ensaio/Casting/Superadmin — `_CAN_ENSAIO`).
 */
export function EnsaioSection({ data }: EnsaioSectionProps) {
  const canEdit = Boolean(data.flags.show_ensaio);
  const create = useCreateEnsaio(data.event.id);
  const removeFromShow = useDeleteEnsaioFromShow(data.event.id);
  const [showForm, setShowForm] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (data.event.is_ensaio) {
    return <EnsaioOwnPanel data={data} canEdit={canEdit} />;
  }
  if (data.ensaios === undefined) return null;

  const precisaEnsaio = data.event.needs_rehearsal || data.event.event_type === "SHOW";

  return (
    <Panel
      title="Ensaios"
      actions={
        canEdit ? (
          <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Fechar" : "+ Agendar ensaio"}
          </Button>
        ) : undefined
      }
    >
      <div className="space-y-3">
        {data.ensaios.length === 0 ? (
          precisaEnsaio ? (
            <Empty>Nenhum ensaio agendado ainda.</Empty>
          ) : (
            <p className="text-sm text-muted">Este evento não pede ensaio.</p>
          )
        ) : (
          <ul className="divide-y divide-line">
            {data.ensaios.map((ensaio) => (
              <li key={ensaio.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <span className="font-medium text-ink tabular-nums">
                  {formatEnsaioLabel(ensaio.start_at, ensaio.end_at)}
                </span>
                {ensaio.location && (
                  <span className="min-w-0 truncate text-xs text-muted">{ensaio.location}</span>
                )}
                <span className="ml-auto flex items-center gap-1.5">
                  <Button asChild variant="ghost" size="sm">
                    <Link to={`/events/${ensaio.id}`}>Abrir</Link>
                  </Button>
                  {canEdit &&
                    (confirmingId === ensaio.id ? (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmingId(null)}>
                          Manter
                        </Button>
                        <Button
                          size="sm"
                          loading={removeFromShow.isPending}
                          onClick={() =>
                            removeFromShow.mutate(ensaio.id, {
                              onSettled: () => setConfirmingId(null),
                            })
                          }
                        >
                          Cancelar ensaio
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted hover:text-red"
                        onClick={() => setConfirmingId(ensaio.id)}
                      >
                        ✕
                      </Button>
                    ))}
                </span>
              </li>
            ))}
          </ul>
        )}

        {showForm && canEdit && (
          <EnsaioForm
            submitLabel="Agendar"
            pending={create.isPending}
            error={error}
            onSubmit={(values) => {
              setError(null);
              create.mutate(values, {
                onSuccess: () => setShowForm(false),
                onError: (err) => {
                  if (err instanceof ApiRequestError) setError(err.message);
                },
              });
            }}
          />
        )}

        <PresencaControl data={data} canEdit={canEdit} />
      </div>
    </Panel>
  );
}
