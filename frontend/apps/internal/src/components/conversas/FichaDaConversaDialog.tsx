import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@manto/ui";
import {
  mensagemDoErro,
  useLigarFicha,
  useRemoverFicha,
  type ConversaResumo,
  type EscolhaDaFicha,
} from "../../lib/conversas";
import { EscolhaDeFicha, erroDaFicha, type ErroDaFicha } from "./EscolhaDeFicha";

/**
 * "Ligar à ficha" / "Trocar ficha" (feature 333, FR-009): a ficha da cliente desta conversa. A escolha feita
 * aqui fica — a ligação automática pelo telefone não a desfaz, nem depois de "Remover vínculo" (que tira o
 * vínculo sem apagar a ficha). Orçamentos já enviados continuam com a ficha do envio.
 */

interface FichaDaConversaDialogProps {
  conversa: ConversaResumo;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FichaDaConversaDialog({ conversa, open, onOpenChange }: FichaDaConversaDialogProps) {
  const ligar = useLigarFicha(conversa.id);
  const remover = useRemoverFicha(conversa.id);
  const [escolha, setEscolha] = useState<EscolhaDaFicha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [erroDoCampo, setErroDoCampo] = useState<ErroDaFicha | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setEscolha(null);
      setErro(null);
      setErroDoCampo(null);
      setAviso(null);
    }
  }, [open]);

  const ocupado = ligar.isPending || remover.isPending;
  const whatsapp = conversa.canal !== "instagram";

  const salvar = () => {
    if (!escolha) {
      setErroDoCampo({ campo: "cliente", mensagem: "Selecione a ficha da cliente ou informe nome e telefone." });
      return;
    }
    setErro(null);
    setErroDoCampo(null);
    ligar.mutate(escolha, {
      onSuccess: (resposta) => {
        // A ficha "nova" já existia pelo telefone: diz antes de fechar (não há toast no app).
        if (resposta.reaproveitada) setAviso("Esta ficha já existia e foi ligada à conversa.");
        else onOpenChange(false);
      },
      onError: (falha) => {
        const doCampo = falha instanceof ApiRequestError ? erroDaFicha(falha.fields) : null;
        if (doCampo) setErroDoCampo(doCampo);
        else setErro(mensagemDoErro(falha, "Não foi possível ligar a ficha. Tente novamente."));
      },
    });
  };

  const tirar = () => {
    setErro(null);
    remover.mutate(undefined, {
      onSuccess: () => onOpenChange(false),
      onError: (falha) => setErro(mensagemDoErro(falha, "Não foi possível remover o vínculo. Tente novamente.")),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-md">
        <DialogHeader>
          <DialogTitle>{conversa.cliente ? "Trocar ficha" : "Ligar à ficha"}</DialogTitle>
          <DialogDescription>
            {conversa.cliente
              ? `Esta conversa está ligada à ficha de ${conversa.cliente.nome}. Escolha outra ou remova o vínculo.`
              : "Escolha a ficha da cliente desta conversa ou crie uma nova."}
          </DialogDescription>
        </DialogHeader>
        {aviso ? (
          <p role="status" className="text-sm">
            {aviso}
          </p>
        ) : (
          <EscolhaDeFicha
            id={`ficha-${conversa.id}`}
            valor={escolha}
            onMudar={(v) => {
              setEscolha(v);
              setErroDoCampo(null);
            }}
            telefoneInicial={whatsapp ? (conversa.telefone_legivel ?? conversa.telefone) : null}
            nomeInicial={conversa.nome_perfil}
            erro={erroDoCampo}
          />
        )}
        {erro ? (
          <p role="alert" className="text-sm text-red">
            {erro}
          </p>
        ) : null}
        <DialogFooter className="flex-wrap gap-2">
          {aviso ? (
            <Button type="button" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
          ) : (
            <>
              {conversa.cliente ? (
                <Button type="button" variant="outline" onClick={tirar} loading={remover.isPending} disabled={ocupado}>
                  {remover.isPending ? "Removendo…" : "Remover vínculo"}
                </Button>
              ) : null}
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={ocupado}>
                Cancelar
              </Button>
              <Button type="button" onClick={salvar} loading={ligar.isPending} disabled={ocupado}>
                {ligar.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
