import { type ReactNode } from "react";
import { Button } from "./button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./dialog";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** O que exatamente vai acontecer — cite o item, a quantidade e o valor quando houver. */
  description: ReactNode;
  confirmLabel: string;
  /** Botão em vermelho: ação que apaga ou não tem volta. */
  destructive?: boolean;
  /** Ação em voo — o botão gira e o "Cancelar" trava (Princípio V). */
  pending: boolean;
  /** Erro da API: aparece DENTRO do diálogo, que continua aberto para nova tentativa. */
  error?: string | null;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
}

/**
 * Confirmação de ação destrutiva ou irreversível (Princípio V — nunca `window.confirm()`).
 *
 * Promovido de `GastosRecorrentesPage.tsx` para fonte única na feature 228, mesmo caminho que
 * `CopyButton` fez na 189: o componente já existia pronto e bem-acabado, mas trancado numa
 * página, enquanto o resto do painel caía no `window.confirm` nativo — que não respeita o tema,
 * não mostra valor formatado, não tem estado de carregando e, no celular, aparece como um alerta
 * do sistema colado no topo da tela, fácil de tocar errado.
 */
function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = false,
  pending,
  error,
  onConfirm,
  onOpenChange,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="text-sm text-muted">{description}</div>
        {error && (
          <p className="mt-3 rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancelar
          </Button>
          <Button
            className={destructive ? "bg-red hover:bg-red/90" : undefined}
            loading={pending}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export { ConfirmDialog };
