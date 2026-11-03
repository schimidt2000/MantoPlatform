import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Mic, Send, X } from "lucide-react";
import { Button } from "@manto/ui";

/**
 * Gravar áudio pelo microfone (feature 328, FR-012 a FR-014).
 *
 * O navegador grava no primeiro formato que souber: ogg/opus (Firefox), webm/opus (Chrome, Edge —
 * o servidor troca o recipiente por ogg, sem recodificar) ou mp4 (Safari, que chega como áudio
 * comum, sem a marca de nota de voz). A gravação para sozinha em 5 minutos e espera "Enviar".
 * Sem permissão ou sem microfone, a caixa diz como liberar e nada é gravado.
 */

export const TEXTO_MICROFONE_NEGADO =
  "Não foi possível usar o microfone. Libere o acesso nas configurações do navegador.";
const LIMITE_SEGUNDOS = 5 * 60;
const FORMATOS = ["audio/ogg;codecs=opus", "audio/webm;codecs=opus", "audio/mp4"];
const EXTENSAO: Record<string, string> = { "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "m4a" };

export type EstadoDaGravacao = "parado" | "gravando" | "pronto";

function formatoSuportado(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return FORMATOS.find((f) => MediaRecorder.isTypeSupported(f));
}

function nomeDoArquivo(mime: string): string {
  const agora = new Date();
  const dois = (n: number) => String(n).padStart(2, "0");
  const carimbo =
    `${agora.getFullYear()}${dois(agora.getMonth() + 1)}${dois(agora.getDate())}-` +
    `${dois(agora.getHours())}${dois(agora.getMinutes())}${dois(agora.getSeconds())}`;
  return `audio-${carimbo}.${EXTENSAO[mime.split(";")[0] ?? ""] ?? "webm"}`;
}

/** "1:07" */
export function tempoDaGravacao(segundos: number): string {
  return `${Math.floor(segundos / 60)}:${String(segundos % 60).padStart(2, "0")}`;
}

export function useGravador(onErro: (mensagem: string) => void) {
  const [estado, setEstado] = useState<EstadoDaGravacao>("parado");
  const [segundos, setSegundos] = useState(0);
  const gravador = useRef<MediaRecorder | null>(null);
  const pedacos = useRef<Blob[]>([]);
  const relogio = useRef<ReturnType<typeof setInterval> | null>(null);
  // Quem recebe o arquivo quando a gravação parar ("Enviar" ou "Cancelar"); nulo = parou sozinha.
  const aoTerminar = useRef<((arquivo: File | null) => void) | null>(null);
  // O áudio que parou sozinho nos 5 minutos, esperando o "Enviar".
  const ultimoArquivo = useRef<File | null>(null);

  const soltarMicrofone = useCallback(() => {
    if (relogio.current) clearInterval(relogio.current);
    relogio.current = null;
    gravador.current?.stream.getTracks().forEach((faixa) => faixa.stop());
  }, []);

  useEffect(() => soltarMicrofone, [soltarMicrofone]);

  const parar = useCallback(() => {
    if (gravador.current?.state === "recording") gravador.current.stop();
  }, []);

  const iniciar = useCallback(async () => {
    const formato = formatoSuportado();
    let fluxo: MediaStream;
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("sem microfone");
      fluxo = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      onErro(TEXTO_MICROFONE_NEGADO);
      return;
    }
    const novo = new MediaRecorder(fluxo, formato ? { mimeType: formato } : undefined);
    pedacos.current = [];
    novo.ondataavailable = (e) => e.data.size > 0 && pedacos.current.push(e.data);
    novo.onstop = () => {
      soltarMicrofone();
      const mime = novo.mimeType || formato || "audio/webm";
      const arquivo = pedacos.current.length ? new File(pedacos.current, nomeDoArquivo(mime), { type: mime }) : null;
      pedacos.current = [];
      const destino = aoTerminar.current;
      aoTerminar.current = null;
      if (destino) {
        setEstado("parado");
        destino(arquivo);
        return;
      }
      ultimoArquivo.current = arquivo;
      setEstado("pronto");
    };
    gravador.current = novo;
    novo.start(1000);
    setSegundos(0);
    setEstado("gravando");
    relogio.current = setInterval(() => setSegundos((s) => Math.min(s + 1, LIMITE_SEGUNDOS)), 1000);
  }, [onErro, soltarMicrofone]);

  // Os 5 minutos: para sozinha e espera o "Enviar" (FR-012).
  useEffect(() => {
    if (estado === "gravando" && segundos >= LIMITE_SEGUNDOS) parar();
  }, [estado, segundos, parar]);

  /** Para (se ainda grava) e entrega o arquivo; `null` quando não gravou nada. */
  const finalizar = useCallback(
    (destino: (arquivo: File | null) => void) => {
      if (gravador.current?.state === "recording") {
        aoTerminar.current = destino;
        gravador.current.stop();
        return;
      }
      const arquivo = ultimoArquivo.current;
      ultimoArquivo.current = null;
      setEstado("parado");
      destino(arquivo);
    },
    [],
  );

  const cancelar = useCallback(() => {
    aoTerminar.current = () => undefined;
    if (gravador.current?.state === "recording") gravador.current.stop();
    else soltarMicrofone();
    ultimoArquivo.current = null;
    setEstado("parado");
  }, [soltarMicrofone]);

  return { estado, segundos, iniciar, finalizar, cancelar, disponivel: typeof MediaRecorder !== "undefined" };
}

interface BarraDeGravacaoProps {
  estado: EstadoDaGravacao;
  segundos: number;
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: () => void;
}

/** A barra que toma o lugar do campo enquanto grava: tempo correndo, "Cancelar" e "Enviar". */
export function BarraDeGravacao({ estado, segundos, enviando, onCancelar, onEnviar }: BarraDeGravacaoProps) {
  const reduzir = useReducedMotion();
  return (
    <div className="flex items-center gap-2" role="group" aria-label="Gravação de áudio">
      <Button
        type="button"
        variant="outline"
        className="h-11 shrink-0"
        onClick={onCancelar}
        disabled={enviando}
        aria-label="Cancelar a gravação"
      >
        <X className="h-5 w-5" aria-hidden />
        <span className="hidden sm:inline">Cancelar</span>
      </Button>
      <div className="flex min-h-11 flex-1 items-center gap-2 rounded-md border border-line bg-surface px-3 text-sm">
        {estado === "gravando" ? (
          <motion.span
            aria-hidden
            className="h-2.5 w-2.5 rounded-full bg-red"
            animate={reduzir ? undefined : { opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
        ) : (
          <Mic className="h-4 w-4 text-muted" aria-hidden />
        )}
        <span aria-live="polite" className="tabular-nums">
          {tempoDaGravacao(segundos)}
        </span>
        <span className="truncate text-xs text-muted">
          {estado === "gravando" ? "Gravando…" : "Gravação parada em 5 minutos."}
        </span>
      </div>
      <Button type="button" className="h-11 shrink-0" onClick={onEnviar} loading={enviando} aria-label="Enviar o áudio">
        {enviando ? "Enviando…" : <Send className="h-5 w-5" aria-hidden />}
      </Button>
    </div>
  );
}
