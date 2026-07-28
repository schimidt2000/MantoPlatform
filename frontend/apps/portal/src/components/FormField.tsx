import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { Input } from "@manto/ui";

/**
 * Campo de formulário com rótulo, erro e dica — o trio que todas as telas do portal repetem.
 *
 * O `<Input>` do design system já tem 44px de altura (alvo de toque, Princípio VIII) e estilo de
 * inválido via `aria-invalid`; aqui só amarramos rótulo/erro/ajuda por `id` para leitores de
 * tela e evitamos repetir a mesma marcação em oito telas.
 */
export const FormField = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode }
>(function FormField({ label, error, hint, id, ...props }, ref) {
  const fieldId = id ?? props.name;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;

  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="text-sm font-medium text-ink">
        {label}
      </label>
      <Input
        id={fieldId}
        ref={ref}
        aria-invalid={error ? true : undefined}
        aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
        {...props}
      />
      {hint && (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-red" role="alert">
          {error}
        </p>
      )}
    </div>
  );
});

/** Faixa de erro do formulário inteiro (falha da API, não de um campo específico). */
export function FormError({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <div className="rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
      {children}
    </div>
  );
}

/** Faixa de sucesso após uma operação importante (Princípio V). */
export function FormSuccess({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <div className="rounded-md bg-green-soft px-3 py-2 text-sm text-green" role="status">
      {children}
    </div>
  );
}
