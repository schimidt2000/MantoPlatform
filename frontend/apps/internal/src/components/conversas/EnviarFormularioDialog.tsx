import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
} from "@manto/ui";
import { useFormulariosDaConversa } from "../../lib/conversas";

/**
 * "Enviar formulário" (feature 333, FR-010): os formulários públicos com o texto pronto e o link curto. Escolher
 * insere o texto no campo de mensagem, para conferir e enviar pelo "Enviar" de sempre.
 */

interface EnviarFormularioDialogProps {
  conversaId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEscolher: (texto: string) => void;
}

export function EnviarFormularioDialog({ conversaId, open, onOpenChange, onEscolher }: EnviarFormularioDialogProps) {
  const formularios = useFormulariosDaConversa(conversaId, open);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar formulário</DialogTitle>
          <DialogDescription>O texto com o link entra no campo de mensagem, para conferir antes de enviar.</DialogDescription>
        </DialogHeader>
        {formularios.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : formularios.isError ? (
          <div className="space-y-2">
            <p role="alert" className="text-sm text-red">
              Não foi possível carregar os formulários. Tente novamente.
            </p>
            <Button type="button" variant="outline" loading={formularios.isFetching} onClick={() => void formularios.refetch()}>
              Tentar novamente
            </Button>
          </div>
        ) : (
          <ul className="space-y-2">
            {(formularios.data?.formularios ?? []).map((f) => (
              <li key={f.tipo} className="space-y-2 rounded-md border border-line p-3">
                <p className="text-sm font-medium">{f.titulo}</p>
                <p className="whitespace-pre-wrap break-words text-sm text-muted">{f.texto}</p>
                <Button type="button" variant="outline" size="sm" onClick={() => onEscolher(f.texto)}>
                  Inserir na mensagem
                </Button>
              </li>
            ))}
          </ul>
        )}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
