import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

/** Campo de texto base do design system. */
const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        // `line-strong` e não `line`: a borda é a ÚNICA pista de que existe um campo ali, e
        // o cinza decorativo dava 1.27:1 (a WCAG 1.4.11 exige 3:1 para contorno de controle).
        // O `ring-offset` compensa o anel de foco agora sólido, mantendo o desenho leve.
        "flex h-11 w-full rounded-md border border-line-strong bg-panel px-3 py-2 text-sm text-ink",
        "placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "focus-visible:ring-offset-2 focus-visible:ring-offset-panel",
        "disabled:cursor-not-allowed disabled:opacity-60",
        "aria-[invalid=true]:border-red aria-[invalid=true]:ring-red/30",
        className,
      )}
      {...props}
    />
  );
});

export { Input };
