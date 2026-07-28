import { useRef, useState } from "react";
import { Badge, Button } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  useAddMaterialFile,
  useAddMaterialLink,
  useDeleteMaterial,
  useTravelEstimate,
} from "../../lib/eventDetail";
import { useSaveLogistics } from "../../lib/eventOps";
import { Empty, INPUT_CLASS, Panel } from "./parts";

/** Rótulo legível do local de maquiagem (os dois presets + endereço livre). */
function makeupLocationLabel(loc: string | null): string {
  if (!loc) return "—";
  if (loc === "manto") return "Manto Produções";
  if (loc === "local") return "Local do evento";
  return loc;
}

/** Card do trajeto: tempo/distância em cache do Google Maps + saída sugerida. */
function TrajetoCard({ data }: { data: EventoDetalhe }) {
  const estimate = useTravelEstimate(data.event.id);
  const travel = data.event.travel;
  const canEdit = Boolean(data.flags.can_edit_event);

  return (
    <div className="rounded-md border border-line bg-surface-2/60 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm text-ink">
          {travel.time_minutes != null ? (
            <>
              <span className="font-medium">
                Google Maps: {Math.floor(travel.time_minutes / 60)}h
                {String(travel.time_minutes % 60).padStart(2, "0")} de viagem
              </span>
              {travel.distance_km != null && (
                <span className="ml-2 text-muted tabular-nums">
                  ({travel.distance_km.toFixed(1)} km)
                </span>
              )}
            </>
          ) : (
            <span className="text-muted">Trajeto ainda não estimado.</span>
          )}
          {travel.suggested_departure && (
            <div className="text-xs text-muted">
              Para chegar 1h antes: sair às {travel.suggested_departure}
            </div>
          )}
        </div>
        {travel.is_outside_sp && <Badge tone="gold">Viagem fora de SP</Badge>}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {canEdit && (
          <Button
            variant="outline"
            size="sm"
            loading={estimate.isPending}
            onClick={() => estimate.mutate()}
          >
            Estimar via Google Maps
          </Button>
        )}
        {travel.maps_url && (
          <Button asChild variant="ghost" size="sm">
            <a href={travel.maps_url} target="_blank" rel="noopener noreferrer">
              Abrir no Maps ↗
            </a>
          </Button>
        )}
      </div>
      {estimate.isError && <p className="mt-1 text-sm text-red">{estimate.error?.message}</p>}
    </div>
  );
}

/** Formulário de logística (maquiagem, saída, "precisa ensaio"). */
function LogisticaForm({ data }: { data: EventoDetalhe }) {
  const save = useSaveLogistics(data.event.id);
  const event = data.event;
  const initLoc = event.makeup_location;
  const isPreset = initLoc === "manto" || initLoc === "local";
  const [makeupTime, setMakeupTime] = useState(event.makeup_time ?? "");
  const [makeupSel, setMakeupSel] = useState(isPreset ? initLoc! : initLoc ? "outro" : "manto");
  const [makeupCustom, setMakeupCustom] = useState(!isPreset && initLoc ? initLoc : "");
  const [departureTime, setDepartureTime] = useState(event.departure_time ?? "");
  const [departureLocation, setDepartureLocation] = useState(
    event.departure_location ?? "Manto Produções",
  );
  const [needsRehearsal, setNeedsRehearsal] = useState(event.needs_rehearsal);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Horário de maquiagem</span>
          <input
            type="time"
            className={INPUT_CLASS}
            value={makeupTime}
            onChange={(e) => setMakeupTime(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Local de maquiagem</span>
          <select
            className={INPUT_CLASS}
            value={makeupSel}
            onChange={(e) => setMakeupSel(e.target.value)}
          >
            <option value="manto">Manto Produções</option>
            <option value="local">Local do evento</option>
            <option value="outro">Outro endereço…</option>
          </select>
        </label>
      </div>
      {makeupSel === "outro" && (
        <input
          type="text"
          className={INPUT_CLASS}
          placeholder="Endereço da maquiagem"
          value={makeupCustom}
          onChange={(e) => setMakeupCustom(e.target.value)}
          aria-label="Endereço da maquiagem"
        />
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Horário de saída</span>
          <input
            type="time"
            className={INPUT_CLASS}
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Local de saída</span>
          <input
            type="text"
            className={INPUT_CLASS}
            value={departureLocation}
            onChange={(e) => setDepartureLocation(e.target.value)}
          />
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={needsRehearsal}
          onChange={(e) => setNeedsRehearsal(e.target.checked)}
        />
        Precisa de ensaio
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          size="sm"
          loading={save.isPending}
          onClick={() =>
            save.mutate({
              makeup_time: makeupTime,
              makeup_location: makeupSel === "outro" ? makeupCustom.trim() : makeupSel,
              departure_time: departureTime,
              departure_location: departureLocation,
              needs_rehearsal: needsRehearsal,
            })
          }
        >
          Salvar logística
        </Button>
        {save.isSuccess && !save.isPending && (
          <span className="text-sm text-green">Logística salva.</span>
        )}
        {save.isError && <span className="text-sm text-red">Não foi possível salvar.</span>}
      </div>
    </div>
  );
}

/** Leitura da logística para quem não pode editar o evento. */
function LogisticaLeitura({ data }: { data: EventoDetalhe }) {
  const event = data.event;
  const maquiagem = [event.makeup_time, makeupLocationLabel(event.makeup_location)]
    .filter(Boolean)
    .join(" · ");
  const saida = [event.departure_time, event.departure_location].filter(Boolean).join(" · ");
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      <dt className="text-muted">Maquiagem</dt>
      <dd className="text-ink">{maquiagem || "—"}</dd>
      <dt className="text-muted">Saída</dt>
      <dd className="text-ink">{saida || "—"}</dd>
      <dt className="text-muted">Precisa ensaio</dt>
      <dd className="text-ink">{event.needs_rehearsal ? "Sim" : "Não"}</dd>
    </dl>
  );
}

/** Materiais de ensaio: upload de arquivo e link externo (Drive, YouTube…). */
function MateriaisSection({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const addFile = useAddMaterialFile(eventId);
  const addLink = useAddMaterialLink(eventId);
  const remove = useDeleteMaterial(eventId);
  const [file, setFile] = useState<File | null>(null);
  const [fileLabel, setFileLabel] = useState("");
  const [url, setUrl] = useState("");
  const [urlLabel, setUrlLabel] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const canEdit = Boolean(data.flags.show_ensaio);
  const materiais = data.materiais ?? [];

  return (
    <Panel title="Materiais de ensaio">
      {materiais.length === 0 ? (
        <Empty>Nenhum material adicionado ainda.</Empty>
      ) : (
        <ul className="mb-3 divide-y divide-line">
          {materiais.map((material) => (
            <li key={material.id} className="flex items-center justify-between gap-2 py-1.5">
              <a
                href={assetUrl(material.url ?? material.file_path)}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate text-sm text-blue underline"
              >
                {material.material_type === "link" ? "🔗" : "📄"} {material.label || material.url}
              </a>
              {canEdit && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={remove.isPending}
                  onClick={() => {
                    if (window.confirm("Remover este material?")) remove.mutate(material.id);
                  }}
                  aria-label={`Remover ${material.label ?? "material"}`}
                >
                  ✕
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canEdit && (
        <div className="grid gap-4 border-t border-line pt-3 sm:grid-cols-2">
          <div>
            <div className="mb-1 text-sm font-medium text-ink">📎 Enviar arquivo</div>
            <p className="mb-1 text-xs text-muted">TXT / PDF / DOC / DOCX, máx. 20 MB</p>
            <input
              ref={fileRef}
              type="file"
              className="text-sm text-ink"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              aria-label="Arquivo do material"
            />
            <input
              className={`${INPUT_CLASS} mt-2`}
              placeholder="Descrição (opcional)"
              value={fileLabel}
              onChange={(e) => setFileLabel(e.target.value)}
              aria-label="Descrição do arquivo"
            />
            <Button
              size="sm"
              className="mt-2"
              loading={addFile.isPending}
              disabled={!file}
              onClick={() =>
                file &&
                addFile.mutate(
                  { file, label: fileLabel.trim() || undefined },
                  {
                    onSuccess: () => {
                      setFile(null);
                      setFileLabel("");
                      if (fileRef.current) fileRef.current.value = "";
                    },
                  },
                )
              }
            >
              Enviar arquivo
            </Button>
            {addFile.isError && <p className="mt-1 text-sm text-red">{addFile.error?.message}</p>}
          </div>

          <div>
            <div className="mb-1 text-sm font-medium text-ink">🔗 Adicionar link</div>
            <p className="mb-1 text-xs text-muted">URL (Google Drive, YouTube, etc.)</p>
            <input
              className={INPUT_CLASS}
              placeholder="https://drive.google.com/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              aria-label="URL do material"
            />
            <input
              className={`${INPUT_CLASS} mt-2`}
              placeholder="Descrição (opcional)"
              value={urlLabel}
              onChange={(e) => setUrlLabel(e.target.value)}
              aria-label="Descrição do link"
            />
            <Button
              size="sm"
              className="mt-2"
              loading={addLink.isPending}
              disabled={!url.trim()}
              onClick={() =>
                addLink.mutate(
                  { url: url.trim(), label: urlLabel.trim() || undefined },
                  {
                    onSuccess: () => {
                      setUrl("");
                      setUrlLabel("");
                    },
                  },
                )
              }
            >
              Adicionar link
            </Button>
            {addLink.isError && <p className="mt-1 text-sm text-red">{addLink.error?.message}</p>}
          </div>
        </div>
      )}
    </Panel>
  );
}

export interface LogisticaSectionProps {
  data: EventoDetalhe;
}

/** Logística & trajeto + materiais de ensaio (coluna esquerda, feature 190). */
export function LogisticaSection({ data }: LogisticaSectionProps) {
  const canEdit = Boolean(data.flags.can_edit_event);
  return (
    <>
      <Panel title="Logística & trajeto">
        <div className="grid gap-3 lg:grid-cols-2">
          <div>{canEdit ? <LogisticaForm data={data} /> : <LogisticaLeitura data={data} />}</div>
          <TrajetoCard data={data} />
        </div>
      </Panel>
      <MateriaisSection data={data} />
    </>
  );
}
