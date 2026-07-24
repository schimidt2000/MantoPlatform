import { useState } from "react";
import { useFormContext } from "react-hook-form";
import { Button } from "@manto/ui";
import { MoneyInput } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import type { CharacterInput } from "../../lib/eventCreate";
import { FIELD, FIELD_ERROR, LABEL, HELP, FieldError, BlockCard } from "./shared";

interface CharacterRowProps {
  value: CharacterInput;
  onChange: (next: CharacterInput) => void;
  onRemove: () => void;
  figurinoSheets: { id: number; character_name: string }[];
  talents: { id: number; name: string }[];
}

function CharacterRow({ value, onChange, onRemove, figurinoSheets, talents }: CharacterRowProps) {
  return (
    <li className="space-y-2 border-b border-line pb-3 last:border-none">
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Personagem / função"
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
          aria-label="Nome do personagem"
        />
        <Button type="button" variant="ghost" size="sm" onClick={onRemove} aria-label="Remover">
          ✕
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.figurino_sheet_id ?? ""}
          onChange={(e) =>
            onChange({
              ...value,
              figurino_sheet_id: e.target.value ? Number(e.target.value) : null,
            })
          }
          aria-label="Buscar figurino"
        >
          <option value="">🔍 Buscar figurino… (auto-detectar pelo nome)</option>
          {figurinoSheets.map((s) => (
            <option key={s.id} value={s.id}>
              {s.character_name}
            </option>
          ))}
        </select>
        <select
          className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.talent_id ?? ""}
          onChange={(e) =>
            onChange({ ...value, talent_id: e.target.value ? Number(e.target.value) : null })
          }
          aria-label="Pré-escalar talento específico"
        >
          <option value="">— pré-escalar talento específico (opcional) —</option>
          {talents.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <MoneyInput
          className="h-10 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.cache_value ?? 0}
          onValueChange={(v) => onChange({ ...value, cache_value: v })}
          aria-label="Cachê"
        />
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={value.needs_makeup}
            onChange={(e) => onChange({ ...value, needs_makeup: e.target.checked })}
          />
          Maquiagem
        </label>
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={value.is_singer}
            onChange={(e) => onChange({ ...value, is_singer: e.target.checked })}
          />
          Cantor(a)
        </label>
      </div>
    </li>
  );
}

export interface ElencoBlockProps {
  characters: CharacterInput[];
  onCharactersChange: (next: CharacterInput[]) => void;
  coordinatorTalentId: number | null;
  onCoordinatorTalentIdChange: (id: number | null) => void;
  figurinoSheets: { id: number; character_name: string }[];
  talents: { id: number; name: string }[];
}

/** Bloco 3 — Personagens e equipe (elenco dinâmico) + título do evento (feature 184). */
export function ElencoBlock({
  characters,
  onCharactersChange,
  coordinatorTalentId,
  onCoordinatorTalentIdChange,
  figurinoSheets,
  talents,
}: ElencoBlockProps) {
  const {
    register,
    watch,
    setValue,
    formState: { errors },
  } = useFormContext<EventFormValues>();
  const [titleEdited, setTitleEdited] = useState(false);
  const eventType = watch("event_type");

  const addCharacter = () =>
    onCharactersChange([
      ...characters,
      {
        role_id: null,
        name: "",
        figurino_sheet_id: null,
        cache_value: null,
        needs_makeup: false,
        is_singer: false,
        talent_id: null,
      },
    ]);

  const generateTitle = () => {
    const names = characters
      .map((c) => c.name.trim())
      .filter(Boolean)
      .map((n) => n.toUpperCase());
    const prefix = eventType ? `(${eventType}) ` : "";
    setValue("title", `${prefix}${names.join(" + ")}`, { shouldValidate: true });
    setTitleEdited(false);
  };

  return (
    <BlockCard title="Personagens e equipe" id="bloco-elenco">
      <ul className="space-y-3">
        {characters.map((c, i) => (
          <CharacterRow
            key={i}
            value={c}
            onChange={(next) => onCharactersChange(characters.map((p, j) => (j === i ? next : p)))}
            onRemove={() => onCharactersChange(characters.filter((_, j) => j !== i))}
            figurinoSheets={figurinoSheets}
            talents={talents}
          />
        ))}
      </ul>
      <Button type="button" variant="outline" size="sm" onClick={addCharacter}>
        + Adicionar personagem / equipe
      </Button>

      <div className="border-t border-line pt-3">
        <label className={LABEL} htmlFor="coordinator">
          Coordenador específico (opcional)
        </label>
        <select
          id="coordinator"
          className={FIELD}
          value={coordinatorTalentId ?? ""}
          onChange={(e) => onCoordinatorTalentIdChange(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— sem pré-escala —</option>
          {talents.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <p className={HELP}>
          Pré-escalar um coordenador do banco. Se vazio, a vaga fica aberta para o casting
          designar.
        </p>
      </div>

      <div className="border-t border-line pt-3">
        <label className={LABEL} htmlFor="title">
          Título do evento *
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            id="title"
            className={errors.title ? FIELD_ERROR : FIELD}
            {...register("title", { onChange: () => setTitleEdited(true) })}
          />
          <Button type="button" variant="outline" size="sm" onClick={generateTitle}>
            Gerar título automaticamente
          </Button>
        </div>
        <FieldError message={errors.title?.message} />
        {!titleEdited && (
          <p className={HELP}>Padrão: (TIPO) PERSONAGEM 1 + PERSONAGEM 2</p>
        )}
      </div>
    </BlockCard>
  );
}
