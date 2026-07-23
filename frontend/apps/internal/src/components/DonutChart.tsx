import { motion, useReducedMotion } from "framer-motion";

export interface DonutChartProps {
  label: string;
  done: number;
  total: number;
}

// Cores replicadas de app/static/style.css (.donut): verde concluído / vermelho-suave restante —
// mesma paleta do preset compartilhado (green.DEFAULT / red.soft), sem token Tailwind próprio
// para conic-gradient dinâmico.
const DONE_COLOR = "#1a7f3c";
const REMAINING_COLOR = "#fde8e8";

/** Donut de progresso (CSS puro), paridade visual com `.donut`/`.donut-inner` do Jinja clássico. */
export function DonutChart({ label, done, total }: DonutChartProps) {
  const reduceMotion = useReducedMotion();
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="text-center">
      <div className="mb-2 text-xs font-medium text-muted">{label}</div>
      <motion.div
        className="mx-auto grid h-28 w-28 place-items-center rounded-full"
        style={{
          background: `conic-gradient(${DONE_COLOR} 0deg, ${DONE_COLOR} ${pct * 3.6}deg, ${REMAINING_COLOR} ${pct * 3.6}deg)`,
        }}
        initial={reduceMotion ? false : { opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      >
        <div className="grid h-[72px] w-[72px] place-items-center rounded-full bg-panel text-base font-extrabold text-ink">
          {pct}%
        </div>
      </motion.div>
      <div className="mt-2 text-xs text-muted">
        {done}/{total}
      </div>
    </div>
  );
}
