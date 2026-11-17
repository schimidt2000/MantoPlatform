import { useRef, useState, type FormEvent } from "react";
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
import { mensagemDoErro, useMarcarPerdida, type MotivoDePerda } from "../../lib/conversas";

const CONTROL =
  "flex w-full rounded-md border bg-panel px-3 py-2 text-sm text-ink placeholder:text-muted " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

interface Erros {
  motivo?: string;
  frase?: string;
  geral?: string;
}

/**
 * Marcar a conversa como perdida (feature 349, FR-007), no molde do encerramento de formulário (298): os motivos
 * chegam do servidor (a tela não tem cópia da lista nem sabe qual pede frase). A frase é opcional nos outros motivos
 * e obrigatória no "Outro". O erro do servidor volta ao campo.
 */
export function PerdidaDialog({
  conversaId,
  nome,
  motivos,
  open,
  onClose,
}: {
  conversaId: number;
  nome: string;
  motivos: MotivoDePerda[];
  open: boolean;
  onClose: () => void;
}) {
  const marcar = useMarcarPerdida(conversaId);
  const [motivo, setMotivo] = useState("");
  const [frase, setFrase] = useState("");
  const [erros, setErros] = useState<Erros>({});
  const motivoRef = useRef<HTMLSelectElement>(null);
  const fraseRef = useRef<HTMLTextAreaElement>(null);
  const pedeFrase = motivos.find((m) => m.codigo === motivo)?.pede_frase ?? false;

  function fechar() {
    setMotivo("");
    setFrase("");
    setErros({});
    marcar.reset();
    onClose();
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!motivo) {
      setErros({ motivo: "Selecione o motivo." });
      motivoRef.current?.focus();
      return;
    }
    if (pedeFrase && !frase.trim()) {
      setErros({ frase: "Informe em uma frase por que a conversa foi perdida." });
      fraseRef.current?.focus();
      return;
    }
    setErros({});
    marcar.mutate(
      { motivo, frase: frase.trim() || undefined },
      {
        onSuccess: fechar,
        onError: (erro) => {
          const campos = erro instanceof ApiRequestError ? erro.fields : undefined;
          if (campos?.motivo || campos?.frase) {
            setErros({ motivo: campos.motivo, frase: campos.frase });
            (campos.frase ? fraseRef : motivoRef).current?.focus();
            return;
          }
          setErros({ geral: mensagemDoErro(erro, "Não foi possível marcar a conversa como perdida. Tente novamente.") });
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(proximo) => !proximo && fechar()}>
      <DialogContent open={open} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Marcar como perdida</DialogTitle>
          <DialogDescription>
            A conversa com {nome} sai da régua de lembretes e do filtro de orçamento parado. É possível reabrir depois.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={enviar} noValidate className="space-y-3">
          <div className="space-y-1">
            <label htmlFor="perdida-motivo" className="text-sm font-medium text-ink">
              Motivo
            </label>
            <select
              id="perdida-motivo"
              ref={motivoRef}
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value);
                setErros({});
              }}
              aria-invalid={erros.motivo ? true : undefined}
              aria-describedby={erros.motivo ? "perdida-motivo-erro" : undefined}
              className={`${CONTROL} h-11 md:h-10 ${erros.motivo ? "border-red" : "border-line"}`}
            >
              <option value="">Selecione…</option>
              {motivos.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.rotulo}
                </option>
              ))}
            </select>
            {erros.motivo && (
              <p id="perdida-motivo-erro" className="text-xs text-red">
                {erros.motivo}
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label htmlFor="perdida-frase" className="text-sm font-medium text-ink">
              {pedeFrase ? "Em uma frase" : "Em uma frase (opcional)"}
            </label>
            <textarea
              id="perdida-frase"
              ref={fraseRef}
              rows={3}
              maxLength={300}
              value={frase}
              onChange={(e) => {
                setFrase(e.target.value);
                setErros((atual) => ({ ...atual, frase: undefined }));
              }}
              aria-invalid={erros.frase ? true : undefined}
              aria-describedby={erros.frase ? "perdida-frase-erro" : undefined}
              className={`${CONTROL} ${erros.frase ? "border-red" : "border-line"}`}
              placeholder="Ex.: fechou com o buffet que já incluía personagens"
            />
            {erros.frase && (
              <p id="perdida-frase-erro" className="text-xs text-red">
                {erros.frase}
              </p>
            )}
          </div>

          {erros.geral && (
            <p role="alert" className="text-sm text-red">
              {erros.geral}
            </p>
          )}

          <DialogFooter className="flex-wrap gap-2">
            <Button type="button" variant="ghost" onClick={fechar}>
              Cancelar
            </Button>
            <Button type="submit" loading={marcar.isPending}>
              {marcar.isPending ? "Salvando…" : "Marcar como perdida"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
