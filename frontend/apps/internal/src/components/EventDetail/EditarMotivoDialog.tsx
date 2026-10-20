import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useEditarMotivoCancelamento } from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";

interface EditarMotivoDialogProps {
  eventId: number;
  motivo: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Editar motivo" do cancelado (feature 306b): o texto novo vale para o ato inteiro (os dias do
 * grupo cancelados com o mesmo motivo) e troca o antigo no histórico. Só pela flag
 * `can_edit_motivo_cancelado` (Superadmin ou Comercial).
 */
export function EditarMotivoDialog({ eventId, motivo, open, onOpenChange }: EditarMotivoDialogProps) {
  const editar = useEditarMotivoCancelamento(eventId);
  const [texto, setTexto] = useState(motivo);
  const [erroCampo, setErroCampo] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (open) {
      setTexto(motivo);
    } else {
      setErroCampo("");
      setErro("");
    }
  }, [open, motivo]);

  function salvar() {
    setErroCampo("");
    setErro("");
    if (!texto.trim()) {
      setErroCampo("Explique o motivo do cancelamento.");
      return;
    }
    editar.mutate(
      { motivo: texto.trim() },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => {
          if (e instanceof ApiRequestError && (e.status === 404 || e.status === 405)) {
            setErro("O sistema está atualizando — tente em um minuto.");
            return;
          }
          if (e instanceof ApiRequestError && e.fields?.motivo) {
            setErroCampo(e.fields.motivo);
            return;
          }
          setErro(e.message);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Editar motivo do cancelamento</DialogTitle>
          <DialogDescription>
            O motivo aparece para quem abre o evento. O texto novo substitui o antigo também no histórico e nos
            outros dias do grupo cancelados junto. O dinheiro e os avisos não mudam.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className={LABEL} htmlFor="editar-motivo-cancelamento">
              Motivo do cancelamento
            </label>
            <Input
              id="editar-motivo-cancelamento"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              aria-invalid={Boolean(erroCampo)}
            />
            {erroCampo && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erroCampo}
              </p>
            )}
          </div>
          {erro && (
            <p className="text-sm text-red" role="alert">
              {erro}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={editar.isPending}>
            Voltar
          </Button>
          <Button size="sm" onClick={salvar} loading={editar.isPending}>
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
