import type { EventoResumo } from "./agenda";

/** Posição/tamanho calculado de um evento na linha do tempo de um dia (visão Dia). */
export interface AgendaLayoutBlock {
  event: EventoResumo;
  /** Posição vertical, % do dia (00:00–24:00). */
  topPct: number;
  /** Altura do bloco, % do dia. */
  heightPct: number;
  /** Coluna atribuída dentro do cluster de eventos sobrepostos (0-indexed). */
  column: number;
  /** Nº total de colunas do cluster ao qual este evento pertence. */
  columnCount: number;
}

const DAY_MINUTES = 24 * 60;
const MIN_DURATION_MINUTES = 60;
const MIN_BLOCK_MINUTES = 15;

interface TimedEvent {
  event: EventoResumo;
  startMin: number;
  endMin: number;
}

function toTimedEvent(event: EventoResumo): TimedEvent {
  const start = new Date(event.start_at as string);
  const startMin = start.getHours() * 60 + start.getMinutes();

  let endMin: number;
  if (event.end_at) {
    const end = new Date(event.end_at);
    // Evento que atravessa a meia-noite: trunca ao final da grade (edge case do spec.md),
    // não é redistribuído para o dia seguinte.
    endMin = end.toDateString() === start.toDateString()
      ? end.getHours() * 60 + end.getMinutes()
      : DAY_MINUTES;
  } else {
    endMin = startMin + MIN_DURATION_MINUTES;
  }

  endMin = Math.min(Math.max(endMin, startMin + MIN_BLOCK_MINUTES), DAY_MINUTES);
  return { event, startMin, endMin };
}

/** Agrupa eventos ordenados por início em clusters transitivamente sobrepostos. */
function clusterByOverlap(timed: TimedEvent[]): TimedEvent[][] {
  const clusters: TimedEvent[][] = [];
  let current: TimedEvent[] = [];
  let clusterEnd = -Infinity;

  for (const ev of timed) {
    if (current.length === 0 || ev.startMin < clusterEnd) {
      current.push(ev);
      clusterEnd = Math.max(clusterEnd, ev.endMin);
    } else {
      clusters.push(current);
      current = [ev];
      clusterEnd = ev.endMin;
    }
  }
  if (current.length > 0) clusters.push(current);
  return clusters;
}

/** Atribui colunas gulosamente dentro de um cluster (1ª coluna livre para cada evento). */
function assignColumns(cluster: TimedEvent[]): AgendaLayoutBlock[] {
  const columnEnds: number[] = [];
  const withColumn: { timed: TimedEvent; column: number }[] = [];

  for (const ev of cluster) {
    let column = columnEnds.findIndex((end) => end <= ev.startMin);
    if (column === -1) {
      column = columnEnds.length;
      columnEnds.push(ev.endMin);
    } else {
      columnEnds[column] = ev.endMin;
    }
    withColumn.push({ timed: ev, column });
  }

  const columnCount = columnEnds.length;
  return withColumn.map(({ timed, column }) => ({
    event: timed.event,
    topPct: (timed.startMin / DAY_MINUTES) * 100,
    heightPct: ((timed.endMin - timed.startMin) / DAY_MINUTES) * 100,
    column,
    columnCount,
  }));
}

/**
 * Calcula posição/overlap dos eventos com horário definido para a linha do tempo 00:00–23:00.
 *
 * Eventos sem `start_at` não entram no cálculo — tratados à parte como "sem horário" (FR-012).
 */
export function computeDayLayout(events: EventoResumo[]): AgendaLayoutBlock[] {
  const timed = events
    .filter((ev) => Boolean(ev.start_at))
    .map(toTimedEvent)
    .sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin);

  return clusterByOverlap(timed).flatMap(assignColumns);
}
