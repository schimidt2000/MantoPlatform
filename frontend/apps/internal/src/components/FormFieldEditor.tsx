import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, Input, Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import {
  FIELD_TYPES,
  optionsToText,
  useCreateField,
  useDeleteField,
  useFormFieldDefinitions,
  useMoveField,
  useUpdateField,
  type FormFieldDefinition,
} from "../lib/formulariosAdmin";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const CONTROL =
  "flex h-11 w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink " +
  "placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** Estado de um campo em edição/criação — espelha o payload aceito pelo backend. */
interface FieldDraft {
  label: string;
  section_name: string;
  field_type: string;
  help_text: string;
  placeholder: string;
  required: boolean;
  options: string;
}

const EMPTY_DRAFT: FieldDraft = {
  label: "",
  section_name: "",
  field_type: "texto_curto",
  help_text: "",
  placeholder: "",
  required: false,
  options: "",
};

function draftFromField(f: FormFieldDefinition): FieldDraft {
  return {
    label: f.label,
    section_name: f.section_name,
    field_type: f.field_type,
    help_text: f.help_text ?? "",
    placeholder: f.placeholder ?? "",
    required: f.required,
    options: optionsToText(f.options),
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) return error.message;
  return "Não foi possível salvar o campo. Tente novamente.";
}

interface FieldFormProps {
  draft: FieldDraft;
  onChange: (next: FieldDraft) => void;
  /** Em edição o tipo e a seção são imutáveis no backend (`update_field`). */
  lockStructure: boolean;
  sections: string[];
}

function FieldForm({ draft, onChange, lockStructure, sections }: FieldFormProps) {
  const set = <K extends keyof FieldDraft>(key: K, value: FieldDraft[K]) =>
    onChange({ ...draft, [key]: value });

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className={LABEL} htmlFor="campo-label">
          Rótulo *
        </label>
        <Input
          id="campo-label"
          value={draft.label}
          onChange={(e) => set("label", e.target.value)}
          placeholder="Ex.: Nome do aniversariante"
        />
      </div>

      <div>
        <label className={LABEL} htmlFor="campo-secao">
          Seção *
        </label>
        <input
          id="campo-secao"
          className={CONTROL}
          list="secoes-existentes"
          value={draft.section_name}
          disabled={lockStructure}
          onChange={(e) => set("section_name", e.target.value)}
          placeholder="Ex.: Dados do evento"
        />
        <datalist id="secoes-existentes">
          {sections.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
        {lockStructure && <p className="mt-1 text-xs text-muted">A seção não muda depois de criada.</p>}
      </div>

      <div>
        <label className={LABEL} htmlFor="campo-tipo">
          Tipo *
        </label>
        <select
          id="campo-tipo"
          className={CONTROL}
          value={draft.field_type}
          disabled={lockStructure}
          onChange={(e) => set("field_type", e.target.value)}
        >
          {FIELD_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        {lockStructure && (
          <p className="mt-1 text-xs text-muted">
            O tipo não muda depois de criado — respostas já salvas dependem dele.
          </p>
        )}
      </div>

      {draft.field_type === "selecao" && (
        <div className="sm:col-span-2">
          <label className={LABEL} htmlFor="campo-opcoes">
            Opções * — uma por linha
          </label>
          <textarea
            id="campo-opcoes"
            className={`${CONTROL} h-24 resize-y`}
            value={draft.options}
            onChange={(e) => set("options", e.target.value)}
            placeholder={"Sim\nNão\nTalvez"}
          />
        </div>
      )}

      <div>
        <label className={LABEL} htmlFor="campo-ajuda">
          Texto de ajuda
        </label>
        <Input
          id="campo-ajuda"
          value={draft.help_text}
          onChange={(e) => set("help_text", e.target.value)}
          placeholder="Explicação exibida abaixo do campo"
        />
      </div>

      <div>
        <label className={LABEL} htmlFor="campo-placeholder">
          Placeholder
        </label>
        <Input
          id="campo-placeholder"
          value={draft.placeholder}
          onChange={(e) => set("placeholder", e.target.value)}
          placeholder="Texto de exemplo dentro do campo"
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-ink sm:col-span-2">
        <input
          type="checkbox"
          className="h-4 w-4 rounded border-line accent-accent"
          checked={draft.required}
          onChange={(e) => set("required", e.target.checked)}
        />
        Preenchimento obrigatório
      </label>
    </div>
  );
}

interface FieldRowProps {
  field: FormFieldDefinition;
  isFirst: boolean;
  isLast: boolean;
  onEdit: () => void;
  onMove: (direction: "up" | "down") => void;
  onDelete: () => void;
  busy: boolean;
  /** Direção em voo **para este campo** — só a seta clicada mostra spinner (Princípio V). */
  movingDirection: "up" | "down" | null;
}

function FieldRow({
  field,
  isFirst,
  isLast,
  onEdit,
  onMove,
  onDelete,
  busy,
  movingDirection,
}: FieldRowProps) {
  const typeLabel = FIELD_TYPES.find((t) => t.value === field.field_type)?.label ?? field.field_type;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-2 last:border-0">
      <div className="min-w-0">
        <p className="truncate text-sm text-ink">
          {field.label}
          {field.required && <span className="ml-1 text-red">*</span>}
          {field.is_system && (
            <span className="ml-2 rounded bg-surface-2 px-1.5 py-0.5 text-xs text-muted">sistema</span>
          )}
        </p>
        <p className="truncate text-xs text-muted">{typeLabel}</p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          size="sm"
          variant="ghost"
          disabled={isFirst || busy}
          loading={movingDirection === "up"}
          aria-label={`Mover "${field.label}" para cima`}
          onClick={() => onMove("up")}
        >
          {movingDirection === "up" ? "" : "↑"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={isLast || busy}
          loading={movingDirection === "down"}
          aria-label={`Mover "${field.label}" para baixo`}
          onClick={() => onMove("down")}
        >
          {movingDirection === "down" ? "" : "↓"}
        </Button>
        <Button size="sm" variant="ghost" onClick={onEdit}>
          Editar
        </Button>
        {!field.is_system && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={onDelete}>
            Excluir
          </Button>
        )}
      </div>
    </div>
  );
}

export interface FormFieldEditorProps {
  formType: "comum" | "corporativo";
}

/**
 * Editor da estrutura de um formulário (`FormFieldDefinition`) — criar, editar, reordenar e
 * excluir campos. Exclusivo de SUPERADMIN: o backend rejeita (403) qualquer outro papel, e a
 * tela só monta este componente quando `can_edit_structure` vem verdadeiro.
 */
export function FormFieldEditor({ formType }: FormFieldEditorProps) {
  const reduceMotion = useReducedMotion();
  const fields = useFormFieldDefinitions(formType);
  const create = useCreateField(formType);
  const update = useUpdateField(formType);
  const move = useMoveField(formType);
  const del = useDeleteField(formType);

  /** `null` = nenhum formulário aberto; `"new"` = criação; número = edição daquele campo. */
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [draft, setDraft] = useState<FieldDraft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<FormFieldDefinition | null>(null);

  // Trocar de formulário (comum ↔ corporativo) fecha qualquer edição em andamento — o campo
  // aberto pertence ao formulário anterior.
  useEffect(() => {
    setEditing(null);
    setError(null);
    setConfirmDelete(null);
  }, [formType]);

  const list = fields.data?.fields ?? [];
  const sections = Array.from(new Set(list.map((f) => f.section_name)));

  const openCreate = () => {
    setDraft({ ...EMPTY_DRAFT, section_name: sections[0] ?? "" });
    setError(null);
    setEditing("new");
  };

  const openEdit = (field: FormFieldDefinition) => {
    setDraft(draftFromField(field));
    setError(null);
    setEditing(field.id);
  };

  const submit = () => {
    setError(null);
    const onError = (e: unknown) => setError(errorMessage(e));
    if (editing === "new") {
      create.mutate(
        {
          label: draft.label,
          section_name: draft.section_name,
          field_type: draft.field_type,
          help_text: draft.help_text,
          placeholder: draft.placeholder,
          required: draft.required,
          options: draft.options,
        },
        { onSuccess: () => setEditing(null), onError },
      );
    } else if (typeof editing === "number") {
      // Payload completo: `update_field` substitui help_text/placeholder/required — omitir apaga.
      update.mutate(
        {
          id: editing,
          label: draft.label,
          help_text: draft.help_text,
          placeholder: draft.placeholder,
          required: draft.required,
          options: draft.options,
        },
        { onSuccess: () => setEditing(null), onError },
      );
    }
  };

  if (fields.isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (fields.isError) {
    return (
      <div className="rounded-md border border-line bg-surface-2 p-4 text-sm text-muted">
        Não foi possível carregar os campos deste formulário.{" "}
        <button type="button" className="text-accent hover:underline" onClick={() => fields.refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  const busy = move.isPending || del.isPending;
  const grouped = sections.map((section) => ({
    section,
    campos: list.filter((f) => f.section_name === section),
  }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted">
          {list.length} campo{list.length === 1 ? "" : "s"} em {sections.length} seç
          {sections.length === 1 ? "ão" : "ões"}
        </p>
        <Button size="sm" onClick={openCreate} disabled={editing === "new"}>
          + Novo campo
        </Button>
      </div>

      <AnimatePresence initial={false}>
        {editing !== null && (
          <motion.div
            initial={reduceMotion ? undefined : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="rounded-md border border-line bg-surface-2 p-4">
              <p className="mb-3 text-sm font-medium text-ink">
                {editing === "new" ? "Novo campo" : "Editar campo"}
              </p>
              <FieldForm
                draft={draft}
                onChange={setDraft}
                lockStructure={editing !== "new"}
                sections={sections}
              />
              {error && <p className="mt-3 text-sm text-red">{error}</p>}
              <div className="mt-4 flex justify-end gap-2">
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                  Cancelar
                </Button>
                <Button size="sm" loading={create.isPending || update.isPending} onClick={submit}>
                  Salvar
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {list.length === 0 && (
        <p className="text-sm text-muted">
          Este formulário ainda não tem campos. Use “+ Novo campo” para começar.
        </p>
      )}

      {grouped.map(({ section, campos }) => (
        <div key={section}>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{section}</p>
          <div className="rounded-md border border-line px-3">
            {campos.map((f, i) => (
              <FieldRow
                key={f.id}
                field={f}
                isFirst={i === 0}
                isLast={i === campos.length - 1}
                busy={busy}
                movingDirection={
                  move.isPending && move.variables?.id === f.id ? move.variables.direction : null
                }
                onEdit={() => openEdit(f)}
                onMove={(direction) => move.mutate({ id: f.id, direction })}
                onDelete={() => setConfirmDelete(f)}
              />
            ))}
          </div>
        </div>
      ))}

      {confirmDelete && (
        <div className="rounded-md border border-red/40 bg-red-soft p-3">
          <p className="text-sm text-ink">
            Excluir o campo “{confirmDelete.label}”? As respostas já enviadas continuam guardadas,
            mas ele deixa de aparecer no formulário público.
          </p>
          <div className="mt-2 flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(null)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              loading={del.isPending}
              onClick={() =>
                del.mutate(confirmDelete.id, {
                  onSuccess: () => setConfirmDelete(null),
                  onError: (e) => setError(errorMessage(e)),
                })
              }
            >
              Excluir campo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
