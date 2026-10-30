import { motion, useReducedMotion } from "framer-motion";
import { AlertCircle, Check, CheckCheck, Clock, FileText, Smartphone } from "lucide-react";
import { assetUrl } from "@manto/api-client";
import { Foto, cn } from "@manto/ui";
import { LinkDeArquivo } from "../ArquivoViewer";
import { horaDaMensagem, type Mensagem as MensagemTipo, type Situacao } from "../../lib/conversas";

/**
 * Uma mensagem da conversa (feature 325): balão à esquerda (cliente) ou à direita (equipe), com
 * a mídia, o horário de São Paulo, a situação da enviada e quem mandou.
 *
 * A mídia só tem `url` depois de guardada na Plataforma; antes disso (download em andamento) ou se
 * falhou, o balão diz isso em vez de desenhar um arquivo quebrado (FR-019).
 */

const ROTULO_DA_SITUACAO: Record<Situacao, string> = {
  recebida: "Recebida",
  pendente: "Enviando",
  enviada: "Enviada",
  entregue: "Entregue",
  lida: "Lida",
  falhou: "Não entregue",
};

function IconeDaSituacao({ situacao }: { situacao: Situacao }) {
  const classe = "h-3.5 w-3.5";
  if (situacao === "pendente") return <Clock className={classe} aria-hidden />;
  if (situacao === "enviada") return <Check className={classe} aria-hidden />;
  if (situacao === "entregue") return <CheckCheck className={classe} aria-hidden />;
  if (situacao === "lida") return <CheckCheck className={cn(classe, "text-blue")} aria-hidden />;
  if (situacao === "falhou") return <AlertCircle className={cn(classe, "text-red")} aria-hidden />;
  return null;
}

function MidiaDaMensagem({ mensagem }: { mensagem: MensagemTipo }) {
  const midia = mensagem.midia;
  if (!midia) return null;
  if (midia.estado === "pendente") {
    return <p className="text-xs italic text-muted">Arquivo sendo carregado…</p>;
  }
  if (midia.estado === "falhou" || !midia.url) {
    return <p className="text-xs italic text-muted">Arquivo indisponível. Abra no celular.</p>;
  }
  const url = assetUrl(midia.url) ?? midia.url;
  if (mensagem.tipo === "imagem" || mensagem.tipo === "figurinha") {
    return (
      <LinkDeArquivo caminho={midia.url} nome={midia.nome ?? "Foto"} className="block">
        <Foto
          src={url}
          alt={mensagem.texto ?? "Foto enviada na conversa"}
          className="max-h-64 w-auto max-w-full rounded-md object-contain"
          fallback={<span className="text-xs italic text-muted">Arquivo indisponível. Abra no celular.</span>}
        />
      </LinkDeArquivo>
    );
  }
  if (mensagem.tipo === "audio") {
    return <audio controls preload="none" src={url} className="h-10 w-64 max-w-full" />;
  }
  if (mensagem.tipo === "video") {
    return <video controls preload="metadata" src={url} className="max-h-64 max-w-full rounded-md bg-media" />;
  }
  return (
    <LinkDeArquivo
      caminho={midia.url}
      nome={midia.nome ?? "Documento"}
      className="flex min-h-11 items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm underline-offset-2 hover:underline"
    >
      <FileText className="h-4 w-4 shrink-0" aria-hidden />
      <span className="truncate">{midia.nome ?? "Documento"}</span>
    </LinkDeArquivo>
  );
}

export function Mensagem({ mensagem }: { mensagem: MensagemTipo }) {
  const reduzir = useReducedMotion();
  const daEquipe = mensagem.direcao === "enviada";
  const rodape = [
    mensagem.origem === "celular" ? "Enviada pelo celular" : mensagem.autor?.nome,
    horaDaMensagem(mensagem.momento),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <motion.li
      initial={reduzir ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={cn("flex", daEquipe ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "max-w-[85%] space-y-1.5 rounded-lg px-3 py-2 text-sm shadow-sm sm:max-w-[70%]",
          daEquipe ? "bg-accent-soft text-ink" : "border border-line bg-panel text-ink",
        )}
      >
        {mensagem.tipo === "modelo" && mensagem.modelo_nome ? (
          <p className="text-xs font-medium text-muted">Modelo: {mensagem.modelo_nome}</p>
        ) : null}
        <MidiaDaMensagem mensagem={mensagem} />
        {mensagem.texto ? <p className="whitespace-pre-wrap break-words">{mensagem.texto}</p> : null}
        <p className="flex items-center justify-end gap-1 text-xs text-muted">
          {mensagem.origem === "celular" ? <Smartphone className="h-3.5 w-3.5" aria-hidden /> : null}
          <span>{rodape}</span>
          {daEquipe ? (
            <span className="inline-flex items-center gap-0.5" title={ROTULO_DA_SITUACAO[mensagem.situacao]}>
              <IconeDaSituacao situacao={mensagem.situacao} />
              <span className="sr-only">{ROTULO_DA_SITUACAO[mensagem.situacao]}</span>
            </span>
          ) : null}
        </p>
        {mensagem.erro ? (
          <p role="alert" className="text-xs text-red">
            Não entregue: {mensagem.erro.motivo}
          </p>
        ) : null}
      </div>
    </motion.li>
  );
}
