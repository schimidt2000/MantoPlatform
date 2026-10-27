import { Suspense, lazy, useEffect, useRef, useState, type ReactNode } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Download, FileQuestion, TriangleAlert } from "lucide-react";
import { Button } from "./button";
import { Skeleton } from "./skeleton";

/**
 * Visualizador de arquivo em tela cheia (feature 320).
 *
 * Nasceu do iPhone: com o sistema aberto pelo ícone da Tela de Início não existe barra nem botão
 * de voltar, e o comprovante que abria "em outra aba" prendia a pessoa — ela precisava fechar o
 * app. Aqui o arquivo abre POR CIMA da tela, com "Voltar" sempre à vista (fora da área que rola).
 *
 * Só apresentação: quem liga o "Voltar" ao histórico do navegador é o app (no interno,
 * `ArquivoViewerProvider`). z-[60] para ficar acima do `Dialog` (z-50) e do `Modal` do interno —
 * "Ver comprovante" também existe dentro de diálogo.
 */

const PdfPaginas = lazy(() => import("./pdf-paginas"));

export type TipoDeArquivo = "imagem" | "pdf" | "outro";

const EXTENSOES_DE_IMAGEM = new Set(["jpg", "jpeg", "png", "webp", "gif", "heic", "heif", "avif"]);

/** Tipo pela extensão do caminho (sem query nem âncora). */
export function tipoDeArquivo(url: string): TipoDeArquivo {
  const caminho = url.split(/[?#]/)[0] ?? "";
  const extensao = caminho.slice(caminho.lastIndexOf(".") + 1).toLowerCase();
  if (extensao === "pdf") return "pdf";
  return EXTENSOES_DE_IMAGEM.has(extensao) ? "imagem" : "outro";
}

function nomeDoArquivo(arquivo: ArquivoParaVisualizar): string {
  if (arquivo.nome) return arquivo.nome;
  const caminho = arquivo.url.split(/[?#]/)[0] ?? "";
  return decodeURIComponent(caminho.slice(caminho.lastIndexOf("/") + 1)) || "arquivo";
}

export interface ArquivoParaVisualizar {
  /** Endereço já resolvido (`assetUrl`). */
  url: string;
  /** Título na barra; sem ele, o nome do arquivo. */
  nome?: string;
}

export interface VisualizadorDeArquivoProps {
  /** `null` = fechado. */
  arquivo: ArquivoParaVisualizar | null;
  /** "Voltar", Esc ou toque fora da área do arquivo. */
  onFechar: () => void;
}

export function VisualizadorDeArquivo({ arquivo, onFechar }: VisualizadorDeArquivoProps) {
  const reduceMotion = useReducedMotion();
  // Mantém o último arquivo durante a animação de saída (o pai já mandou `null`).
  const ultimo = useRef<ArquivoParaVisualizar | null>(null);
  if (arquivo) ultimo.current = arquivo;
  const atual = arquivo ?? ultimo.current;
  // Sem `Trigger`, o Radix não sabe para onde devolver o foco ao fechar e larga no `body`: guarda
  // quem tinha o foco (o "Ver") no momento em que o visualizador abriu.
  const origem = useRef<HTMLElement | null>(null);
  const estavaAberto = useRef(false);
  if (arquivo && !estavaAberto.current && typeof document !== "undefined") {
    origem.current = document.activeElement as HTMLElement | null;
  }
  estavaAberto.current = arquivo !== null;

  return (
    <DialogPrimitive.Root open={arquivo !== null} onOpenChange={(aberto) => !aberto && onFechar()}>
      <AnimatePresence>
        {arquivo && atual && (
          <DialogPrimitive.Portal forceMount>
            <DialogPrimitive.Content
              asChild
              forceMount
              aria-describedby={undefined}
              data-visualizador-arquivo=""
              onCloseAutoFocus={(e) => {
                e.preventDefault();
                origem.current?.focus();
              }}
            >
              <motion.div
                className="fixed inset-0 z-[60] flex flex-col bg-bg focus:outline-none"
                initial={reduceMotion ? undefined : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: 12 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                <Conteudo arquivo={atual} onFechar={onFechar} />
              </motion.div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        )}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}

function Conteudo({ arquivo, onFechar }: { arquivo: ArquivoParaVisualizar; onFechar: () => void }) {
  const tipo = tipoDeArquivo(arquivo.url);
  const nome = nomeDoArquivo(arquivo);
  const [erro, setErro] = useState(false);
  // "Tentar novamente" remonta a foto/PDF com uma chave nova.
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    setErro(false);
    setTentativa(0);
  }, [arquivo.url]);

  return (
    <>
      <header className="flex shrink-0 items-center gap-2 border-b border-line bg-panel px-2 py-2 sm:px-4">
        <Button variant="ghost" onClick={onFechar} className="px-3">
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
          Voltar
        </Button>
        <DialogPrimitive.Title className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
          {nome}
        </DialogPrimitive.Title>
        <BotaoBaixar arquivo={arquivo} nome={nome} />
      </header>

      <div
        data-rolagem-do-visualizador=""
        className="min-h-0 flex-1 overflow-auto overscroll-contain bg-surface-2 p-3 sm:p-6"
      >
        {erro ? (
          <Aviso
            icone={<TriangleAlert className="h-8 w-8 text-red" aria-hidden="true" />}
            texto="Não foi possível abrir o arquivo. Tente novamente."
          >
            <Button
              variant="outline"
              onClick={() => {
                setErro(false);
                setTentativa((t) => t + 1);
              }}
            >
              Tentar novamente
            </Button>
          </Aviso>
        ) : tipo === "imagem" ? (
          <img
            key={tentativa}
            src={arquivo.url}
            alt={nome}
            onError={() => setErro(true)}
            // Inteira na tela (retrato alto inclusive); o zoom é o de pinça do aparelho.
            className="mx-auto max-h-full max-w-full rounded-md bg-white object-contain shadow-sm"
          />
        ) : tipo === "pdf" ? (
          <Suspense fallback={<Skeleton className="mx-auto h-[70vh] w-full max-w-[900px]" />}>
            <PdfPaginas key={tentativa} url={arquivo.url} onErro={() => setErro(true)} />
          </Suspense>
        ) : (
          <Aviso
            icone={<FileQuestion className="h-8 w-8 text-muted" aria-hidden="true" />}
            texto="Este tipo de arquivo não tem prévia. Baixe o arquivo para abrir."
          >
            <BotaoBaixar arquivo={arquivo} nome={nome} />
          </Aviso>
        )}
      </div>
    </>
  );
}

function Aviso({ icone, texto, children }: { icone: ReactNode; texto: string; children: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center gap-3 py-16 text-center">
      {icone}
      <p className="text-sm text-ink">{texto}</p>
      {children}
    </div>
  );
}

/** Tela de toque com folha de compartilhar de arquivo (iPhone, Android)? */
function podeCompartilharArquivo(): boolean {
  if (typeof window === "undefined" || typeof navigator.canShare !== "function") return false;
  return window.matchMedia?.("(pointer: coarse)").matches ?? false;
}

/**
 * No celular, "Baixar" abre a folha de compartilhar do aparelho (Salvar em Arquivos, Fotos,
 * WhatsApp). Um `<a download>` no app da Tela de Início pode abrir o arquivo na própria janela —
 * a armadilha de novo. No computador, download comum.
 *
 * O arquivo é buscado quando o visualizador abre, não no toque: o Safari só aceita `share` chamado
 * direto do toque, e um `await fetch` antes faz ele recusar.
 */
function BotaoBaixar({ arquivo, nome }: { arquivo: ArquivoParaVisualizar; nome: string }) {
  const [compartilhar] = useState(podeCompartilharArquivo);
  const [pronto, setPronto] = useState<File | null>(null);
  const [preparando, setPreparando] = useState(compartilhar);

  useEffect(() => {
    if (!compartilhar) return;
    let vivo = true;
    setPronto(null);
    setPreparando(true);
    fetch(arquivo.url, { credentials: "same-origin" })
      .then((resposta) => (resposta.ok ? resposta.blob() : Promise.reject(new Error(String(resposta.status)))))
      .then((blob) => {
        if (vivo) setPronto(new File([blob], nome, { type: blob.type }));
      })
      .catch(() => {
        // Sem o arquivo em mãos, o toque cai no download comum (abaixo).
      })
      .finally(() => {
        if (vivo) setPreparando(false);
      });
    return () => {
      vivo = false;
    };
  }, [arquivo.url, nome, compartilhar]);

  function baixar() {
    if (pronto && navigator.canShare({ files: [pronto] })) {
      // Cancelar a folha não é erro; e nenhum erro aqui pode cair no `<a download>`, que no app
      // da Tela de Início prenderia a pessoa.
      navigator.share({ files: [pronto] }).catch(() => undefined);
      return;
    }
    const link = document.createElement("a");
    link.href = arquivo.url;
    link.download = nome;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  return (
    // Tamanho padrão (44px): é alvo de toque no celular.
    <Button variant="outline" loading={preparando} onClick={baixar} className="px-3">
      <Download className="h-4 w-4" aria-hidden="true" />
      Baixar
    </Button>
  );
}
