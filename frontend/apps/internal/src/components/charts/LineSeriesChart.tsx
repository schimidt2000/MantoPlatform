import { useId, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

export interface LinePoint {
  /** Rótulo do eixo X (ex.: "11/08"). */
  label: string;
  value: number | null;
}

interface LineSeriesChartProps {
  title: string;
  points: LinePoint[];
  formatValue?: (value: number) => string;
  tone?: "accent" | "gold" | "green";
}

const VIEW_W = 600;
const VIEW_H = 200;
const PAD = { top: 10, right: 12, bottom: 26, left: 48 };
const TONE_CLASS = { accent: "text-accent", gold: "text-gold", green: "text-green" } as const;

/** Teto "redondo" para o eixo Y (1, 2, 5 × 10^n) — evita o eixo terminar em 5.437. */
function niceMax(maximo: number): number {
  if (maximo <= 0) return 1;
  const expoente = 10 ** Math.floor(Math.log10(maximo));
  const base = maximo / expoente;
  const passo = base <= 1 ? 1 : base <= 2 ? 2 : base <= 5 ? 5 : 10;
  return passo * expoente;
}

const padrao = (v: number) => v.toLocaleString("pt-BR");

/**
 * Série temporal de uma medida só (uma escala, um eixo — medida diferente é outro gráfico).
 * SVG por `viewBox`, cor pela classe de token, linha de 2px, marcadores de 8px e tooltip ao
 * passar o mouse/tocar; respeita `useReducedMotion`.
 */
export function LineSeriesChart({ title, points, formatValue = padrao, tone = "accent" }: LineSeriesChartProps) {
  const reduceMotion = useReducedMotion();
  const [ativo, setAtivo] = useState<number | null>(null);
  const idClip = useId();
  const valores = points.map((p) => p.value).filter((v): v is number => v != null);
  const maximo = niceMax(Math.max(0, ...valores));
  const larguraUtil = VIEW_W - PAD.left - PAD.right;
  const alturaUtil = VIEW_H - PAD.top - PAD.bottom;
  const passoX = points.length > 1 ? larguraUtil / (points.length - 1) : 0;
  const x = (i: number) => PAD.left + i * passoX;
  const y = (v: number) => PAD.top + alturaUtil - (v / maximo) * alturaUtil;

  // Segmentos contínuos: um buraco (null) quebra a linha em vez de ligar pontos distantes.
  const segmentos: string[] = [];
  let atual: string[] = [];
  points.forEach((p, i) => {
    if (p.value == null) {
      if (atual.length) segmentos.push(atual.join(" "));
      atual = [];
      return;
    }
    atual.push(`${atual.length ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`);
  });
  if (atual.length) segmentos.push(atual.join(" "));

  const ticksY = [0, maximo / 2, maximo];
  const cadaQuantos = Math.max(1, Math.ceil(points.length / 8));
  const ponto = ativo != null ? points[ativo] : null;

  if (valores.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">Sem dado no período.</p>;
  }

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label={`${title}: ${points.length} semanas, máximo ${formatValue(Math.max(...valores))}`}
        onMouseLeave={() => setAtivo(null)}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const xv = ((e.clientX - rect.left) / rect.width) * VIEW_W;
          const i = passoX ? Math.round((xv - PAD.left) / passoX) : 0;
          setAtivo(Math.min(points.length - 1, Math.max(0, i)));
        }}
      >
        <defs>
          <clipPath id={idClip}>
            <rect x={PAD.left - 6} y={0} width={larguraUtil + 12} height={VIEW_H} />
          </clipPath>
        </defs>
        {ticksY.map((t) => (
          <g key={t} className="text-line">
            <line x1={PAD.left} x2={VIEW_W - PAD.right} y1={y(t)} y2={y(t)} stroke="currentColor" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(t) + 3} textAnchor="end" className="fill-current text-[10px] text-muted">
              {formatValue(t)}
            </text>
          </g>
        ))}
        {points.map((p, i) =>
          i % cadaQuantos === 0 || i === points.length - 1 ? (
            <text key={p.label + i} x={x(i)} y={VIEW_H - 8} textAnchor="middle" className="fill-current text-[10px] text-muted">
              {p.label}
            </text>
          ) : null,
        )}
        <g className={TONE_CLASS[tone]} clipPath={`url(#${idClip})`}>
          {segmentos.map((d, i) => (
            <motion.path
              key={i}
              d={d}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              initial={reduceMotion ? false : { pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            />
          ))}
          {points.map((p, i) =>
            p.value == null ? null : (
              <circle
                key={i}
                cx={x(i)}
                cy={y(p.value)}
                r={ativo === i ? 5 : 4}
                fill="currentColor"
                stroke="currentColor"
                strokeWidth={0}
              >
                <title>{`${p.label}: ${formatValue(p.value)}`}</title>
              </circle>
            ),
          )}
        </g>
        {ponto && ponto.value != null && ativo != null && (
          <g transform={`translate(${Math.min(VIEW_W - 120, Math.max(PAD.left, x(ativo) - 50))}, ${Math.max(0, y(ponto.value) - 36)})`}>
            <rect width={108} height={26} rx={6} className="fill-current text-panel" stroke="currentColor" strokeWidth={1} />
            <text x={54} y={17} textAnchor="middle" className="fill-current text-[11px] font-medium text-ink">
              {`${ponto.label} · ${formatValue(ponto.value)}`}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
