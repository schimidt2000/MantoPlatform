import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "../lib/cn";

const buttonVariants = cva(
  // `ring-offset-2`: o token `ring` deixou de ser translúcido (1.64:1, foco invisível) e virou
  // o roxo sólido da marca — o respiro branco impede que o anel encoste na borda do botão.
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-panel disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      variant: {
        default: "bg-accent text-white hover:bg-accent-dark",
        // Contorno em `line-strong`: no botão outline a borda é a única pista de que existe
        // um alvo clicável ali, então vale o mínimo de 3:1 da WCAG 1.4.11.
        outline: "border border-line-strong bg-panel hover:bg-surface-2",
        ghost: "hover:bg-surface-2",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-9 px-3",
        lg: "h-12 px-8 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Renderiza como o filho (padrão Slot do shadcn/ui) em vez de um `<button>`. */
  asChild?: boolean;
  /** Mostra spinner e desabilita o botão — feedback de clique (Princípio V). */
  loading?: boolean;
}

/**
 * Botão base do design system. Nunca fica "morto" ao clique: quando `loading`, exibe
 * spinner e bloqueia novos envios (Princípio V da constituição).
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild = false, loading = false, disabled, children, ...props },
  ref,
) {
  if (asChild) {
    return (
      <Slot className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props}>
        {children}
      </Slot>
    );
  }
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
});

export { Button, buttonVariants };
