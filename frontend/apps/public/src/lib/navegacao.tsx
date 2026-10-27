import { forwardRef, useLayoutEffect, useRef } from "react";
import { Link, useLocation, useNavigate, useNavigationType, type LinkProps } from "react-router-dom";

/**
 * Navegação "voltar sem perder o lugar" (feature 320). Gêmeo de
 * `apps/internal/src/lib/navegacao.tsx` — o `@manto/ui` não depende do roteador, então o que precisa
 * dele mora em cada app.
 */

/** Marca posta no `state` dos links lista → tema: "a pessoa veio da lista". */
export const DA_LISTA = { daLista: true } as const;

function veioDaLista(state: unknown): boolean {
  return Boolean(state && typeof state === "object" && (state as { daLista?: boolean }).daLista);
}

/**
 * Para os "← Voltar": quem veio da lista volta pelo histórico (busca e categoria no endereço,
 * rolagem pela chave da entrada); quem chegou por link direto vai para o início da lista.
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
 * Link "← Voltar" com `useVoltarParaLista`. O `href` aponta para a lista (Ctrl/⌘-clique abre em
 * outra aba); o clique simples volta pelo histórico quando dá.
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

/** A chegada atual foi um "voltar"/"avançar" do histórico (e não um clique em link)? */
export function useChegouPeloHistorico(): boolean {
  return useNavigationType() === "POP";
}

/**
 * Navegação NOVA para outra página começa do topo — sem isto o tema abria na rolagem da grade.
 * Montado ANTES das `<Routes>`: o detalhe que rola até um personagem (`?personagem=`) roda depois.
 */
export function RolarAoTopoEmNovaPagina() {
  const { pathname } = useLocation();
  const tipo = useNavigationType();
  const anterior = useRef(pathname);
  useLayoutEffect(() => {
    if (pathname !== anterior.current && tipo !== "POP") window.scrollTo(0, 0);
    anterior.current = pathname;
  }, [pathname, tipo]);
  return null;
}
