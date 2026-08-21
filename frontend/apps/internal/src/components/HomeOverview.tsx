import { motion, useReducedMotion } from "framer-motion";
import { Card } from "@manto/ui";

export interface HomeOverviewItem {
  key: string;
  emoji: string;
  label: string;
  count: number;
  /** Subconjunto de `count` que precisa de ação imediata (selo vermelho). */
  urgent: number;
  /** Contexto extra numa linha (ex.: "R$ 12.400 em aberto", "3 sem convite"). */
  detail?: string | null;
}

interface HomeOverviewProps {
  items: HomeOverviewItem[];
  onSelect: (key: string) => void;
}

/**
 * Visão geral da Home: um card compacto por setor com a contagem de pendências,
 * o recorte urgente e um toque que leva direto ao painel correspondente.
 *
 * É a resposta ao "lista gigante": no celular a pessoa enxerga em uma tela o que
 * cada área deve, e só então mergulha; no desktop (superadmin) vira o mapa dos
 * oito painéis. Card zerado fica esmaecido de propósito — o olho vai para onde
 * há trabalho.
 */
export function HomeOverview({ items, onSelect }: HomeOverviewProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-4" role="list">
      {items.map((item, index) => {
        const emDia = item.count === 0;
        return (
          <motion.div
            key={item.key}
            role="listitem"
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: reduceMotion ? 0 : index * 0.03, ease: "easeOut" }}
          >
            <Card
              asChild
              className={`h-full transition-colors hover:border-line-strong hover:bg-surface-2 ${
                emDia ? "opacity-70" : ""
              }`}
            >
              <button
                type="button"
                onClick={() => onSelect(item.key)}
                className="flex w-full cursor-pointer flex-col items-start gap-1 px-3.5 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`${item.label}: ${item.count} pendência${item.count !== 1 ? "s" : ""}${
                  item.urgent > 0 ? `, ${item.urgent} urgente${item.urgent !== 1 ? "s" : ""}` : ""
                } — ir para a seção`}
              >
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
                  <span aria-hidden="true" className="text-sm leading-none">
                    {item.emoji}
                  </span>
                  {item.label}
                </span>
                <span className="flex w-full flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span
                    className={`text-2xl font-semibold leading-none tabular-nums ${
                      emDia ? "text-muted" : "text-ink"
                    }`}
                  >
                    {item.count}
                  </span>
                  {emDia ? (
                    <span className="rounded-full bg-green-soft px-2 py-0.5 text-[11px] font-medium text-green">
                      Em dia ✓
                    </span>
                  ) : (
                    item.urgent > 0 && (
                      <span className="rounded-full bg-red-soft px-2 py-0.5 text-[11px] font-medium text-red">
                        {item.urgent} urgente{item.urgent !== 1 ? "s" : ""}
                      </span>
                    )
                  )}
                </span>
                {item.detail && (
                  <span className="max-w-full truncate text-[11px] text-muted">{item.detail}</span>
                )}
              </button>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
