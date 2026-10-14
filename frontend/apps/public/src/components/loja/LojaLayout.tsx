import { useEffect, type ReactNode } from "react";
import { Outlet } from "react-router-dom";
import { RODAPE, TITULO_LOJA } from "../../lib/lojaTema";

/**
 * Moldura das três páginas da loja de conversas (`/v`, `/v/:slug`, `/v/pedido/:token`) — feature
 * 304.
 *
 * O `body` do app público é creme (`index.css`, catálogo de festa). Pintar só este `div` deixaria
 * a faixa creme aparecer no "puxa para baixo" do iPhone e atrás da barra do navegador; por isso a
 * classe vai no `<html>` enquanto a loja está montada, e sai quando a pessoa navega para fora.
 */
export function LojaLayout() {
  useEffect(() => {
    const raiz = document.documentElement;
    const tituloAnterior = document.title;
    raiz.classList.add("tema-alo");
    document.title = TITULO_LOJA;
    return () => {
      raiz.classList.remove("tema-alo");
      document.title = tituloAnterior;
    };
  }, []);

  return (
    <div className="min-h-screen bg-alo-bg bg-alo-glow bg-no-repeat text-alo-ink">
      <Outlet />
      <footer className="mx-auto max-w-lg px-4 pb-10 pt-4 text-center">
        <Ornamento />
        <p className="mt-3 text-[12px] uppercase tracking-[0.25em] text-alo-muted">{RODAPE}</p>
      </footer>
    </div>
  );
}

/** A linha fina com estrela no meio que separa os blocos nas artes de Natal. */
export function Ornamento({ className = "" }: { className?: string }) {
  return (
    <div aria-hidden="true" className={`flex items-center justify-center gap-3 ${className}`}>
      <span className="h-px w-16 bg-gradient-to-r from-transparent to-alo-gold/70" />
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-alo-gold">
        <path d="M12 0c.6 6.2 5.8 11.4 12 12-6.2.6-11.4 5.8-12 12-.6-6.2-5.8-11.4-12-12C6.2 11.4 11.4 6.2 12 0z" />
      </svg>
      <span className="h-px w-16 bg-gradient-to-l from-transparent to-alo-gold/70" />
    </div>
  );
}

/** Rótulo de seção: caixa alta espaçada em dourado, como "RESERVAS ABERTAS PARA O NATAL". */
export function TituloSecao({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-[12px] font-semibold uppercase tracking-[0.22em] text-alo-gold">
      {children}
    </h2>
  );
}

/**
 * Classes do botão principal: vermelho veludo com contorno dourado. O contorno não é enfeite —
 * o vermelho sozinho dá 1,9:1 sobre o verde e o botão se perderia na página.
 */
export const BOTAO_PRINCIPAL =
  "flex min-h-[48px] w-full items-center justify-center rounded-full border border-alo-gold/80 " +
  "bg-alo-red px-5 text-[15px] font-bold text-alo-on-red shadow-[0_8px_24px_rgba(0,0,0,0.35)] " +
  "transition-colors hover:bg-alo-red-hover disabled:opacity-60";

/** Botão secundário (WhatsApp, voltar): contorno dourado sobre o verde. */
export const BOTAO_SECUNDARIO =
  "flex min-h-[44px] w-full items-center justify-center rounded-full border border-alo-line-strong " +
  "px-5 py-2 text-center text-[15px] text-alo-ink transition-colors hover:bg-alo-surface";

/** Campo de formulário sobre o verde. `invalido` troca o contorno pelo vermelho-claro de erro. */
export function classeCampo(invalido: boolean): string {
  return (
    "min-h-[44px] w-full rounded-lg border bg-alo-surface px-3 text-[15px] text-alo-ink " +
    "placeholder:text-alo-muted/70 focus:outline-none focus:ring-2 focus:ring-alo-gold " +
    (invalido ? "border-alo-error" : "border-alo-line-strong")
  );
}
