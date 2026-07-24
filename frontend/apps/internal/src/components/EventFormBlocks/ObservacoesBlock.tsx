import { useRef, useState, type ReactNode } from "react";
import { Button } from "@manto/ui";
import type { ObservationInput } from "../../lib/eventCreate";
import { BlockCard, HELP } from "./shared";

export interface ObservacoesBlockProps {
  observations: ObservationInput[];
  onObservationsChange: (next: ObservationInput[]) => void;
  /** Observações já salvas (feature 184, edição) — exibidas para contexto; excluir uma
   * observação já salva continua na tela de detalhe do evento. */
  existingNote?: ReactNode;
}

/** Bloco 7 — Observações (feature 184): texto, foto e link, com rótulo opcional. */
export function ObservacoesBlock({
  observations,
  onObservationsChange,
  existingNote,
}: ObservacoesBlockProps) {
  const [draftLabel, setDraftLabel] = useState("");
  const [draftText, setDraftText] = useState("");
  const [draftLink, setDraftLink] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addObservation = (obs: ObservationInput) => {
    onObservationsChange([...observations, obs]);
    setDraftLabel("");
    setDraftText("");
    setDraftLink("");
  };

  const removeObservation = (index: number) =>
    onObservationsChange(observations.filter((_, i) => i !== index));

  return (
    <BlockCard title="Observações" id="bloco-observacoes">
      <p className={HELP}>
        Registre informações da cliente: fotos do local, referências, pedidos especiais, links.
      </p>
      {existingNote}

      {observations.length > 0 && (
        <ul className="divide-y divide-line">
          {observations.map((o, i) => (
            <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span className="text-ink">
                {o.label && <span className="mr-2 text-xs text-muted">{o.label}</span>}
                {o.obs_type === "image" ? `📷 ${o.file?.name ?? "foto"}` : o.content}
              </span>
              <Button type="button" variant="ghost" size="sm" onClick={() => removeObservation(i)}>
                ✕
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-2 rounded-md border border-line bg-surface-2 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="h-10 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            placeholder="Escreva a observação"
            value={draftText}
            onChange={(e) => setDraftText(e.target.value)}
            aria-label="Observação de texto"
          />
          <input
            className="h-10 w-40 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            placeholder="Rótulo (opcional)"
            value={draftLabel}
            onChange={(e) => setDraftLabel(e.target.value)}
            aria-label="Rótulo da observação"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!draftText.trim()}
            onClick={() => addObservation({ obs_type: "text", content: draftText.trim(), label: draftLabel.trim() })}
          >
            + Texto
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="h-10 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            placeholder="https://…"
            type="url"
            value={draftLink}
            onChange={(e) => setDraftLink(e.target.value)}
            aria-label="Link"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!draftLink.trim()}
            onClick={() => addObservation({ obs_type: "link", content: draftLink.trim(), label: draftLabel.trim() })}
          >
            + Link
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              if (file) {
                addObservation({ obs_type: "image", content: "", label: draftLabel.trim(), file });
              }
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
          />
          <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
            + Foto
          </Button>
        </div>
      </div>
    </BlockCard>
  );
}
