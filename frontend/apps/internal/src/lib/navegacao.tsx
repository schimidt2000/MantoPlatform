import { forwardRef, useLayoutEffect, useRef } from "react";
import { Link, useLocation, useNavigate, useNavigationType, type LinkProps } from "react-router-dom";

/**
 * Navegação "voltar sem perder o lugar" (feature 320). Gêmeo de `apps/public/src/lib/navegacao.tsx`
 * — o `@manto/ui` não depende do roteador, então o que precisa dele mora em cada app.
 */

/** Marca posta no `state` dos links lista → detalhe: "a pessoa veio da lista". */
export const DA_LISTA = { daLista: true } as const;

function veioDaLista(state: unknown): boolean {
  return Boolean(state && typeof state === "object" && (state as { daLista?: boolean }).daLista);
}

/**
 * Para os atalhos "Voltar" das páginas de detalhe: quem veio da lista volta pelo histórico (a
 * entrada da lista guarda filtros no endereço e a rolagem pela chave); quem chegou por link direto
 * ou de outra tela vai para o início da lista — o rótulo do atalho diz "lista", não "onde eu
 * estava".
 */
export function useVoltarParaLista(fallback: string): () => void {
  const location = useLocation();
  const navigate = useNavigate();
  return () => {
    if (veioDaLista(location.state)) navigate(-1);
    else navigate(fallback);
  };
}

/**
 * Link "‹ Voltar" com `useVoltarParaLista`. O `href` aponta para a lista (Ctrl/⌘-clique abre em
 * outra aba); o clique simples volta pelo histórico quando dá. Funciona com `<Button asChild>`.
 */
export const LinkVoltarParaLista = forwardRef<HTMLAnchorElement, Omit<LinkProps, "to"> & { to: string }>(
  function LinkVoltarParaLista({ to, onClick, ...props }, ref) {
    const voltar = useVoltarParaLista(to);
    return (
      <Link
        ref={ref}
        to={to}
        onClick={(e) => {
          onClick?.(e);
          if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          e.preventDefault();
          voltar();
        }}
        {...props}
      />
    );
  },
);

/**
 * Já houve navegação dentro deste carregamento do app? A primeira tela de um carregamento também
 * chega como "POP" no React Router — e não é um "voltar": abrir o app de novo numa lista não pode
 * devolver a rolagem de uma visita antiga.
 */
let houveNavegacao = false;

/** A chegada atual foi um "voltar"/"avançar" do histórico (e não um clique em link)? */
export function useChegouPeloHistorico(): boolean {
  return useNavigationType() === "POP" && houveNavegacao;
}

/**
 * Navegação NOVA para outra tela começa do topo. Sem isto a tela nova abria na rolagem da anterior
 * (o `BrowserRouter` não rola sozinho). Mesma tela com outro `?aba=`/filtro não sobe. Montado
 * ANTES das `<Routes>`: telas que rolam até um item ao abrir (`Tags3DPage`) rodam depois.
 */
export function RolarAoTopoEmNovaPagina() {
  const { pathname, key } = useLocation();
  const tipo = useNavigationType();
  const anterior = useRef(pathname);
  const chaveInicial = useRef(key);
  useLayoutEffect(() => {
    if (key !== chaveInicial.current) houveNavegacao = true;
    if (pathname !== anterior.current && tipo !== "POP") window.scrollTo(0, 0);
    anterior.current = pathname;
  }, [pathname, key, tipo]);
  return null;
}
