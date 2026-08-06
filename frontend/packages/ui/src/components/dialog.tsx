import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "../lib/cn";

/**
 * Dialog do design system Manto (feature 187) — sobre `@radix-ui/react-dialog` (foco preso,
 * `Escape`/clique-fora fecham, portal, ARIA corretos "de fábrica"), com Tailwind + Framer
 * Motion por cima para a animação de entrada/saída (Princípio IX). Mesma abordagem já aceita
 * no projeto para `Button`/`Card` via `@radix-ui/react-slot` — primitivos headless pequenos,
 * não o pacote/CLI completo do shadcn/ui.
 *
 * Usado para confirmações de ações financeiras/irreversíveis (Princípio V — ações destrutivas
 * exigem confirmação via modal/dialog, nunca `window.confirm()`).
 */
const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

interface DialogContentProps extends HTMLAttributes<HTMLDivElement> {
  /** Controla a montagem/desmontagem animada — passar o mesmo `open` do `Dialog`. */
  open: boolean;
  children: ReactNode;
}

const DialogContent = forwardRef<HTMLDivElement, DialogContentProps>(function DialogContent(
  { className, open, children, ...props },
  ref,
) {
  const reduceMotion = useReducedMotion();
  return (
    <AnimatePresence>
      {open && (
        <DialogPrimitive.Portal forceMount>
          <DialogPrimitive.Overlay asChild forceMount>
            {/* `bg-black/50` é intencional nos dois temas e NÃO deve virar token: o véu não é
                uma superfície, é sombra — a função dele é escurecer o que está atrás. Um véu
                que clareasse no tema escuro empurraria a página PARA CIMA do modal. */}
            <motion.div
              className="fixed inset-0 z-40 bg-black/50"
              initial={reduceMotion ? undefined : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={reduceMotion ? undefined : { opacity: 0 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            />
          </DialogPrimitive.Overlay>
          {/*
            Centralização por FLEX, nunca por `translate` do Tailwind.

            O painel é um `motion.div` e o Framer Motion escreve `transform` no estilo inline ao
            animar `scale`/`y` — isso sobrescrevia as classes `-translate-x-1/2 -translate-y-1/2`
            que faziam a centralização. O resultado: o canto superior esquerdo do diálogo parava
            exatamente no meio da tela e metade dele ficava para fora, sem como rolar até o resto
            (era o bug relatado em 11 telas).

            O container também é quem rola (`overflow-y-auto` + `min-h-full`): diálogo curto fica
            centralizado; diálogo alto (formulários longos) empurra a rolagem em vez de vazar pelo
            rodapé. Clique aqui fora do painel continua fechando — quem cuida disso é o Radix, pelo
            `onPointerDownOutside` do `Content`, não o overlay.
          */}
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4">
              <DialogPrimitive.Content asChild forceMount {...props}>
                <motion.div
                  ref={ref}
                  className={cn(
                    "relative w-full max-w-md rounded-lg border border-line bg-panel p-5 shadow-lg focus:outline-none",
                    className,
                  )}
                  initial={reduceMotion ? undefined : { opacity: 0, scale: 0.96, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, scale: 0.96, y: 8 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  {children}
                  <DialogPrimitive.Close
                    className="absolute right-4 top-4 rounded-md p-1 text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label="Fechar"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </DialogPrimitive.Close>
                </motion.div>
              </DialogPrimitive.Content>
            </div>
          </div>
        </DialogPrimitive.Portal>
      )}
    </AnimatePresence>
  );
});

const DialogHeader = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("mb-4 flex flex-col gap-1 pr-6", className)} {...props} />
);

const DialogTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  function DialogTitle({ className, ...props }, ref) {
    return (
      <DialogPrimitive.Title asChild>
        <h2 ref={ref} className={cn("text-lg font-semibold text-ink", className)} {...props} />
      </DialogPrimitive.Title>
    );
  },
);

const DialogDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  function DialogDescription({ className, ...props }, ref) {
    return (
      <DialogPrimitive.Description asChild>
        <p ref={ref} className={cn("text-sm text-muted", className)} {...props} />
      </DialogPrimitive.Description>
    );
  },
);

const DialogFooter = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("mt-5 flex justify-end gap-2", className)} {...props} />
);

export {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
};
