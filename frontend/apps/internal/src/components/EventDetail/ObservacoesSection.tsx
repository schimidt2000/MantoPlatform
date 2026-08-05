import { useRef, useState } from "react";
import { AccordionRow, Button, CopyButton } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  useAddImageObservation,
  useAddObservation,
  useDeleteObservation,
} from "../../lib/observations";
import { Empty, INPUT_CLASS, Panel } from "./parts";

type Observation = NonNullable<EventoDetalhe["observations"]>[number];

/** Uma observação (texto, link ou imagem), com remoção confirmada. */
function ObservationItem({ obs, eventId }: { obs: Observation; eventId: number }) {
  const del = useDeleteObservation(eventId);
  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0 flex-1">
        {obs.label && <div className="text-xs text-muted">{obs.label}</div>}
        {obs.obs_type === "image" ? (
          obs.image_url ? (
            <img
              src={assetUrl(obs.image_url)}
              alt={obs.label ?? "Observação"}
              className="mt-1 max-w-full rounded-md"
            />
          ) : null
        ) : obs.obs_type === "link" ? (
          <a
            href={obs.content ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="break-words text-sm text-blue underline"
          >
            {obs.content}
          </a>
        ) : (
          <p className="whitespace-pre-wrap break-words text-sm text-ink">{obs.content}</p>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        loading={del.isPending}
        onClick={() => {
          if (window.confirm("Remover esta observação?")) del.mutate(obs.id);
        }}
        aria-label="Remover observação"
      >
        ✕
      </Button>
    </li>
  );
}

/** Formulário de nova observação (texto/link via JSON, imagem via multipart). */
function AddObservationForm({ eventId }: { eventId: number }) {
  const add = useAddObservation(eventId);
  const addImage = useAddImageObservation(eventId);
  const [obsType, setObsType] = useState<"text" | "link" | "image">("text");
  const [content, setContent] = useState("");
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isImage = obsType === "image";
  const pending = isImage ? addImage.isPending : add.isPending;
  const isError = isImage ? addImage.isError : add.isError;
  const canSubmit = isImage ? Boolean(file) : Boolean(content.trim());

  const submit = () => {
    if (isImage) {
      if (!file) return;
      addImage.mutate(
        { file, label: label.trim() || undefined },
        {
          onSuccess: () => {
            setFile(null);
            setLabel("");
            if (inputRef.current) inputRef.current.value = "";
          },
        },
      );
      return;
    }
    if (!content.trim()) return;
    add.mutate(
      { obs_type: obsType, content: content.trim(), label: label.trim() || undefined },
      {
        onSuccess: () => {
          setContent("");
          setLabel("");
        },
      },
    );
  };

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
      <label>
        <span className="sr-only">Tipo de observação</span>
        <select
          className={INPUT_CLASS}
          value={obsType}
          onChange={(e) => setObsType(e.target.value as "text" | "link" | "image")}
        >
          <option value="text">Texto</option>
          <option value="link">Link</option>
          <option value="image">Imagem</option>
        </select>
      </label>
      {isImage ? (
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="text-sm text-ink"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label="Arquivo da imagem"
        />
      ) : (
        <input
          className={`${INPUT_CLASS} min-w-40 flex-1`}
          placeholder={obsType === "link" ? "https://…" : "Escreva a observação"}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          aria-label="Conteúdo da observação"
        />
      )}
      <input
        className={`${INPUT_CLASS} w-32`}
        placeholder="Rótulo (opcional)"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        aria-label="Rótulo"
      />
      <Button size="sm" loading={pending} disabled={!canSubmit} onClick={submit}>
        Adicionar
      </Button>
      {isError && <p className="w-full text-sm text-red">Não foi possível adicionar.</p>}
    </div>
  );
}

const HTML_ENTITIES: Record<string, string> = {
  "&nbsp;": " ",
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
};

/**
 * Converte a descrição do evento (HTML vindo do Google Agenda/Kommo) em texto puro.
 *
 * A descrição chega com `<br>` e âncoras de e-mail; colada crua no WhatsApp ela vira um
 * paragrafão com tags à mostra. Aqui as quebras viram `\n`, as tags saem e as entidades são
 * decodificadas — sem `innerHTML`/`querySelector` (proibidos pela constituição), só regex
 * sobre a string.
 */
export function descriptionToText(html: string): string {
  const semTags = html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|li)>/gi, "\n")
    .replace(/<[^>]+>/g, "");
  const decodificado = semTags.replace(
    /&nbsp;|&amp;|&lt;|&gt;|&quot;|&#39;/g,
    (entidade) => HTML_ENTITIES[entidade] ?? entidade,
  );
  return decodificado
    .split("\n")
    .map((linha) => linha.trim())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Resumo do evento em fonte monoespaçada, pronto para colar no WhatsApp (feature 190).
 * É a descrição que vem do Google Agenda/Kommo, já convertida em texto puro.
 */
export function WhatsAppSummary({ data }: { data: EventoDetalhe }) {
  const description = data.event.description;
  if (!description) return null;
  const texto = descriptionToText(description);
  return (
    <Panel
      title="Resumo para WhatsApp"
      actions={<CopyButton value={texto} label="Copiar resumo do evento" />}
    >
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md bg-surface-2 p-3 font-mono text-xs leading-relaxed text-ink">
        {texto}
      </pre>
    </Panel>
  );
}

export interface ObservacoesSectionProps {
  data: EventoDetalhe;
}

/** Observações do evento (texto, link e imagem). */
export function ObservacoesSection({ data }: ObservacoesSectionProps) {
  const observations = data.observations;
  if (!observations) return null;
  return (
    <Panel title="Observações">
      {observations.length === 0 ? (
        <Empty>Nenhuma observação ainda.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {observations.map((obs) => (
            <ObservationItem key={obs.id} obs={obs} eventId={data.event.id} />
          ))}
        </ul>
      )}
      <AddObservationForm eventId={data.event.id} />
    </Panel>
  );
}

export interface LogsSectionProps {
  data: EventoDetalhe;
}

/**
 * Log de atividades do evento (`EventLog`), em accordion no fim da página.
 *
 * SEGURANÇA: o servidor só serializa `logs` para SUPERADMIN — para os demais papéis a chave
 * nem chega na rede (antes o gate era só aqui no cliente e o payload vazava no devtools).
 * A checagem de presença da chave segue o padrão das seções condicionais (`kpi`, `venda`).
 */
export function LogsSection({ data }: LogsSectionProps) {
  const logs = data.logs;
  if (!logs || logs.length === 0) return null;
  return (
    <Panel title="Log de atividades">
      <AccordionRow
        summary={
          <span className="text-sm text-ink">
            {logs.length} registro(s) — histórico completo do evento
          </span>
        }
      >
        <ul className="space-y-1.5 text-sm">
          {logs.map((log, index) => (
            <li key={index} className="text-muted">
              <span className="tabular-nums">{log.ts}</span> · {log.actor_name}: {log.message}
            </li>
          ))}
        </ul>
      </AccordionRow>
    </Panel>
  );
}
