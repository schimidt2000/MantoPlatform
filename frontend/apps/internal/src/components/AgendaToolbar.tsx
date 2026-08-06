import { Button, Input } from "@manto/ui";
import { type AgendaViewMode, dayLabel, monthLabel } from "../lib/agendaDates";

export interface AgendaToolbarProps {
  view: AgendaViewMode;
  /** "YYYY-MM-DD" — data de referência (usada também para o rótulo de Mês/Lista via slice). */
  refDate: string;
  onViewChange: (view: AgendaViewMode) => void;
  onNavigate: (delta: -1 | 1) => void;
  onToday: () => void;
  /** Pula direto para o mês (visão Mês/Lista) ou dia (visão Dia) escolhido. */
  onDateChange: (date: string) => void;
  /** Campo ÚNICO de busca (evento, cliente ou telefone) — sem filtros extras. */
  searchValue: string;
  onSearchChange: (q: string) => void;
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
  onDateChange,
  searchValue,
  onSearchChange,
}: AgendaToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <Input
        type="search"
        aria-label="Buscar eventos"
        placeholder="Buscar evento, cliente ou telefone…"
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        className="h-9 w-full sm:w-64"
      />
      {/* Contorno em `line-strong`: é ele que agrupa Mês/Dia/Lista num controle único —
          com o `line` decorativo (1.27:1) o grupo se dissolvia no fundo da página. */}
      <div
        role="group"
        aria-label="Visualização da agenda"
        className="inline-flex w-fit overflow-hidden rounded-md border border-line-strong"
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

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => onNavigate(-1)} aria-label="Período anterior">
          ‹
        </Button>
        <Button variant="outline" size="sm" onClick={onToday}>
          Hoje
        </Button>
        <Button variant="outline" size="sm" onClick={() => onNavigate(1)} aria-label="Próximo período">
          ›
        </Button>
        <span className="text-center text-sm font-medium text-ink sm:min-w-40">
          {periodLabel(view, refDate)}
        </span>
        {view === "day" ? (
          <Input
            type="date"
            aria-label="Ir para o dia"
            value={refDate}
            onChange={(e) => e.target.value && onDateChange(e.target.value)}
            className="h-9 w-40"
          />
        ) : (
          <Input
            type="month"
            aria-label="Ir para o mês"
            value={refDate.slice(0, 7)}
            onChange={(e) => e.target.value && onDateChange(`${e.target.value}-01`)}
            className="h-9 w-36"
          />
        )}
      </div>
    </div>
  );
}
