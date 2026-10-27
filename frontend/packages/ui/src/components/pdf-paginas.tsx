import { useEffect, useRef, useState } from "react";
import { GlobalWorkerOptions, getDocument, type PDFDocumentProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Skeleton } from "./skeleton";

/**
 * Páginas de um PDF desenhadas pelo pdf.js (feature 320) — só é carregado quando um PDF abre no
 * `VisualizadorDeArquivo` (`React.lazy`), então não pesa em tela nenhuma que não abra PDF.
 *
 * Por que não `<iframe>`: o Safari do iPhone mostra PDF embutido sem rolagem confiável e às vezes só
 * a primeira página — e o iPhone, com o sistema na Tela de Início, é justamente onde a equipe abre
 * comprovante. Desenhado em `<canvas>`, o PDF sai igual no iPhone e no computador.
 */

GlobalWorkerOptions.workerSrc = workerUrl;

/** Acima de 2x o canvas pesa na memória do iPhone sem ganho visível. */
const DENSIDADE_MAXIMA = 2;
/** Largura máxima da página no computador: mais que isso só aumenta o PDF sem ajudar a leitura. */
const LARGURA_MAXIMA = 900;
/** Começa a desenhar a página um pouco antes de ela chegar na tela. */
const MARGEM_DE_ANTECIPACAO = "800px";

interface PdfPaginasProps {
  url: string;
  onErro: () => void;
}

export default function PdfPaginas({ url, onErro }: PdfPaginasProps) {
  const caixa = useRef<HTMLDivElement>(null);
  const [documento, setDocumento] = useState<PDFDocumentProxy | null>(null);
  const [proporcao, setProporcao] = useState(1.414);
  const [largura, setLargura] = useState(0);

  useEffect(() => {
    const tarefa = getDocument({ url });
    let vivo = true;
    tarefa.promise
      .then(async (doc) => {
        const primeira = await doc.getPage(1);
        const vp = primeira.getViewport({ scale: 1 });
        if (!vivo) return;
        setProporcao(vp.height / vp.width);
        setDocumento(doc);
      })
      .catch(() => {
        if (vivo) onErro();
      });
    return () => {
      vivo = false;
      void tarefa.destroy();
    };
    // `onErro` muda a cada render do pai; o documento só depende do endereço.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  useEffect(() => {
    if (caixa.current) setLargura(Math.min(caixa.current.clientWidth, LARGURA_MAXIMA));
  }, []);

  return (
    <div ref={caixa} className="mx-auto flex w-full max-w-[900px] flex-col items-center gap-3">
      {!documento || largura === 0 ? (
        <Skeleton className="w-full" style={{ height: Math.max(largura, 320) * proporcao }} />
      ) : (
        Array.from({ length: documento.numPages }, (_, i) => (
          <Pagina
            key={i}
            documento={documento}
            numero={i + 1}
            largura={largura}
            proporcao={proporcao}
            onErro={onErro}
          />
        ))
      )}
    </div>
  );
}

interface PaginaProps {
  documento: PDFDocumentProxy;
  numero: number;
  largura: number;
  proporcao: number;
  onErro: () => void;
}

function Pagina({ documento, numero, largura, proporcao, onErro }: PaginaProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [perto, setPerto] = useState(numero === 1);
  const [desenhada, setDesenhada] = useState(false);

  useEffect(() => {
    if (perto || !canvas.current) return;
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((e) => e.isIntersecting)) setPerto(true);
      },
      { rootMargin: MARGEM_DE_ANTECIPACAO },
    );
    observador.observe(canvas.current);
    return () => observador.disconnect();
  }, [perto]);

  useEffect(() => {
    if (!perto || !canvas.current) return;
    let vivo = true;
    let cancelar: (() => void) | null = null;
    documento
      .getPage(numero)
      .then((pagina) => {
        if (!vivo || !canvas.current) return;
        const base = pagina.getViewport({ scale: 1 });
        const vp = pagina.getViewport({ scale: largura / base.width });
        const densidade = Math.min(window.devicePixelRatio || 1, DENSIDADE_MAXIMA);
        const el = canvas.current;
        el.width = Math.floor(vp.width * densidade);
        el.height = Math.floor(vp.height * densidade);
        el.style.width = `${Math.floor(vp.width)}px`;
        el.style.height = `${Math.floor(vp.height)}px`;
        const contexto = el.getContext("2d");
        if (!contexto) return;
        const tarefa = pagina.render({
          canvasContext: contexto,
          viewport: vp,
          transform: densidade === 1 ? undefined : [densidade, 0, 0, densidade, 0, 0],
        });
        cancelar = () => tarefa.cancel();
        return tarefa.promise.then(() => {
          if (vivo) setDesenhada(true);
        });
      })
      .catch((erro: { name?: string }) => {
        if (vivo && erro?.name !== "RenderingCancelledException") onErro();
      });
    return () => {
      vivo = false;
      cancelar?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perto, documento, numero, largura]);

  return (
    <div className="relative w-full" style={{ maxWidth: largura }}>
      {!desenhada && (
        <Skeleton className="absolute inset-0" style={{ height: largura * proporcao }} />
      )}
      <canvas
        ref={canvas}
        aria-label={`Página ${numero} de ${documento.numPages}`}
        className="block bg-white shadow-sm"
        style={{ width: largura, height: largura * proporcao }}
      />
    </div>
  );
}
