import { useMemo, useState } from "react";
import { useFormContext } from "react-hook-form";
import { Button, Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { MoneyInput } from "@manto/money";
import type { EventFormValues } from "../../lib/eventFormSchema";
import type { CharacterInput } from "../../lib/eventCreate";
import type { AssignableTalent, FigurinoSheetOption } from "../../lib/eventCreate";
import { useCatalogElencoBusca } from "../../lib/catalogoElenco";
import { CharacterAutocomplete, type CharacterSelection } from "../CharacterAutocomplete";
import { FIELD, FIELD_ERROR, LABEL, HELP, FieldError, BlockCard } from "./shared";

/** Opções de talento com avatar circular (feature 195, Princípio X.1/X.2). */
function talentOptions(talents: AssignableTalent[]): ComboboxOption[] {
  return talents.map((t) => ({
    value: String(t.id),
    label: t.name,
    imageUrl: t.photo_face_path ? assetUrl(t.photo_face_path) : null,
    imageShape: "circle" as const,
  }));
}

/** Opções de ficha de figurino com miniatura quadrada (feature 195, Princípio X.2). */
function figurinoOptions(sheets: FigurinoSheetOption[]): ComboboxOption[] {
  return sheets.map((s) => ({
    value: String(s.id),
    label: s.character_name,
    imageUrl: s.photo_url ? assetUrl(s.photo_url) : null,
    imageShape: "square" as const,
    fallbackIcon: "🎭",
  }));
}

interface CharacterRowProps {
  value: CharacterInput;
  onChange: (next: CharacterInput) => void;
  onRemove: () => void;
  figurinoOpts: ComboboxOption[];
  talentOpts: ComboboxOption[];
}

function CharacterRow({ value, onChange, onRemove, figurinoOpts, talentOpts }: CharacterRowProps) {
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
        <Combobox
          className="min-w-56 flex-1"
          aria-label="Buscar figurino"
          placeholder="🔍 Buscar figurino… (auto-detectar pelo nome)"
          emptyMessage="Nenhuma ficha de figurino encontrada."
          options={figurinoOpts}
          value={value.figurino_sheet_id != null ? String(value.figurino_sheet_id) : null}
          onChange={(next) =>
            onChange({ ...value, figurino_sheet_id: next ? Number(next) : null })
          }
        />
        <Combobox
          className="min-w-56 flex-1"
          aria-label="Pré-escalar talento específico"
          placeholder="— pré-escalar talento específico (opcional) —"
          emptyMessage="Nenhum talento encontrado."
          options={talentOpts}
          value={value.talent_id != null ? String(value.talent_id) : null}
          onChange={(next) => onChange({ ...value, talent_id: next ? Number(next) : null })}
        />
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
  figurinoSheets: FigurinoSheetOption[];
  talents: AssignableTalent[];
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
  const catalogElenco = useCatalogElencoBusca();
  const talentOpts = useMemo(() => talentOptions(talents), [talents]);
  const figurinoOpts = useMemo(() => figurinoOptions(figurinoSheets), [figurinoSheets]);

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

  /**
   * Escolher do catálogo (feature 185, US4; busca visual na feature 186, US1): adiciona uma
   * linha de elenco já preenchida com o nome do Personagem e a `figurino_sheet_id` vinculada —
   * é um prefill único, não um vínculo persistente (FR-014: remover manualmente depois não é
   * reaplicado). Só Personagens Filhos aparecem nessa busca (FR-003 da feature 186) — o Tema pai
   * não é uma atração vendável isoladamente no elenco de um evento.
   */
  const addCharacterFromCatalog = (selection: CharacterSelection) => {
    onCharactersChange([
      ...characters,
      {
        role_id: null,
        name: selection.character.name,
        figurino_sheet_id: selection.character.figurino_sheet_id,
        cache_value: null,
        needs_makeup: false,
        is_singer: false,
        talent_id: null,
      },
    ]);
  };

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
            figurinoOpts={figurinoOpts}
            talentOpts={talentOpts}
          />
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" size="sm" onClick={addCharacter}>
          + Adicionar personagem / equipe
        </Button>
        <div className="w-64">
          <CharacterAutocomplete
            temas={catalogElenco.data?.temas ?? []}
            onSelect={addCharacterFromCatalog}
            placeholder="🎭 Escolher personagem do catálogo…"
          />
        </div>
      </div>

      <div className="border-t border-line pt-3">
        <label className={LABEL} htmlFor="coordinator">
          Coordenador específico (opcional)
        </label>
        <Combobox
          id="coordinator"
          aria-label="Coordenador específico"
          placeholder="— sem pré-escala —"
          emptyMessage="Nenhum talento encontrado."
          options={talentOpts}
          value={coordinatorTalentId != null ? String(coordinatorTalentId) : null}
          onChange={(next) => onCoordinatorTalentIdChange(next ? Number(next) : null)}
        />
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
