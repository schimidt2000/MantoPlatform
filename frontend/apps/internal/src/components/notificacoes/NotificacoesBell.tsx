import { useCallback, useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Bell } from "lucide-react";
import { useNaoLidas } from "../../lib/notificacoes";
import { NotificacoesPanel } from "./NotificacoesPanel";

/**
 * Sino de notificações do shell (feature 272) — entra pelo slot `headerActions` do `AppLayout`,
 * renderizado na linha da marca da sidebar (desktop) e na barra superior do mobile, FORA do
 * drawer: um sino escondido atrás do hambúrguer não avisa nada.
 *
 * As classes responsivas espelham os dois fundos: abaixo de `lg` o sino está na barra clara
 * (`text-ink`); a partir de `lg`, na sidebar escura (`text-white/70`). Só uma instância é visível
 * por vez, e as duas compartilham a mesma query (um request por poll).
 *
 * Passivo por desenho: sem toast, sem som. O anunciador `aria-live` só fala quando a contagem
 * SOBE em relação ao render anterior — anunciar a cada poll seria o e-mail em áudio.
 */
export function NotificacoesBell() {
  const [aberto, setAberto] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);
  const painelId = useId();
  const reduceMotion = useReducedMotion();

  const { data } = useNaoLidas();
  const count = data?.unread_count ?? 0;

  const anterior = useRef(0);
  const [anuncio, setAnuncio] = useState("");
  useEffect(() => {
    if (count > anterior.current) {
      setAnuncio(count === 1 ? "1 notificação não lida" : `${count} notificações não lidas`);
    }
    anterior.current = count;
  }, [count]);

  const fechar = useCallback(() => {
    setAberto(false);
    botaoRef.current?.focus();
  }, []);

  // Fecha em clique fora e Esc — mesmo contrato do KebabMenu/FilterDropdown.
  useEffect(() => {
    if (!aberto) return;
    function onMouseDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) fechar();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") fechar();
    }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [aberto, fechar]);

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={botaoRef}
        type="button"
        aria-label={count > 0 ? `Notificações, ${count} não lidas` : "Notificações"}
        aria-expanded={aberto}
        aria-controls={painelId}
        onClick={() => setAberto((o) => !o)}
        className="relative flex h-11 w-11 items-center justify-center rounded-md text-ink transition-colors hover:bg-surface-2 lg:h-9 lg:w-9 lg:text-white/70 lg:hover:bg-white/10 lg:hover:text-white"
      >
        <Bell className="h-5 w-5" aria-hidden />
        <AnimatePresence>
          {count > 0 && (
            // `key={count}`: a bolinha reanima quando o número muda, nunca a cada poll igual.
            // Contador sobre o acento sólido: `on-color`, como o do FilterDropdown.
            <motion.span
              key={count}
              initial={reduceMotion ? undefined : { scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={reduceMotion ? undefined : { scale: 0.6, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-on-color lg:right-0 lg:top-0"
              aria-hidden
            >
              {count > 9 ? "9+" : count}
            </motion.span>
          )}
        </AnimatePresence>
      </button>
      <span className="sr-only" aria-live="polite">
        {anuncio}
      </span>
      <NotificacoesPanel id={painelId} aberto={aberto} onFechar={fechar} />
    </div>
  );
}
