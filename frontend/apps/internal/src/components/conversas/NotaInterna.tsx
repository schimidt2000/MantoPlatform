import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { StickyNote } from "lucide-react";
import { Button } from "@manto/ui";
import { ehToque, horaDaMensagem, mensagemDoErro, useGravarNota, type Nota } from "../../lib/conversas";

/**
 * Nota interna na linha do tempo (feature 328, FR-009): centralizada, em dourado claro, com o autor
 * e o horário — nunca parece uma mensagem enviada, porque nunca sai para a cliente.
 */

export function NotaInterna({ nota }: { nota: Nota }) {
  const reduzir = useReducedMotion();
  return (
    <motion.li
      className="mx-auto max-w-[min(32rem,92%)] rounded-md border border-gold bg-gold-50 px-3 py-2 text-sm text-ink"
      initial={reduzir ? false : { opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.18 }}
    >
      <p className="mb-0.5 flex items-center gap-1 text-xs font-medium text-gold-ink">
        <StickyNote className="h-3.5 w-3.5" aria-hidden />
        Nota interna · {nota.autor?.nome ?? "Equipe"} · {horaDaMensagem(nota.momento)}
      </p>
      <p className="whitespace-pre-wrap break-words">{nota.texto}</p>
    </motion.li>
  );
}

interface CaixaDeNotaProps {
  conversaId: number;
}

/**
 * A caixa no modo "Nota interna": grava a nota, que nunca sai para a cliente e vale com a janela de
 * 24 h fechada. O erro do servidor (`fields.texto`) realça o campo; o texto só sai no sucesso.
 */
export function CaixaDeNota({ conversaId }: CaixaDeNotaProps) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const campo = useRef<HTMLTextAreaElement>(null);
  const gravar = useGravarNota(conversaId);

  const enviar = (evento?: FormEvent) => {
    evento?.preventDefault();
    if (gravar.isPending) return;
    if (!texto.trim()) {
      setErro("Informe a nota.");
      campo.current?.focus();
      return;
    }
    setErro(null);
    gravar.mutate(texto.trim(), {
      onSuccess: () => setTexto(""),
      onError: (falha) => {
        setErro(mensagemDoErro(falha, "Não foi possível gravar a nota. Tente novamente."));
        campo.current?.focus();
      },
    });
  };

  const aoTeclar = (evento: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evento.key !== "Enter" || evento.shiftKey || evento.nativeEvent.isComposing || ehToque()) return;
    evento.preventDefault();
    enviar();
  };

  return (
    <form onSubmit={enviar} className="space-y-2 p-3 pt-2">
      <div className="flex items-end gap-2">
        <label htmlFor={`nota-${conversaId}`} className="sr-only">
          Nota interna
        </label>
        <textarea
          id={`nota-${conversaId}`}
          ref={campo}
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value);
            if (erro) setErro(null);
          }}
          onKeyDown={aoTeclar}
          rows={1}
          maxLength={2000}
          placeholder="Nota interna (só a equipe vê)"
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `erro-nota-${conversaId}` : undefined}
          className="max-h-40 min-h-11 flex-1 resize-y rounded-md border border-gold bg-gold-50 px-3 py-2.5 text-sm text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-red aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-red"
        />
        <Button type="submit" loading={gravar.isPending} className="h-11 shrink-0">
          {gravar.isPending ? "Gravando…" : "Gravar nota"}
        </Button>
      </div>
      {erro ? (
        <p id={`erro-nota-${conversaId}`} role="alert" className="text-xs text-red">
          {erro}
        </p>
      ) : null}
    </form>
  );
}
