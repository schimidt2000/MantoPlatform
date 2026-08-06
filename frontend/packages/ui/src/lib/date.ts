/**
 * Formatação amigável de data em pt-BR — fonte única da plataforma (Princípio VII).
 *
 * Promovido de `apps/portal/src/lib/format.ts` na feature 197, quando o painel interno
 * (`ClientFeedbackPage`) passou a precisar dos mesmos formatos. O Portal continua expondo
 * `formatShortDate`/`formatRelativeDay` pelo seu `lib/format.ts`, que agora só reexporta
 * daqui — nenhuma tela ficou com cópia própria.
 *
 * O backend serializa datas em ISO naïve (sem fuso). `new Date("2026-07-28T20:00:00")`
 * interpreta string sem fuso como horário LOCAL do navegador — que é o que queremos: a data
 * é lida como foi cadastrada, sem deslocamento.
 *
 * A exceção é a data **pura** (`"2026-08-05"`, sem hora): essa a especificação manda interpretar
 * como **UTC**, e em São Paulo (UTC−3) ela vira 21h do dia anterior — a tela mostrava 04/08 para
 * um vencimento em 05/08. Por isso `parse` monta a data pura campo a campo, em horário local.
 */

const DATA_PURA = /^\d{4}-\d{2}-\d{2}$/;

function parse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  if (DATA_PURA.test(iso)) {
    const [year, month, day] = iso.split("-").map(Number);
    const local = new Date(year, month - 1, day);
    return Number.isNaN(local.getTime()) ? null : local;
  }
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** `hoje` / `amanhã` / `em 5 dias` / `há 3 dias` — distância relativa, em pt-BR. */
export function formatRelativeDay(iso: string | null | undefined): string {
  const date = parse(iso);
  if (!date) return "";

  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOfDay(date) - startOfDay(new Date())) / 86_400_000);

  if (days === 0) return "hoje";
  if (days === 1) return "amanhã";
  if (days === -1) return "ontem";
  return days > 0 ? `em ${days} dias` : `há ${Math.abs(days)} dias`;
}

/** `28/07/2026` — data curta, para listagens e formato tabular. */
export function formatShortDate(iso: string | null | undefined): string {
  const date = parse(iso);
  if (!date) return "—";
  return date.toLocaleDateString("pt-BR");
}
