import {
  createContext,
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type AnchorHTMLAttributes,
  type MouseEvent,
  type ReactNode,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { VisualizadorDeArquivo, type ArquivoParaVisualizar } from "@manto/ui";

/**
 * Todo arquivo do sistema abre aqui dentro (feature 320) — comprovante, nota, contrato, documento.
 *
 * Abrir faz um PUSH do MESMO endereço com uma marca no `state`; assim o voltar do navegador (e o
 * gesto do iPhone) fecha o visualizador em vez de sair da tela, e o "Voltar" do visualizador é só
 * `navigate(-1)`. O arquivo aberto vive no estado do React, não no histórico: recarregar a página
 * não reabre nada, e a marca que sobrou é limpa.
 */

type MarcaNoHistorico = { arquivoAberto?: number } & Record<string, unknown>;

const AbrirArquivoContext = createContext<((arquivo: ArquivoParaVisualizar) => void) | null>(null);

function marcaDe(state: unknown): number | undefined {
  return state && typeof state === "object" ? (state as MarcaNoHistorico).arquivoAberto : undefined;
}

function semMarca(state: unknown): unknown {
  if (!state || typeof state !== "object") return state;
  const { arquivoAberto: _fora, ...resto } = state as MarcaNoHistorico;
  return Object.keys(resto).length ? resto : null;
}

export function ArquivoViewerProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [aberto, setAberto] = useState<{ marca: number; arquivo: ArquivoParaVisualizar } | null>(null);
  const proximaMarca = useRef(1);
  const algumAberto = useRef(false);
  const marcaAtual = marcaDe(location.state);
  if (!aberto) algumAberto.current = false;

  // Voltar do navegador/gesto: a marca saiu do histórico → fecha.
  useEffect(() => {
    if (aberto && marcaAtual !== aberto.marca) setAberto(null);
  }, [aberto, marcaAtual]);

  // Recarregou com a marca no histórico: não há arquivo para mostrar. Tira a marca (senão o
  // próximo "Ver" acharia que já há um aberto); a entrada repetida da mesma tela continua lá — um
  // "voltar" a mais, que o histórico do navegador não deixa apagar.
  const conferiuNaMontagem = useRef(false);
  useEffect(() => {
    if (conferiuNaMontagem.current) return;
    conferiuNaMontagem.current = true;
    if (marcaAtual !== undefined) {
      navigate(location, { replace: true, state: semMarca(location.state) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const abrir = useCallback(
    (arquivo: ArquivoParaVisualizar) => {
      // Toque duplo no "Ver" não empilha dois passos de "voltar" (ref, não estado: o segundo
      // toque chega antes de a tela renderizar de novo).
      if (algumAberto.current) return;
      algumAberto.current = true;
      const marca = proximaMarca.current++;
      setAberto({ marca, arquivo });
      const base = location.state && typeof location.state === "object" ? location.state : {};
      navigate(location, { state: { ...base, arquivoAberto: marca } });
    },
    [location, navigate],
  );

  const fechar = useCallback(() => {
    if (aberto && marcaAtual === aberto.marca) navigate(-1);
    else setAberto(null);
  }, [aberto, marcaAtual, navigate]);

  return (
    <AbrirArquivoContext.Provider value={abrir}>
      {children}
      <VisualizadorDeArquivo arquivo={aberto?.arquivo ?? null} onFechar={fechar} />
    </AbrirArquivoContext.Provider>
  );
}

export function useAbrirArquivo(): (arquivo: ArquivoParaVisualizar) => void {
  const abrir = useContext(AbrirArquivoContext);
  if (!abrir) throw new Error("useAbrirArquivo fora do ArquivoViewerProvider");
  return abrir;
}

function ehDeOutroSite(url: string): boolean {
  if (!/^https?:\/\//i.test(url)) return false;
  try {
    return new URL(url).origin !== window.location.origin;
  } catch {
    return true;
  }
}

export interface LinkDeArquivoProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  /** Caminho do Flask (`/uploads/...` ou relativo) ou URL absoluta. */
  caminho: string;
  /** Título na barra do visualizador; sem ele, o nome do arquivo. */
  nome?: string;
}

/**
 * Link de arquivo do sistema: clique abre o visualizador. Mantém o `href` de verdade para
 * Ctrl/⌘-clique e clique do meio (abrir em outra aba no computador continua possível). Link de
 * outro site (comprovante da InfinitePay, material em link) segue como link comum em outra aba.
 */
export const LinkDeArquivo = forwardRef<HTMLAnchorElement, LinkDeArquivoProps>(function LinkDeArquivo(
  { caminho, nome, onClick, children, ...props },
  ref,
) {
  const abrir = useAbrirArquivo();
  const url = assetUrl(caminho) ?? caminho;

  if (ehDeOutroSite(url)) {
    return (
      <a ref={ref} href={url} target="_blank" rel="noopener noreferrer" onClick={onClick} {...props}>
        {children}
      </a>
    );
  }

  const aoClicar = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    abrir({ url, nome });
  };

  return (
    <a ref={ref} href={url} onClick={aoClicar} {...props}>
      {children}
    </a>
  );
});
