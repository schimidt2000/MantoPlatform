/** Estado e helpers de data compartilhados pelas 3 visões da Agenda (Mês/Dia/Lista). */
export type AgendaViewMode = "month" | "day" | "list";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function toYmd(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function capitalize(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** Data de hoje em "YYYY-MM-DD". */
export function todayYmd(): string {
  return toYmd(new Date());
}

/** Mês corrente em "YYYY-MM". */
export function currentYm(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
}

/** "YYYY-MM" do dia informado ("YYYY-MM-DD"). */
export function ymOf(date: string): string {
  return date.slice(0, 7);
}

/** Desloca um mês ("YYYY-MM") em `delta` meses. */
export function shiftMonth(ym: string, delta: number): string {
  const [y, m] = ym.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}`;
}

/** Desloca um dia ("YYYY-MM-DD") em `delta` dias. */
export function shiftDay(date: string, delta: number): string {
  const [y, m, d] = date.split("-").map(Number);
  const dt = new Date(y, m - 1, d + delta);
  return toYmd(dt);
}

/** Rótulo do mês, capitalizado (ex.: "Julho de 2026"). */
export function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  const label = new Date(y, m - 1, 1).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
  return capitalize(label);
}

/** Rótulo do dia, capitalizado (ex.: "25 de julho de 2026"). */
export function dayLabel(date: string): string {
  const [y, m, d] = date.split("-").map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return capitalize(label);
}

/** Rótulo do dia com dia da semana, capitalizado (ex.: "Sexta-feira, 25 de julho"). */
export function dayHeaderLabel(date: string): string {
  const [y, m, d] = date.split("-").map(Number);
  const label = new Date(y, m - 1, d).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  return capitalize(label);
}
