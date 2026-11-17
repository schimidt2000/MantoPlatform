import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
} from "@manto/ui";
import { mensagemDoErro, useDefinirResponsavel, useEquipe } from "../../lib/conversas";

/**
 * "Transferir…" (feature 328, FR-004/FR-018): escolher a pessoa da equipe que passa a atender.
 * `Combobox` porque a equipe pode passar de 10 pessoas (Princípio XII). Quem recebe é avisada no
 * sino pelo servidor. O erro do campo (`fields.responsavel_id`) realça o seletor.
 */

interface TransferirDialogProps {
  conversaId: number;
  nomeDoContato: string;
  responsavelAtual: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TransferirDialog({
  conversaId,
  nomeDoContato,
  responsavelAtual,
  open,
  onOpenChange,
}: TransferirDialogProps) {
  const equipe = useEquipe(open);
  const definir = useDefinirResponsavel(conversaId);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [invalido, setInvalido] = useState(false);

  useEffect(() => {
    if (!open) {
      setEscolhido(null);
      setErro(null);
      setInvalido(false);
    }
  }, [open]);

  const opcoes = (equipe.data?.equipe ?? [])
    .filter((p) => p.id !== responsavelAtual)
    .map((p) => ({ value: String(p.id), label: p.nome }));

  const transferir = () => {
    if (!escolhido) {
      setInvalido(true);
      setErro("Selecione uma pessoa da equipe.");
      document.getElementById(`transferir-${conversaId}`)?.focus();
      return;
    }
    setErro(null);
    definir.mutate(
      { acao: "transferir", responsavel_id: Number(escolhido) },
      {
        onSuccess: () => onOpenChange(false),
        onError: (falha) => {
          if (falha instanceof ApiRequestError && falha.fields?.responsavel_id) {
            setInvalido(true);
            document.getElementById(`transferir-${conversaId}`)?.focus();
          }
          setErro(mensagemDoErro(falha, "Não foi possível transferir. Tente novamente."));
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Transferir conversa</DialogTitle>
          <DialogDescription>
            A conversa com {nomeDoContato} passa a ser de quem você escolher, e essa pessoa é avisada no sino.
          </DialogDescription>
        </DialogHeader>
        {equipe.isLoading ? (
          <Skeleton className="h-11 w-full" />
        ) : equipe.isError ? (
          <div className="space-y-2">
            <p role="alert" className="text-sm text-red">
              Não foi possível carregar a equipe. Tente novamente.
            </p>
            <Button type="button" variant="outline" loading={equipe.isFetching} onClick={() => void equipe.refetch()}>
              Tentar novamente
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5">
            <label htmlFor={`transferir-${conversaId}`} className="text-sm font-medium">
              Pessoa da equipe
            </label>
            <Combobox
              id={`transferir-${conversaId}`}
              options={opcoes}
              value={escolhido}
              onChange={(valor) => {
                setEscolhido(valor);
                setInvalido(false);
                setErro(null);
              }}
              invalid={invalido}
              placeholder="Selecione a pessoa"
              emptyMessage="Nenhuma outra pessoa encontrada na equipe."
            />
          </div>
        )}
        {erro ? (
          <p role="alert" className="text-sm text-red">
            {erro}
          </p>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={definir.isPending}>
            Cancelar
          </Button>
          <Button type="button" onClick={transferir} loading={definir.isPending}>
            {definir.isPending ? "Transferindo…" : "Transferir"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
