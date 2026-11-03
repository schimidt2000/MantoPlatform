import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Mic, Paperclip, Send, X, Zap } from "lucide-react";
import { Button, cn } from "@manto/ui";
import {
  aplicarNome,
  codigoDaRecusa,
  ehToque,
  mensagemDoErro,
  novaChaveDeEnvio,
  useEnviarArquivo,
  useEnviarTexto,
  useRespostasRapidas,
  type ConversaResumo,
  type RespostaRapida,
} from "../../lib/conversas";
import { GerenciarRespostasDialog } from "./GerenciarRespostasDialog";
import { BarraDeGravacao, useGravador } from "./GravadorDeAudio";
import { CaixaDeNota } from "./NotaInterna";
import { RespostasRapidas, filtrarRespostas, teclaNaLista, type ControleDaLista } from "./RespostasRapidas";

/**
 * Caixa de envio da conversa (features 325 e 328).
 *
 * - "Mensagem | Nota interna" no topo (328): a nota nunca sai para a cliente e vale com a janela
 *   fechada.
 * - Computador: Enter envia, Shift+Enter quebra a linha. No toque (celular), Enter quebra a linha e
 *   o envio é pelo botão — o teclado do celular não tem Shift.
 * - O texto só sai do campo quando a Plataforma confirma a gravação; no erro, ele fica (Princípio V).
 * - A `chave_envio` é do RASCUNHO, não do clique: nasce no primeiro envio e só muda quando o texto
 *   ou o arquivo mudam (ou no sucesso). Se a resposta se perde (502 no meio do deploy) e a pessoa
 *   envia de novo, o servidor reconhece a chave e devolve a mensagem já enviada — a cliente não
 *   recebe duas vezes.
 * - Respostas rápidas (328): pelo botão ou digitando "/" no começo; escolher só preenche o campo.
 * - Com o campo vazio, o botão de enviar vira o microfone (328): o áudio gravado sai como arquivo.
 * - Com a janela de 24 h fechada, a mensagem vira o aviso + "Enviar modelo" (só modelo aprovado sai).
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

type Modo = "mensagem" | "nota";
/** De onde a lista de respostas rápidas foi aberta: do botão (busca própria) ou da "/" no campo. */
type Painel = null | "botao" | "barra";

function AlternarModo({ modo, onMudar }: { modo: Modo; onMudar: (modo: Modo) => void }) {
  const opcoes: { valor: Modo; rotulo: string }[] = [
    { valor: "mensagem", rotulo: "Mensagem" },
    { valor: "nota", rotulo: "Nota interna" },
  ];
  return (
    <div role="group" aria-label="Tipo de registro" className="flex gap-1 px-3 pt-2">
      {opcoes.map((opcao) => (
        <button
          key={opcao.valor}
          type="button"
          aria-pressed={modo === opcao.valor}
          onClick={() => onMudar(opcao.valor)}
          className={cn(
            "min-h-11 rounded-md px-3 text-xs font-medium transition-colors md:min-h-8",
            modo === opcao.valor
              ? opcao.valor === "nota"
                ? "bg-gold-50 text-gold-ink"
                : "bg-surface-2 text-ink"
              : "text-muted hover:text-ink",
          )}
        >
          {opcao.rotulo}
        </button>
      ))}
    </div>
  );
}

function JanelaFechada({ onEnviarModelo }: { onEnviarModelo: () => void }) {
  return (
    <div className="space-y-2 p-3 pt-2">
      <p className="text-sm text-muted">
        A janela de 24 horas desta conversa fechou. Para retomar o contato, envie um modelo aprovado.
      </p>
      <Button type="button" onClick={onEnviarModelo} className="w-full sm:w-auto">
        Enviar modelo
      </Button>
    </div>
  );
}

interface CaixaDeEnvioProps {
  conversa: ConversaResumo;
  onEnviarModelo: () => void;
  onJanelaFechou: () => void;
}

export function CaixaDeEnvio({ conversa, onEnviarModelo, onJanelaFechou }: CaixaDeEnvioProps) {
  const [modo, setModo] = useState<Modo>("mensagem");
  return (
    <div className="border-t border-line bg-panel">
      <AlternarModo modo={modo} onMudar={setModo} />
      {modo === "nota" ? (
        <CaixaDeNota conversaId={conversa.id} />
      ) : conversa.janela_aberta ? (
        <CaixaDeMensagem conversa={conversa} onEnviarModelo={onEnviarModelo} onJanelaFechou={onJanelaFechou} />
      ) : (
        <JanelaFechada onEnviarModelo={onEnviarModelo} />
      )}
    </div>
  );
}

/** Lista de respostas rápidas da caixa: quem abriu, o que busca, qual está ativa. */
function useListaDeRespostas(texto: string) {
  const [painel, setPainel] = useState<Painel>(null);
  const [buscaDoBotao, setBuscaDoBotao] = useState("");
  const [ativo, setAtivo] = useState(0);
  const respostas = useRespostasRapidas(painel !== null);
  const consulta = painel === "barra" ? texto.slice(1) : buscaDoBotao;
  const filtradas = filtrarRespostas(respostas.data?.respostas, consulta);

  useEffect(() => setAtivo(0), [consulta, painel]);

  const abrirPeloBotao = () => {
    setBuscaDoBotao("");
    setPainel((atual) => (atual === "botao" ? null : "botao"));
  };
  /** A "/" no começo do campo, sem espaço depois, abre a lista; qualquer outra coisa a fecha. */
  const acompanharCampo = (valor: string) => {
    const comando = /^\/\S*$/.test(valor);
    setPainel((atual) => (comando ? (atual === "botao" ? atual : "barra") : atual === "barra" ? null : atual));
  };
  return { painel, setPainel, buscaDoBotao, setBuscaDoBotao, ativo, setAtivo, respostas, filtradas, abrirPeloBotao, acompanharCampo };
}

function CaixaDeMensagem({ conversa, onEnviarModelo, onJanelaFechou }: CaixaDeEnvioProps) {
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  // O aviso do microfone não é erro do campo: não deixa a mensagem vermelha.
  const [aviso, setAviso] = useState<string | null>(null);
  const [gerenciando, setGerenciando] = useState(false);
  const chaveDoRascunho = useRef<string | null>(null);
  const entradaDeArquivo = useRef<HTMLInputElement>(null);
  const campo = useRef<HTMLTextAreaElement>(null);
  const area = useRef<HTMLDivElement>(null);
  const idDaLista = useId();
  const enviarTexto = useEnviarTexto(conversa.id);
  const enviarArquivo = useEnviarArquivo(conversa.id);
  const lista = useListaDeRespostas(texto);
  const gravador = useGravador(setAviso);
  const enviando = enviarTexto.isPending || enviarArquivo.isPending;
  const { painel, setPainel } = lista;

  // Clique fora fecha a lista de respostas rápidas.
  useEffect(() => {
    if (!painel) return;
    const fora = (evento: MouseEvent) => {
      if (area.current && !area.current.contains(evento.target as Node)) setPainel(null);
    };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [painel, setPainel]);

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
    setAviso(null);
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

  const escolher = (resposta: RespostaRapida) => {
    const inserido = aplicarNome(resposta.texto, conversa.nome);
    setTexto((atual) => {
      if (painel === "barra" || !atual.trim()) return inserido;
      return `${atual}${/\s$/.test(atual) ? "" : " "}${inserido}`;
    });
    mudouORascunho();
    setPainel(null);
    campo.current?.focus();
  };

  const controle: ControleDaLista = {
    total: lista.filtradas.length,
    ativo: lista.ativo,
    onAtivo: lista.setAtivo,
    onEscolherAtivo: () => {
      const resposta = lista.filtradas[lista.ativo];
      if (resposta) escolher(resposta);
    },
    onFechar: () => setPainel(null),
  };

  const aoTeclar = (evento: KeyboardEvent<HTMLTextAreaElement>) => {
    if (painel === "barra" && teclaNaLista(evento, controle)) return;
    if (evento.key !== "Enter" || evento.shiftKey || evento.nativeEvent.isComposing || ehToque()) return;
    evento.preventDefault();
    enviar();
  };

  /** O áudio gravado sai pelo mesmo envio de arquivo; se falhar, fica anexado para tentar de novo. */
  const enviarGravacao = () =>
    gravador.finalizar((gravado) => {
      if (!gravado) {
        setAviso("Nada foi gravado. Tente de novo.");
        return;
      }
      setErro(null);
      setAviso(null);
      enviarArquivo.mutate(
        { arquivo: gravado, legenda: "", chave_envio: novaChaveDeEnvio() },
        {
          onError: (falha) => {
            setArquivo(gravado);
            mudouORascunho();
            aoErrar(falha);
          },
        },
      );
    });

  const mostrarMicrofone = gravador.disponivel && !arquivo && !texto.trim();

  return (
    <>
      <form onSubmit={enviar} className="space-y-2 p-3 pt-2">
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
        {gravador.estado !== "parado" ? (
          <BarraDeGravacao
            estado={gravador.estado}
            segundos={gravador.segundos}
            enviando={enviarArquivo.isPending}
            onCancelar={gravador.cancelar}
            onEnviar={enviarGravacao}
          />
        ) : (
          <div ref={area} className="relative flex items-end gap-2">
            {painel ? (
              <RespostasRapidas
                idDaLista={idDaLista}
                respostas={lista.filtradas}
                carregando={lista.respostas.isLoading}
                falhou={lista.respostas.isError}
                onTentarDeNovo={() => void lista.respostas.refetch()}
                busca={painel === "botao" ? { valor: lista.buscaDoBotao, onMudar: lista.setBuscaDoBotao } : null}
                controle={controle}
                onEscolher={escolher}
                onGerenciar={() => {
                  setPainel(null);
                  setGerenciando(true);
                }}
              />
            ) : null}
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
            <Button
              type="button"
              variant="outline"
              className="h-11 w-11 shrink-0 px-0"
              onClick={lista.abrirPeloBotao}
              aria-label="Respostas rápidas"
              aria-expanded={painel !== null}
              title="Respostas rápidas (ou digite / no começo)"
              disabled={enviando}
            >
              <Zap className="h-5 w-5" aria-hidden />
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
                lista.acompanharCampo(e.target.value);
                mudouORascunho();
                if (erro) setErro(null);
              }}
              onKeyDown={aoTeclar}
              rows={1}
              maxLength={4096}
              placeholder={arquivo ? "Legenda (opcional)" : "Mensagem"}
              aria-invalid={erro ? true : undefined}
              aria-describedby={erro ? `erro-caixa-${conversa.id}` : undefined}
              aria-controls={painel === "barra" ? idDaLista : undefined}
              className="max-h-40 min-h-11 min-w-0 flex-1 resize-y rounded-md border border-line-strong bg-panel px-3 py-2.5 text-sm text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-red aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-red"
            />
            {mostrarMicrofone ? (
              <Button
                type="button"
                className="h-11 w-11 shrink-0 px-0"
                onClick={() => {
                setAviso(null);
                void gravador.iniciar();
              }}
                aria-label="Gravar áudio"
                title="Gravar áudio"
                loading={enviarArquivo.isPending}
              >
                <Mic className="h-5 w-5" aria-hidden />
              </Button>
            ) : (
              <Button type="submit" loading={enviando} className="h-11 shrink-0" aria-label="Enviar">
                {enviando ? "Enviando…" : <Send className="h-5 w-5" aria-hidden />}
              </Button>
            )}
          </div>
        )}
        <div className="flex items-center justify-between gap-2">
          {erro || aviso ? (
            <p id={`erro-caixa-${conversa.id}`} role="alert" className="text-xs text-red">
              {erro ?? aviso}
            </p>
          ) : (
            <span />
          )}
          <Button type="button" variant="ghost" size="sm" onClick={onEnviarModelo}>
            Enviar modelo
          </Button>
        </div>
      </form>
      <GerenciarRespostasDialog open={gerenciando} onOpenChange={setGerenciando} />
    </>
  );
}
