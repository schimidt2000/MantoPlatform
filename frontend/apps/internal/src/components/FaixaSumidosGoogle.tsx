import { type RefObject, useCallback, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CalendarX, ChevronDown, FileX, type LucideIcon } from "lucide-react";
import { cn, formatShortDate } from "@manto/ui";
import { type SumidoGoogle, useSumidosGoogle } from "../lib/sumidosGoogle";

/** `dd/mm/aaaa`, ou `sem data` — `formatShortDate(null)` devolveria "—". */
function dataDoEvento(iso: string | null): string {
  return iso ? formatShortDate(iso) : "sem data";
}

const FOCO = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset";

type QualLista = "sumidos" | "pedidos";

interface SegmentoProps {
  total: number;
  itens: SumidoGoogle[];
  /** A frase inteira (telas largas) e a curta (celular, quando os dois segmentos dividem a barra). */
  frase: string;
  fraseCurta: string;
  Icone: LucideIcon;
  tom: string;
  aberto: boolean;
  onAlternar: () => void;
  botaoRef: RefObject<HTMLButtonElement>;
  listaId: string;
}

/** Uma frase da faixa: 1 evento → link direto; N → botão que abre a lista (irmã da barra). */
function Segmento({ total, itens, frase, fraseCurta, Icone, tom, aberto, onAlternar, botaoRef, listaId }: SegmentoProps) {
  const unico = total === 1 && itens.length === 1 ? itens[0] : null;
  const texto = (
    <>
      <Icone aria-hidden className="h-4 w-4 shrink-0" />
      <span role="alert" className="min-w-0 truncate">
        <span className="sm:hidden">{fraseCurta}</span>
        <span className="hidden sm:inline">{frase}</span>
      </span>
    </>
  );
  return (
    <div className={cn("flex h-10 min-w-0 flex-1 items-center px-4 text-sm font-medium", tom)}>
      {unico ? (
        <Link
          to={`/events/${unico.id}`}
          className={cn("flex h-full min-w-0 flex-1 items-center gap-2", FOCO, "focus-visible:ring-current")}
        >
          {texto}
          <span className="hidden min-w-0 truncate font-normal lg:inline">— {unico.title}</span>
          <span className="hidden shrink-0 whitespace-nowrap font-normal tabular-nums lg:inline">
            · {dataDoEvento(unico.start_at)}
          </span>
        </Link>
      ) : (
        <button
          ref={botaoRef}
          type="button"
          aria-expanded={aberto}
          aria-controls={listaId}
          onClick={onAlternar}
          className={cn("flex h-full min-w-0 flex-1 items-center gap-2 text-left", FOCO, "focus-visible:ring-current")}
        >
          {texto}
          <ChevronDown aria-hidden className={cn("h-4 w-4 shrink-0 transition-transform", aberto && "rotate-180")} />
        </button>
      )}
    </div>
  );
}

/**
 * Faixa fixa no topo de toda tela do sistema interno: quantos eventos sumiram do Google Agenda e
 * foram mantidos (feature 303) e quantos pedidos de cancelamento aguardam o Superadmin (feature
 * 315). Para Superadmin e Comercial — quem decide é o `pode_ver` do servidor; o componente é
 * montado para todo usuário no `AppShell`. As duas frases dividem a mesma barra de 40 px, cada uma
 * com o seu botão e a sua lista.
 *
 * Dois níveis, de propósito: o wrapper `sticky` não tem overflow (sempre montado); dentro, a barra
 * anima a altura (0 ↔ 40 px), o que exige `overflow-hidden` — por isso as listas são IRMÃS da
 * barra, ancoradas no wrapper, senão seriam cortadas. Altura fixa é o que deixa a régua de abas do
 * evento e as âncoras da Home somarem a faixa por classe.
 *
 * `z-[25]`: acima da régua de abas do evento (`z-20`), abaixo da barra do mobile e do painel do
 * sino (`z-30`). Sem botão de dispensar: a faixa só some quando a marca sai e o pedido é decidido.
 */
export function FaixaSumidosGoogle() {
  const { data } = useSumidosGoogle();
  const reduceMotion = useReducedMotion();
  const [aberta, setAberta] = useState<QualLista | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const botaoSumidos = useRef<HTMLButtonElement>(null);
  const botaoPedidos = useRef<HTMLButtonElement>(null);
  const listaSumidos = useId();
  const listaPedidos = useId();

  const total = data?.pode_ver ? data.total : 0;
  const itens = data?.items ?? [];
  // Opcional: o backend de antes da 315 não manda a chave.
  const totalPedidos = data?.pode_ver ? (data.pedidos?.total ?? 0) : 0;
  const itensPedidos = data?.pedidos?.items ?? [];
  const visivel = total > 0 || totalPedidos > 0;

  const listas: Record<QualLista, { total: number; itens: SumidoGoogle[]; id: string }> = {
    sumidos: { total, itens, id: listaSumidos },
    pedidos: { total: totalPedidos, itens: itensPedidos, id: listaPedidos },
  };
  const lista = aberta ? listas[aberta] : null;
  const listaVale = lista !== null && lista.total > 0 && !(lista.total === 1 && lista.itens.length === 1);

  const fechar = useCallback(() => {
    const botao = aberta === "pedidos" ? botaoPedidos : botaoSumidos;
    setAberta(null);
    botao.current?.focus();
  }, [aberta]);

  // A lista não sobrevive à frase sumir ou virar link direto (o poll pode mudar isso aberto).
  useEffect(() => {
    if (aberta && !listaVale) setAberta(null);
  }, [aberta, listaVale]);

  // Fecha em clique fora e Esc, devolvendo o foco ao botão — o contrato do sino.
  useEffect(() => {
    if (!aberta) return;
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
  }, [aberta, fechar]);

  const alternar = (qual: QualLista) => setAberta((a) => (a === qual ? null : qual));

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
            <div className="flex h-10">
              {total > 0 && (
                <Segmento
                  total={total}
                  itens={itens}
                  frase={total === 1 ? "1 evento sumiu do Google Agenda" : `${total} eventos sumiram do Google Agenda`}
                  fraseCurta={total === 1 ? "1 sumiu do Google" : `${total} sumiram do Google`}
                  Icone={CalendarX}
                  tom="bg-red text-on-color"
                  aberto={aberta === "sumidos"}
                  onAlternar={() => alternar("sumidos")}
                  botaoRef={botaoSumidos}
                  listaId={listaSumidos}
                />
              )}
              {totalPedidos > 0 && (
                <Segmento
                  total={totalPedidos}
                  itens={itensPedidos}
                  frase={
                    totalPedidos === 1
                      ? "1 pedido de cancelamento aguardando o Superadmin"
                      : `${totalPedidos} pedidos de cancelamento aguardando o Superadmin`
                  }
                  fraseCurta={totalPedidos === 1 ? "1 pedido de cancelamento" : `${totalPedidos} pedidos de cancel.`}
                  Icone={FileX}
                  tom="border-b border-gold/40 bg-gold-soft text-gold-ink"
                  aberto={aberta === "pedidos"}
                  onAlternar={() => alternar("pedidos")}
                  botaoRef={botaoPedidos}
                  listaId={listaPedidos}
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {visivel && lista && listaVale && (
          <motion.div
            key={aberta}
            id={lista.id}
            initial={reduceMotion ? false : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: "easeOut" }}
            className="absolute inset-x-0 top-full max-h-[60vh] overflow-y-auto border-b border-line bg-panel shadow-lg"
          >
            <ul className="divide-y divide-line">
              {lista.itens.map((item) => (
                <li key={item.id}>
                  <Link
                    to={`/events/${item.id}`}
                    title={item.title}
                    onClick={() => setAberta(null)}
                    className={cn(
                      "flex min-h-11 items-center gap-3 px-4 py-2 text-sm hover:bg-surface-2",
                      FOCO,
                      "focus-visible:ring-accent",
                    )}
                  >
                    <span className="min-w-0 flex-1 truncate text-ink">{item.title}</span>
                    <span className="shrink-0 tabular-nums text-muted">{dataDoEvento(item.start_at)}</span>
                  </Link>
                </li>
              ))}
              {lista.total > lista.itens.length && (
                <li className="px-4 py-2 text-sm text-muted">e mais {lista.total - lista.itens.length}</li>
              )}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
