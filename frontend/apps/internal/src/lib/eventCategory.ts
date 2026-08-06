/** Estilo visual por categoria de evento — paridade com `app/templates/event_detail.html`. */
export interface EventCategoryStyle {
  label: string;
  bg: string;
  fg: string;
  /**
   * Borda esquerda sólida na cor forte da categoria.
   *
   * O fundo `soft` sozinho difere da célula do calendário em apenas 1.17–1.24:1 (e no dia
   * fora do mês o chip neutro caía sobre `bg-surface-2` idêntico, 1.00:1 — invisível). A
   * WCAG 1.4.11 pede 3:1 para componente não-textual; a barra lateral resolve isso sem
   * escurecer o fundo, então o chip continua leve.
   */
  border: string;
}

// Paridade com as classes `.badge-*` de app/static/style.css: `.badge-gold` (nome legado)
// na verdade renderiza roxo institucional (`--accent`/`--accent-dark`), não dourado — SHOW
// usa a cor real renderizada, não o nome da classe. ENSAIO não tem entrada no mapa Jinja
// (`event_detail.html`) e cai no `badge-gray` padrão, igual a CORP/desconhecido.
const CATEGORY_MAP: Record<string, EventCategoryStyle> = {
  "R&I": { label: "R&I", bg: "bg-blue-soft", fg: "text-blue", border: "border-l-2 border-blue" },
  RI: { label: "R&I", bg: "bg-blue-soft", fg: "text-blue", border: "border-l-2 border-blue" },
  SHOW: {
    label: "Show",
    bg: "bg-accent-soft",
    fg: "text-accent",
    border: "border-l-2 border-accent",
  },
  CORP: {
    label: "Corporativo",
    bg: "bg-line",
    fg: "text-muted",
    border: "border-l-2 border-line-strong",
  },
  VM: {
    label: "Visita Mágica",
    bg: "bg-blue-soft",
    fg: "text-blue",
    border: "border-l-2 border-blue",
  },
  SOCIAL: {
    label: "Social",
    bg: "bg-green-soft",
    fg: "text-green",
    border: "border-l-2 border-green",
  },
};

// `bg-line` (#e5e3ef) em vez de `bg-surface-2`: o chip neutro precisa de um fundo próprio,
// senão coincide exatamente com a célula de dia fora do mês, que também é `bg-surface-2`.
const DEFAULT_STYLE: EventCategoryStyle = {
  label: "Outro",
  bg: "bg-line",
  fg: "text-muted",
  border: "border-l-2 border-line-strong",
};

/** Estilo (cor + rótulo) para um `event_type`; categoria desconhecida cai no padrão neutro. */
export function eventCategory(eventType: string): EventCategoryStyle {
  return CATEGORY_MAP[eventType] ?? { ...DEFAULT_STYLE, label: eventType || DEFAULT_STYLE.label };
}
