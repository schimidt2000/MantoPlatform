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
            <motion.div
              className="fixed inset-0 z-40 bg-black/50"
              initial={reduceMotion ? undefined : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={reduceMotion ? undefined : { opacity: 0 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            />
          </DialogPrimitive.Overlay>
          <DialogPrimitive.Content asChild forceMount {...props}>
            <motion.div
              ref={ref}
              className={cn(
                "fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-line bg-panel p-5 shadow-lg focus:outline-none",
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
