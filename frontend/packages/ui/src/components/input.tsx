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
        "flex h-11 w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink",
        "placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:cursor-not-allowed disabled:opacity-60",
        "aria-[invalid=true]:border-red aria-[invalid=true]:ring-red/30",
        className,
      )}
      {...props}
    />
  );
});

export { Input };
