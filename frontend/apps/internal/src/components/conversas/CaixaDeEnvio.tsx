import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Paperclip, Send, X } from "lucide-react";
import { Button } from "@manto/ui";
import {
  codigoDaRecusa,
  mensagemDoErro,
  novaChaveDeEnvio,
  useEnviarArquivo,
  useEnviarTexto,
  type ConversaResumo,
} from "../../lib/conversas";

/**
 * Caixa de envio da conversa (feature 325, FR-010/FR-011/FR-018/FR-021).
 *
 * - Computador: Enter envia, Shift+Enter quebra a linha. No toque (celular), Enter quebra a linha e
 *   o envio é pelo botão — o teclado do celular não tem Shift.
 * - O texto só sai do campo quando a Plataforma confirma a gravação; no erro, ele fica (Princípio V).
 * - A `chave_envio` é do RASCUNHO, não do clique: nasce no primeiro envio e só muda quando o texto
 *   ou o arquivo mudam (ou no sucesso). Se a resposta se perde (502 no meio do deploy) e a pessoa
 *   envia de novo, o servidor reconhece a chave e devolve a mensagem já enviada — a cliente não
 *   recebe duas vezes.
 * - Com a janela de 24 h fechada, a caixa vira o aviso + "Enviar modelo" (só modelo aprovado sai).
 */

const ACEITOS = [
  "image/jpeg",
  "image/png",
  "audio/aac",
  "audio/amr",
  "audio/mpeg",
  "audio/mp4",
  "audio/x-m4a",
  "audio/ogg",
  "video/mp4",
  "video/3gpp",
  "application/pdf",
  "text/plain",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
].join(",");

function ehToque(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches === true;
}

interface CaixaDeEnvioProps {
  conversa: ConversaResumo;
  onEnviarModelo: () => void;
  onJanelaFechou: () => void;
}

export function CaixaDeEnvio({ conversa, onEnviarModelo, onJanelaFechou }: CaixaDeEnvioProps) {
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const chaveDoRascunho = useRef<string | null>(null);
  const entradaDeArquivo = useRef<HTMLInputElement>(null);
  const campo = useRef<HTMLTextAreaElement>(null);
  const enviarTexto = useEnviarTexto(conversa.id);
  const enviarArquivo = useEnviarArquivo(conversa.id);
  const enviando = enviarTexto.isPending || enviarArquivo.isPending;

  if (!conversa.janela_aberta) {
    return (
      <div className="space-y-2 border-t border-line bg-panel p-3">
        <p className="text-sm text-muted">
          A janela de 24 horas desta conversa fechou. Para retomar o contato, envie um modelo aprovado.
        </p>
        <Button type="button" onClick={onEnviarModelo} className="w-full sm:w-auto">
          Enviar modelo
        </Button>
      </div>
    );
  }

  const mudouORascunho = () => {
    chaveDoRascunho.current = null;
  };

  const aoErrar = (falha: unknown) => {
    if (codigoDaRecusa(falha) === "janela_fechada") onJanelaFechou();
    setErro(mensagemDoErro(falha, "Não foi possível enviar. Tente novamente."));
    campo.current?.focus();
  };

  const aoEnviar = () => {
    chaveDoRascunho.current = null;
    setArquivo(null);
    setTexto("");
  };

  const enviar = (evento?: FormEvent) => {
    evento?.preventDefault();
    if (enviando) return;
    const conteudo = texto.trim();
    setErro(null);
    if (!arquivo && !conteudo) {
      setErro("Informe a mensagem.");
      campo.current?.focus();
      return;
    }
    chaveDoRascunho.current ??= novaChaveDeEnvio();
    const chave_envio = chaveDoRascunho.current;
    if (arquivo) {
      enviarArquivo.mutate({ arquivo, legenda: conteudo, chave_envio }, { onSuccess: aoEnviar, onError: aoErrar });
      return;
    }
    enviarTexto.mutate({ texto: conteudo, chave_envio }, { onSuccess: aoEnviar, onError: aoErrar });
  };

  const aoTeclar = (evento: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evento.key !== "Enter" || evento.shiftKey || evento.nativeEvent.isComposing || ehToque()) return;
    evento.preventDefault();
    enviar();
  };

  return (
    <form onSubmit={enviar} className="space-y-2 border-t border-line bg-panel p-3">
      {arquivo ? (
        <div className="flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm">
          <Paperclip className="h-4 w-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate">{arquivo.name}</span>
          <Button
            type="button"
            variant="ghost"
            className="h-11 w-11 px-0"
            onClick={() => {
              setArquivo(null);
              mudouORascunho();
            }}
            aria-label="Remover o arquivo"
            disabled={enviando}
          >
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      ) : null}
      <div className="flex items-end gap-2">
        <input
          ref={entradaDeArquivo}
          type="file"
          accept={ACEITOS}
          className="hidden"
          onChange={(e) => {
            setArquivo(e.target.files?.[0] ?? null);
            mudouORascunho();
            e.target.value = "";
          }}
        />
        <Button
          type="button"
          variant="outline"
          className="h-11 w-11 shrink-0 px-0"
          onClick={() => entradaDeArquivo.current?.click()}
          aria-label="Inserir arquivo"
          title="Inserir arquivo"
          disabled={enviando}
        >
          <Paperclip className="h-5 w-5" aria-hidden />
        </Button>
        <label htmlFor={`caixa-${conversa.id}`} className="sr-only">
          Mensagem
        </label>
        <textarea
          id={`caixa-${conversa.id}`}
          ref={campo}
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value);
            mudouORascunho();
            if (erro) setErro(null);
          }}
          onKeyDown={aoTeclar}
          rows={1}
          maxLength={4096}
          placeholder={arquivo ? "Legenda (opcional)" : "Mensagem"}
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `erro-caixa-${conversa.id}` : undefined}
          className="max-h-40 min-h-11 flex-1 resize-y rounded-md border border-line-strong bg-panel px-3 py-2.5 text-sm text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-red aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-red"
        />
        <Button type="submit" loading={enviando} className="h-11 shrink-0" aria-label="Enviar">
          {enviando ? "Enviando…" : <Send className="h-5 w-5" aria-hidden />}
        </Button>
      </div>
      <div className="flex items-center justify-between gap-2">
        {erro ? (
          <p id={`erro-caixa-${conversa.id}`} role="alert" className="text-xs text-red">
            {erro}
          </p>
        ) : (
          <span />
        )}
        <Button type="button" variant="ghost" size="sm" onClick={onEnviarModelo}>
          Enviar modelo
        </Button>
      </div>
    </form>
  );
}
