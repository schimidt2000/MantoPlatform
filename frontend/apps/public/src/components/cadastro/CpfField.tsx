import { Input } from "@manto/ui";
import { useCheckCpf } from "../../lib/cadastro";

interface CpfFieldProps {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  error?: string;
}

/**
 * Campo de CPF com aviso de duplicidade em tempo real (feature 162, US2) — some quando o
 * candidato marca "estrangeiro" (`disabled=true`), paridade com `syncForeigner()` do Jinja.
 */
export function CpfField({ value, onChange, disabled, error }: CpfFieldProps) {
  const check = useCheckCpf(disabled ? "" : value);
  const showDuplicateWarning = !disabled && check.data?.valid && check.data.exists;

  return (
    <div>
      <label className="mb-1 block text-sm text-muted">
        CPF {!disabled && <span className="text-red">*</span>}
      </label>
      <Input
        type="text"
        inputMode="numeric"
        placeholder="000.000.000-00"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
        className={disabled ? "opacity-50" : undefined}
      />
      {error && (
        <p className="mt-1 text-sm text-red" role="alert">
          {error}
        </p>
      )}
      {showDuplicateWarning && (
        <p className="mt-1 text-sm text-red" role="alert">
          ⚠️ Este CPF já está cadastrado. Fale com a equipe da Manto.
        </p>
      )}
    </div>
  );
}
