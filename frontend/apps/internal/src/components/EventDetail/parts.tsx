import { type ReactNode } from "react";
import { formatBRL } from "@manto/money";

/**
 * Peças visuais compartilhadas pelas seções da tela de detalhe do evento (feature 190).
 *
 * A tela é de altíssima densidade: em vez do `Card`/`CardHeader` do design system (pensado
 * para blocos espaçados), as seções usam um painel com título compacto em caixa-alta — o
 * mesmo ritmo visual das telas de Financeiro. Fonte única aqui para nenhuma seção reinventar
 * o cabeçalho.
 */

/** Valor monetário formatado no padrão brasileiro (Princípio VII — `@manto/money`). */
export function brl(value: number | null | undefined): string {
  return `R$ ${formatBRL(value ?? 0)}`;
}

/** Data/hora em pt-BR ("05/07/2026 12:00"); string vazia quando não há data. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Só a data em pt-BR ("05/07/2026"). */
export function formatDay(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
}

/** Só o horário em pt-BR ("12:00"). */
export function formatTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

/** Faixa horária do evento ("05/07/2026 12:00 — 16:00"). */
export function formatRange(startIso: string | null, endIso: string | null): string {
  if (!startIso) return "";
  const start = `${formatDay(startIso)} ${formatTime(startIso)}`;
  return endIso ? `${start} — ${formatTime(endIso)}` : start;
}

export interface PanelProps {
  title: string;
  /** Ações à direita do título (botões pequenos, contadores). */
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Painel de seção com título compacto em caixa-alta.
 *
 * O cabeçalho quebra linha (`flex-wrap`) porque as ações são botões com `whitespace-nowrap`:
 * sem isso, dois botões ("Imprimir fichas" + "Banco de figurinos") empurravam o painel além da
 * largura da tela no celular e a página inteira passava a rolar na horizontal.
 */
export function Panel({ title, actions, children, className }: PanelProps) {
  return (
    <section className={`rounded-lg border border-line bg-panel p-4 ${className ?? ""}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.07em] text-muted">{title}</h2>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

/** Linha rótulo → valor das listas de dados (venda, logística). */
export function DataRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="shrink-0 text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

/** Estrelas de uma avaliação (1–5), com o valor acessível por texto. */
export function Stars({ score }: { score: number }) {
  return (
    <span className="whitespace-nowrap text-gold" aria-label={`${score} de 5 estrelas`}>
      {"★".repeat(score)}
      <span className="text-muted">{"★".repeat(Math.max(0, 5 - score))}</span>
    </span>
  );
}

/** Estado vazio padrão das seções. */
export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted">{children}</p>;
}

/** Classe única dos inputs compactos da tela (altura de toque ≥ 44px no mobile). */
export const INPUT_CLASS =
  "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
