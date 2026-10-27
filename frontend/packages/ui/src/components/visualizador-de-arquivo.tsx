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

      <div className="min-h-0 flex-1 overflow-auto overscroll-contain bg-surface-2 p-3 sm:p-6">
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
            className="mx-auto h-auto max-w-full rounded-md bg-white shadow-sm"
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

/**
 * No celular, "Baixar" abre a folha de compartilhar do aparelho (Salvar em Arquivos, Fotos,
 * WhatsApp). Um `<a download>` no app da Tela de Início pode abrir o arquivo na própria janela —
 * a armadilha de novo. No computador, download comum.
 */
function BotaoBaixar({ arquivo, nome }: { arquivo: ArquivoParaVisualizar; nome: string }) {
  const [baixando, setBaixando] = useState(false);

  async function baixar() {
    const toque = window.matchMedia?.("(pointer: coarse)").matches ?? false;
    if (toque && typeof navigator.canShare === "function") {
      setBaixando(true);
      try {
        const resposta = await fetch(arquivo.url, { credentials: "same-origin" });
        if (resposta.ok) {
          const blob = await resposta.blob();
          const file = new File([blob], nome, { type: blob.type });
          if (navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file] });
            return;
          }
        }
      } catch (e) {
        // Cancelar a folha de compartilhar não é erro.
        if (e instanceof DOMException && e.name === "AbortError") return;
      } finally {
        setBaixando(false);
      }
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
    <Button variant="outline" loading={baixando} onClick={() => void baixar()} className="px-3">

      <Download className="h-4 w-4" aria-hidden="true" />
      Baixar
    </Button>
  );
}
