/**
 * Formatação amigável de data/hora do Portal do Artista (Princípio VII).
 *
 * Fonte única do app: nenhuma tela monta `toLocaleString` à mão. Valor monetário NÃO mora aqui
 * — continua vindo de `@manto/money` (`formatBRL`), fonte única de toda a plataforma.
 *
 * O backend serializa datas em ISO naïve (sem fuso), já convertidas para o horário de Brasília
 * (`portal_ops.now_sp`). `new Date("2026-07-28T20:00:00")` interpreta string sem fuso como
 * horário LOCAL do navegador — que é o que queremos: o talento vê o horário do evento como foi
 * cadastrado, sem deslocamento.
 */

const WEEKDAYS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

const MONTHS = [
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

function parse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** `28 de jul, 20:00` — formato padrão de data+hora nas listagens. */
export function formatDateTime(iso: string | null | undefined): string {
  const date = parse(iso);
  if (!date) return "Data a confirmar";
  const time = date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${date.getDate()} de ${MONTHS[date.getMonth()]}, ${time}`;
}

/** `28 de julho de 2026` — data por extenso, para cabeçalhos. */
export function formatLongDate(iso: string | null | undefined): string {
  const date = parse(iso);
  if (!date) return "Data a confirmar";
  return date.toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}

/** `segunda-feira` / `sábado` — dia da semana, para reforçar a leitura rápida da agenda. */
export function formatWeekday(iso: string | null | undefined): string {
  const date = parse(iso);
  if (!date) return "";
  const name = WEEKDAYS[date.getDay()];
  return name === "sábado" || name === "domingo" ? name : `${name}-feira`;
}

// `formatRelativeDay` e `formatShortDate` subiram para `@manto/ui` na feature 197, quando o
// painel interno passou a precisar dos mesmos formatos — reexportados aqui para as telas do
// Portal seguirem importando de um lugar só.
export { formatRelativeDay, formatShortDate } from "@manto/ui";
