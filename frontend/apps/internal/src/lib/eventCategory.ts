/** Estilo visual por categoria de evento — paridade com `app/templates/event_detail.html`. */
export interface EventCategoryStyle {
  label: string;
  bg: string;
  fg: string;
}

// Paridade com as classes `.badge-*` de app/static/style.css: `.badge-gold` (nome legado)
// na verdade renderiza roxo institucional (`--accent`/`--accent-dark`), não dourado — SHOW
// usa a cor real renderizada, não o nome da classe. ENSAIO não tem entrada no mapa Jinja
// (`event_detail.html`) e cai no `badge-gray` padrão, igual a CORP/desconhecido.
const CATEGORY_MAP: Record<string, EventCategoryStyle> = {
  "R&I": { label: "R&I", bg: "bg-blue-soft", fg: "text-blue" },
  RI: { label: "R&I", bg: "bg-blue-soft", fg: "text-blue" },
  SHOW: { label: "Show", bg: "bg-accent-soft", fg: "text-accent" },
  CORP: { label: "Corporativo", bg: "bg-surface-2", fg: "text-muted" },
  VM: { label: "Visita Mágica", bg: "bg-blue-soft", fg: "text-blue" },
  SOCIAL: { label: "Social", bg: "bg-green-soft", fg: "text-green" },
};

const DEFAULT_STYLE: EventCategoryStyle = { label: "Outro", bg: "bg-surface-2", fg: "text-muted" };

/** Estilo (cor + rótulo) para um `event_type`; categoria desconhecida cai no padrão neutro. */
export function eventCategory(eventType: string): EventCategoryStyle {
  return CATEGORY_MAP[eventType] ?? { ...DEFAULT_STYLE, label: eventType || DEFAULT_STYLE.label };
}
