import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CalendarX, ChevronDown } from "lucide-react";
import { cn, formatShortDate } from "@manto/ui";
import { useSumidosGoogle } from "../lib/sumidosGoogle";

/** `dd/mm/aaaa`, ou `sem data` — `formatShortDate(null)` devolveria "—". */
function dataDoEvento(iso: string | null): string {
  return iso ? formatShortDate(iso) : "sem data";
}

const FOCO = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset";

/**
 * Faixa fixa no topo de toda tela do sistema interno (feature 303): quantos eventos sumiram do
 * Google Agenda e foram mantidos no sistema. Para Superadmin e Comercial — quem decide é o
 * `pode_ver` do servidor; o componente é montado para todo usuário no `AppShell`.
 *
 * Dois níveis, de propósito: o wrapper `sticky` não tem overflow (sempre montado); dentro, a barra
 * anima a altura (0 ↔ 40 px), o que exige `overflow-hidden` — por isso a lista de vários eventos é
 * IRMÃ da barra, ancorada no wrapper, senão seria cortada. Altura fixa é o que deixa a régua de
 * abas do evento e as âncoras da Home somarem a faixa por classe.
 *
 * `z-[25]`: acima da régua de abas do evento (`z-20`), abaixo da barra do mobile e do painel do
 * sino (`z-30`). Sem botão de dispensar: a faixa só some quando a marca sai.
 */
export function FaixaSumidosGoogle() {
  const { data } = useSumidosGoogle();
  const reduceMotion = useReducedMotion();
  const [aberto, setAberto] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);
  const listaId = useId();

  const total = data?.pode_ver ? data.total : 0;
  const itens = data?.items ?? [];
  const visivel = total > 0;
  const unico = total === 1 && itens.length === 1 ? itens[0] : null;
  const frase =
    total === 1 ? "1 evento sumiu do Google Agenda" : `${total} eventos sumiram do Google Agenda`;

  const fechar = useCallback(() => {
    setAberto(false);
    botaoRef.current?.focus();
  }, []);

  // A lista não sobrevive à faixa sumir ou virar link direto (o poll pode mudar isso aberto).
  useEffect(() => {
    if (!visivel || unico) setAberto(false);
  }, [visivel, unico]);

  // Fecha em clique fora e Esc, devolvendo o foco ao botão — o contrato do sino.
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
    <div ref={rootRef} className="sticky top-14 z-[25] lg:top-0">
      <AnimatePresence initial={false}>
        {visivel && (
          <motion.div
            key="faixa"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 40, opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex h-10 items-center bg-red px-4 text-sm font-medium text-on-color">
              {unico ? (
                <Link
                  to={`/events/${unico.id}`}
                  className={cn("flex h-full min-w-0 flex-1 items-center gap-2", FOCO, "focus-visible:ring-on-color")}
                >
                  <CalendarX aria-hidden className="h-4 w-4 shrink-0" />
                  <span role="alert" className="whitespace-nowrap">
                    {frase}
                  </span>
                  <span className="hidden min-w-0 truncate font-normal sm:inline">
                    — {unico.title}
                  </span>
                  <span className="hidden shrink-0 whitespace-nowrap font-normal tabular-nums sm:inline">
                    · {dataDoEvento(unico.start_at)}
                  </span>
                </Link>
              ) : (
                <button
                  ref={botaoRef}
                  type="button"
                  aria-expanded={aberto}
                  aria-controls={listaId}
                  onClick={() => setAberto((a) => !a)}
                  className={cn("flex h-full min-w-0 flex-1 items-center gap-2 text-left", FOCO, "focus-visible:ring-on-color")}
                >
                  <CalendarX aria-hidden className="h-4 w-4 shrink-0" />
                  <span role="alert" className="whitespace-nowrap">
                    {frase}
                  </span>
                  <ChevronDown
                    aria-hidden
                    className={cn("h-4 w-4 shrink-0 transition-transform", aberto && "rotate-180")}
                  />
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {visivel && !unico && aberto && (
          <motion.div
            key="lista"
            id={listaId}
            initial={reduceMotion ? false : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: "easeOut" }}
            className="absolute inset-x-0 top-full max-h-[60vh] overflow-y-auto border-b border-line bg-panel shadow-lg"
          >
            <ul className="divide-y divide-line">
              {itens.map((item) => (
                <li key={item.id}>
                  <Link
                    to={`/events/${item.id}`}
                    title={item.title}
                    onClick={() => setAberto(false)}
                    className={cn(
                      "flex min-h-11 items-center gap-3 px-4 py-2 text-sm hover:bg-surface-2",
                      FOCO,
                      "focus-visible:ring-accent",
                    )}
                  >
                    <span className="min-w-0 flex-1 truncate text-ink">{item.title}</span>
                    <span className="shrink-0 tabular-nums text-muted">
                      {dataDoEvento(item.start_at)}
                    </span>
                  </Link>
                </li>
              ))}
              {total > itens.length && (
                <li className="px-4 py-2 text-sm text-muted">e mais {total - itens.length}</li>
              )}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
