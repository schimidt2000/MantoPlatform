import {
  DDI_OPTIONS,
  maskCep,
  maskCnpj,
  maskCpf,
  maskPhone,
  onlyDigits,
  type FieldSchema,
} from "../../lib/formularios";

export const FIELD = "h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink";
export const LABEL = "mb-1 block text-sm text-muted";

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-sm text-red" role="alert">
      {message}
    </p>
  );
}

interface DynamicFieldProps {
  field: FieldSchema;
  values: Record<string, string>;
  errors: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onBlurCep?: (value: string) => void;
}

/** Despacha o widget certo por `field.type` — paridade com a macro Jinja `field()`. */
export function DynamicField({ field, values, errors, onChange, onBlurCep }: DynamicFieldProps) {
  const label = (
    <label className={LABEL} htmlFor={field.key}>
      {field.required && <span className="text-red">* </span>}
      {field.label}
    </label>
  );

  if (field.type === "telefone") {
    const ddiKey = `${field.key}_ddi`;
    const nationalKey = `${field.key}_national`;
    return (
      <div>
        {label}
        <div className="flex gap-2">
          <select
            className={`${FIELD} w-auto`}
            value={values[ddiKey] ?? "+55"}
            onChange={(e) => onChange(ddiKey, e.target.value)}
            aria-label="Código do país"
          >
            {DDI_OPTIONS.map((opt) => (
              <option key={opt.code} value={opt.code}>
                {opt.flag} {opt.code}
              </option>
            ))}
          </select>
          <input
            id={field.key}
            className={FIELD}
            inputMode="tel"
            placeholder="(11) 99999-9999"
            value={values[nationalKey] ?? ""}
            onChange={(e) => onChange(nationalKey, maskPhone(onlyDigits(e.target.value)))}
          />
        </div>
        {field.help_text && <p className="mt-1 text-xs text-muted">{field.help_text}</p>}
        <FieldError message={errors[nationalKey]} />
      </div>
    );
  }

  if (field.type === "texto_longo") {
    return (
      <div>
        {label}
        <textarea
          id={field.key}
          className={`${FIELD} h-auto py-2`}
          rows={4}
          value={values[field.key] ?? ""}
          onChange={(e) => onChange(field.key, e.target.value)}
        />
        {field.help_text && <p className="mt-1 text-xs text-muted">{field.help_text}</p>}
        <FieldError message={errors[field.key]} />
      </div>
    );
  }

  if (field.type === "selecao") {
    return (
      <div>
        {label}
        <select
          id={field.key}
          className={FIELD}
          value={values[field.key] ?? ""}
          onChange={(e) => onChange(field.key, e.target.value)}
        >
          <option value="">Selecione…</option>
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <FieldError message={errors[field.key]} />
      </div>
    );
  }

  if (field.type === "sim_nao") {
    return (
      <div>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="h-[18px] w-[18px] accent-accent"
            checked={values[field.key] === "Sim"}
            onChange={(e) => onChange(field.key, e.target.checked ? "Sim" : "")}
          />
          {field.required && <span className="text-red">*</span>} {field.label}
        </label>
        <FieldError message={errors[field.key]} />
      </div>
    );
  }

  if (field.type === "data" || field.type === "hora") {
    return (
      <div>
        {label}
        <input
          id={field.key}
          type={field.type === "data" ? "date" : "time"}
          className={FIELD}
          value={values[field.key] ?? ""}
          onChange={(e) => onChange(field.key, e.target.value)}
        />
        <FieldError message={errors[field.key]} />
      </div>
    );
  }

  const maskByType: Partial<Record<FieldSchema["type"], (digits: string) => string>> = {
    cpf: maskCpf,
    cnpj: maskCnpj,
    cep: maskCep,
  };
  const mask = maskByType[field.type];

  return (
    <div>
      {label}
      <input
        id={field.key}
        type={field.type === "email" ? "email" : "text"}
        inputMode={mask ? "numeric" : undefined}
        className={FIELD}
        placeholder={field.placeholder ?? undefined}
        value={values[field.key] ?? ""}
        onChange={(e) => onChange(field.key, mask ? mask(onlyDigits(e.target.value)) : e.target.value)}
        onBlur={field.type === "cep" ? () => onBlurCep?.(values[field.key] ?? "") : undefined}
      />
      {field.help_text && <p className="mt-1 text-xs text-muted">{field.help_text}</p>}
      <FieldError message={errors[field.key]} />
    </div>
  );
}
