import { useEffect, useRef, useState, type ReactNode } from "react";

export interface FotoProps {
  /** URL já resolvida (use `assetUrl()` antes de passar). Vazia/`null` cai direto no fallback. */
  src?: string | null;
  srcSet?: string;
  sizes?: string;
  /** Texto alternativo. `""` quando o container ao redor já é `aria-hidden`. */
  alt: string;
  /** O que desenhar quando não há foto — ou quando a foto existe no banco e some do disco. */
  fallback: ReactNode;
  className?: string;
  loading?: "lazy" | "eager";
}

/**
 * `<img>` que sabe cair (feature 292).
 *
 * O `<img>` do navegador não tem estado de erro visível: quando o `src` responde 404, ele desenha
 * o ícone de imagem quebrada e pronto. Isso deixou de ser teórico na migração para o Render —
 * centenas de linhas do banco apontam para arquivos que não voltaram do volume antigo, e cada uma
 * virava um quadrado cinza numa tela de trabalho.
 *
 * **O `onError` do React sozinho não resolve, e isso foi medido na tela.** O evento `error` de
 * imagem não borbulha, e o React o escuta na raiz da aplicação; quando o erro acontece enquanto o
 * elemento ainda está sendo criado — o caso comum, porque o navegador guarda o 404 e responde de
 * imediato na segunda visita — não há caminho até a raiz e o evento se perde. Na prática: a
 * primeira visita mostrava as iniciais e a segunda voltava a mostrar o quadrado quebrado.
 *
 * Por isso a decisão fica num efeito, depois da pintura, com duas redes: se a imagem **já**
 * terminou e não é imagem (`complete` com `naturalWidth === 0`), marca na hora; se ainda está
 * carregando, um ouvinte **no próprio elemento** pega o erro sem depender de borbulhamento.
 *
 * O estado guarda a URL que falhou, não um booleano: trocar de talento no combobox muda o `src`,
 * `urlQuebrada !== src` volta a ser verdade, e a imagem nova é tentada sozinha.
 */
export function Foto({ src, fallback, ...resto }: FotoProps) {
  const [urlQuebrada, setUrlQuebrada] = useState<string | null>(null);
  const ref = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !src) return;
    const marcar = () => setUrlQuebrada(src);
    // Se a imagem JÁ terminou e não é imagem, decide agora; senão, escuta no próprio elemento.
    if (el.complete && el.naturalWidth === 0) {
      marcar();
      return;
    }
    el.addEventListener("error", marcar);
    return () => el.removeEventListener("error", marcar);
  }, [src]);

  if (!src || urlQuebrada === src) return <>{fallback}</>;

  // `key` por URL: elemento novo a cada foto, para o efeito acima nunca julgar o `complete` da
  // imagem anterior.
  return <img key={src} ref={ref} src={src} onError={() => setUrlQuebrada(src)} {...resto} />;
}
