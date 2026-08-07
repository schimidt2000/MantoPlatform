import { useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { useSolicitarExclusao } from "../../lib/eventOps";

export interface SolicitarExclusaoDialogProps {
  eventId: number;
  eventTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEnviado: () => void;
}

/**
 * Pedido de exclusão do Comercial (feature 224). Excluir e cancelar passaram a ser só do
 * Superadmin — a ação mexe em dinheiro recebido, comissão paga e devolução —, então quem vende
 * pede e explica o motivo.
 */
export function SolicitarExclusaoDialog({
  eventId,
  eventTitle,
  open,
  onOpenChange,
  onEnviado,
}: SolicitarExclusaoDialogProps) {
  const solicitar = useSolicitarExclusao(eventId);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");

  function enviar() {
    setErro("");
    if (!motivo.trim()) {
      setErro("Explique o motivo — é o que o Superadmin vai ler para decidir.");
      return;
    }
    solicitar.mutate(
      { motivo },
      {
        onSuccess: () => {
          setMotivo("");
          onOpenChange(false);
          onEnviado();
        },
        onError: (e) => setErro(e.message),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>Solicitar exclusão</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-ink">“{eventTitle}”</p>
        <p className="mt-1 text-sm text-muted">
          O pedido vai para o Superadmin, que decide entre excluir e cancelar — e trata a
          devolução, se a cliente já tiver pago alguma coisa.
        </p>
        <div className="mt-3">
          <label className="mb-1 block text-xs font-semibold uppercase text-muted" htmlFor="motivo-solicitacao">
            Motivo
          </label>
          <Input
            id="motivo-solicitacao"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Ex.: cliente cancelou, evento duplicado…"
          />
        </div>
        {erro && (
          <p className="mt-2 text-sm text-red" role="alert">
            {erro}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Voltar
          </Button>
          <Button size="sm" loading={solicitar.isPending} onClick={enviar}>
            Enviar solicitação
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
