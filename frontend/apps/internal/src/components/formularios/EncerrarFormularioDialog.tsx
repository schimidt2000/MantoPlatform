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
import { mensagemDaApi, useEncerrarFormulario } from "../../lib/formulariosAdmin";
import type { MotivoEncerramento } from "../../lib/types";

const CONTROL =
  "flex w-full rounded-md border bg-panel px-3 py-2 text-sm text-ink placeholder:text-muted " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

interface Erros {
  motivo?: string;
  frase?: string;
  geral?: string;
}

/**
 * Encerrar um formulário com motivo (feature 298): ele sai da lista da Home e continua guardado.
 *
 * Os motivos chegam por prop, do servidor — a tela não tem cópia da lista nem sabe qual motivo
 * pede frase (`pede_frase`). O botão nunca fica morto: campo com erro é apontado e recebe o foco.
 */
export function EncerrarFormularioDialog({
  formularioId,
  nome,
  motivos,
  open,
  onClose,
}: {
  formularioId: number | null;
  nome?: string;
  motivos: MotivoEncerramento[];
  open: boolean;
  onClose: () => void;
}) {
  const encerrar = useEncerrarFormulario();
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
    encerrar.reset();
    onClose();
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (formularioId == null) return;
    if (!motivo) {
      setErros({ motivo: "Escolha um motivo." });
      motivoRef.current?.focus();
      return;
    }
    if (pedeFrase && !frase.trim()) {
      setErros({ frase: "Conte em uma frase por que o formulário não vai virar evento." });
      fraseRef.current?.focus();
      return;
    }
    setErros({});
    encerrar.mutate(
      { id: formularioId, motivo, frase: pedeFrase ? frase.trim() : "" },
      {
        onSuccess: fechar,
        onError: (erro) => {
          const campos = erro instanceof ApiRequestError ? erro.fields : undefined;
          if (campos?.motivo || campos?.frase) {
            setErros({ motivo: campos.motivo, frase: campos.frase });
            (campos.frase ? fraseRef : motivoRef).current?.focus();
            return;
          }
          // 409 (outra pessoa já deu destino) e 422 (histórico) chegam com a frase pronta.
          setErros({ geral: mensagemDaApi(erro, "Não foi possível encerrar. Tente novamente.") });
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={(proximo) => !proximo && fechar()}>
      <DialogContent open={open} className="max-w-md">
        <DialogHeader>
          <DialogTitle>Encerrar formulário</DialogTitle>
          <DialogDescription>
            {nome ? `${nome}: o` : "O"} formulário sai da lista e continua guardado. Dá para reabrir
            depois pela tela Formulários.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={enviar} noValidate className="space-y-3">
          <div className="space-y-1">
            <label htmlFor="encerrar-motivo" className="text-sm font-medium text-ink">
              Motivo
            </label>
            <select
              id="encerrar-motivo"
              ref={motivoRef}
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value);
                setErros({});
              }}
              aria-invalid={erros.motivo ? true : undefined}
              aria-describedby={erros.motivo ? "encerrar-motivo-erro" : undefined}
              className={`${CONTROL} h-10 ${erros.motivo ? "border-red" : "border-line"}`}
            >
              <option value="">Escolha…</option>
              {motivos.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.rotulo}
                </option>
              ))}
            </select>
            {erros.motivo && (
              <p id="encerrar-motivo-erro" className="text-xs text-red">
                {erros.motivo}
              </p>
            )}
          </div>

          {pedeFrase && (
            <div className="space-y-1">
              <label htmlFor="encerrar-frase" className="text-sm font-medium text-ink">
                Em uma frase
              </label>
              <textarea
                id="encerrar-frase"
                ref={fraseRef}
                rows={3}
                value={frase}
                onChange={(e) => {
                  setFrase(e.target.value);
                  setErros((atual) => ({ ...atual, frase: undefined }));
                }}
                aria-invalid={erros.frase ? true : undefined}
                aria-describedby={erros.frase ? "encerrar-frase-erro" : undefined}
                className={`${CONTROL} ${erros.frase ? "border-red" : "border-line"}`}
                placeholder="Ex.: a cliente fechou com outra empresa"
              />
              {erros.frase && (
                <p id="encerrar-frase-erro" className="text-xs text-red">
                  {erros.frase}
                </p>
              )}
            </div>
          )}

          {erros.geral && (
            <p role="alert" className="text-sm text-red">
              {erros.geral}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={fechar}>
              Cancelar
            </Button>
            <Button type="submit" loading={encerrar.isPending}>
              {encerrar.isPending ? "Encerrando…" : "Encerrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
