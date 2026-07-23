import { Button } from "@manto/ui";
import { type AgendaViewMode, dayLabel, monthLabel } from "../lib/agendaDates";

export interface AgendaToolbarProps {
  view: AgendaViewMode;
  /** "YYYY-MM-DD" — data de referência (usada também para o rótulo de Mês/Lista via slice). */
  refDate: string;
  onViewChange: (view: AgendaViewMode) => void;
  onNavigate: (delta: -1 | 1) => void;
  onToday: () => void;
}

const VIEW_OPTIONS: { value: AgendaViewMode; label: string }[] = [
  { value: "month", label: "Mês" },
  { value: "day", label: "Dia" },
  { value: "list", label: "Lista" },
];

function periodLabel(view: AgendaViewMode, refDate: string): string {
  return view === "day" ? dayLabel(refDate) : monthLabel(refDate.slice(0, 7));
}

/** Seletor de visualização (Mês/Dia/Lista) + navegação de período (‹/Hoje/›) da Agenda. */
export function AgendaToolbar({
  view,
  refDate,
  onViewChange,
  onNavigate,
  onToday,
}: AgendaToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <div
        role="group"
        aria-label="Visualização da agenda"
        className="inline-flex w-fit overflow-hidden rounded-md border border-line"
      >
        {VIEW_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            aria-pressed={view === opt.value}
            onClick={() => onViewChange(opt.value)}
            className={`px-3 py-1.5 text-sm font-medium transition-colors ${
              view === opt.value
                ? "bg-accent text-white"
                : "bg-panel text-ink hover:bg-surface-2"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => onNavigate(-1)} aria-label="Período anterior">
          ‹
        </Button>
        <Button variant="outline" size="sm" onClick={onToday}>
          Hoje
        </Button>
        <Button variant="outline" size="sm" onClick={() => onNavigate(1)} aria-label="Próximo período">
          ›
        </Button>
        <span className="min-w-40 text-center text-sm font-medium text-ink">
          {periodLabel(view, refDate)}
        </span>
      </div>
    </div>
  );
}
