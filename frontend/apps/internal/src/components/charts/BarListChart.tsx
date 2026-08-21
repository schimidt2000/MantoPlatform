import { motion, useReducedMotion } from "framer-motion";

export interface BarItem {
  label: string;
  /** Texto secundário à esquerda (ex.: plataforma). */
  sublabel?: string;
  value: number;
  /** Valor já formatado para leitura (ex.: "R$ 1.234,56"). */
  display: string;
}

interface BarListChartProps {
  items: BarItem[];
  tone?: "accent" | "gold" | "green";
  /** Limite de linhas; o resto é somado em "Outras". */
  max?: number;
}

const TONE_CLASS = { accent: "text-accent", gold: "text-gold", green: "text-green" } as const;

/**
 * Barras horizontais de uma medida só (magnitude ⇒ uma matiz). Texto em tokens de texto; a
 * cor só na barra. Largura por atributo SVG — nada de `style` inline.
 */
export function BarListChart({ items, tone = "accent", max = 8 }: BarListChartProps) {
  const reduceMotion = useReducedMotion();
  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">Sem dado no período.</p>;
  }
  const ordenados = [...items].sort((a, b) => b.value - a.value);
  const visiveis = ordenados.slice(0, max);
  const resto = ordenados.slice(max);
  if (resto.length > 0) {
    const soma = resto.reduce((s, it) => s + it.value, 0);
    visiveis.push({ label: `Outras (${resto.length})`, value: soma, display: "" });
  }
  const maximo = Math.max(...visiveis.map((it) => it.value), 1);

  return (
    <ul className="space-y-2" role="list">
      {visiveis.map((it, i) => {
        const pct = Math.max(1, Math.round((it.value / maximo) * 100));
        return (
          <li key={`${it.label}-${i}`} className="grid grid-cols-[minmax(0,40%)_1fr_auto] items-center gap-3 text-sm">
            <span className="min-w-0">
              <span className="block truncate text-ink" title={it.label}>
                {it.label}
              </span>
              {it.sublabel && <span className="block truncate text-[11px] text-muted">{it.sublabel}</span>}
            </span>
            <span className="block h-2.5 w-full overflow-hidden rounded-full bg-surface-2">
              <svg viewBox="0 0 100 10" preserveAspectRatio="none" className={`h-full w-full ${TONE_CLASS[tone]}`} aria-hidden="true">
                <motion.rect
                  x={0}
                  y={0}
                  height={10}
                  className="fill-current"
                  initial={reduceMotion ? { width: pct } : { width: 0 }}
                  animate={{ width: pct }}
                  transition={{ duration: 0.3, ease: "easeOut", delay: reduceMotion ? 0 : i * 0.03 }}
                />
              </svg>
            </span>
            <span className="whitespace-nowrap tabular-nums text-ink">{it.display || it.value.toLocaleString("pt-BR")}</span>
          </li>
        );
      })}
    </ul>
  );
}
