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
import { useMudarNovidades, type TextoDeConsentimento } from "../../lib/baseAutorizada";

export interface AceiteDeNovidadesDialogProps {
  clientId: number;
  nome: string;
  /** Já tem aceite? Então o diálogo retira; senão, registra. */
  ativo: boolean;
  texto: TextoDeConsentimento;
  origens: string[];
  /** Origem marcada ao abrir (na conversa, "Conversa"). */
  origemPadrao?: string;
  /** Vai para o histórico como prova (ex.: `conversa:12`). */
  referencia?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConcluido: (mensagem: string) => void;
}

/**
 * Registrar ou retirar o aceite de novidades (feature 350, LGPD).
 *
 * O texto exato aparece antes do botão: é ele que vai inteiro para o histórico. A origem é uma
 * lista fechada — origem livre não prova nada. Usado na ficha e no cabeçalho da conversa.
 */
export function AceiteDeNovidadesDialog({
  clientId,
  nome,
  ativo,
  texto,
  origens,
  origemPadrao,
  referencia,
  open,
  onOpenChange,
  onConcluido,
}: AceiteDeNovidadesDialogProps) {
  const [origem, setOrigem] = useState(origemPadrao ?? "");
  const mudar = useMudarNovidades(clientId);

  useEffect(() => {
    if (open) {
      setOrigem(origemPadrao ?? "");
      mudar.reset();
    }
    // `mudar` muda a cada render; só a abertura importa aqui.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, origemPadrao]);

  const erroDeOrigem =
    mudar.error instanceof ApiRequestError ? mudar.error.fields?.origem : undefined;
  const erroGeral = mudar.error && !erroDeOrigem ? "Não foi possível salvar. Tente novamente." : null;

  function salvar() {
    mudar.mutate(
      { acao: ativo ? "retirar" : "registrar", origem, referencia },
      {
        onSuccess: () => {
          onOpenChange(false);
          onConcluido(ativo ? "Aceite de novidades retirado." : "Aceite de novidades registrado.");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(aberto) => !mudar.isPending && onOpenChange(aberto)}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{ativo ? "Retirar aceite de novidades" : "Registrar aceite de novidades"}</DialogTitle>
          <DialogDescription>
            {ativo
              ? `${nome} deixa de receber novidades. O aceite anterior continua no histórico.`
              : `Registre só se ${nome} disse sim a este texto:`}
          </DialogDescription>
        </DialogHeader>

        {!ativo && (
          <blockquote className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-ink">
            “{texto.texto}”
            <span className="mt-1 block text-xs text-muted">Versão {texto.versao}</span>
          </blockquote>
        )}

        <fieldset className="space-y-1">
          <legend className="mb-1 text-sm text-muted">
            {ativo ? "Por onde ela pediu para sair" : "Por onde ela aceitou"}
          </legend>
          {origens.map((opcao) => (
            <label
              key={opcao}
              className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md px-2 text-sm text-ink hover:bg-surface-2"
            >
              <input
                type="radio"
                name="origem-do-aceite"
                value={opcao}
                checked={origem === opcao}
                onChange={() => setOrigem(opcao)}
                className="h-4 w-4 accent-accent"
              />
              {opcao}
            </label>
          ))}
          {erroDeOrigem && (
            <p className="text-sm text-red" role="alert">
              {erroDeOrigem}
            </p>
          )}
        </fieldset>

        {erroGeral && (
          <p className="text-sm text-red" role="alert">
            {erroGeral}
          </p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={mudar.isPending}>
            Cancelar
          </Button>
          <Button onClick={salvar} loading={mudar.isPending} disabled={!origem}>
            {ativo ? "Retirar aceite" : "Registrar aceite"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
