import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { Button, Input } from "@manto/ui";
import { brl, currentMonth, shiftMonth } from "../../lib/pagamentos";
import { DESEMBOLSO_FILTRO_LABELS, type DesembolsoFiltro, type FiltrosDeGastos } from "../../lib/gastos";

/** Chave da URL → valor novo (`null` apaga a chave). */
export type MudancaDeFiltro = Partial<Record<"busca" | "categoria" | "desembolso" | "mes", string | null>>;

const SELECT =
  "h-10 min-w-0 rounded-md border border-line bg-panel px-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

interface GastosFiltrosProps {
  filtros: FiltrosDeGastos;
  categorias: readonly string[];
  onChange: (mudanca: MudancaDeFiltro) => void;
  /** Há algum filtro (inclusive a situação, escolhida nos cartões) — mostra o resumo e o "Limpar filtros". */
  filtroAtivo: boolean;
  emExibicao: number;
  totalGastos: number;
  somaEmExibicao: number;
  onLimpar: () => void;
}

/**
 * Barra de filtros de Gastos Extras (feature 314): busca, categoria, desembolso e mês. A situação
 * não está aqui — escolhe-se nos cartões-filtro, como em Pagamentos. Tudo vira chave na URL.
 */
export function GastosFiltros({
  filtros,
  categorias,
  onChange,
  filtroAtivo,
  emExibicao,
  totalGastos,
  somaEmExibicao,
  onLimpar,
}: GastosFiltrosProps) {
  // Sem mês escolhido, as setas partem do mês corrente: a tela abre em "todos os meses" e a
  // primeira seta leva a um mês que faz sentido, não a um vazio.
  const andarMes = (delta: number) => onChange({ mes: shiftMonth(filtros.mes ?? currentMonth(), delta) });

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1 basis-64 sm:max-w-lg">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            aria-hidden
          />
          <Input
            value={filtros.busca}
            onChange={(e) => onChange({ busca: e.target.value || null })}
            placeholder="Buscar por descrição, quem recebe, evento, autor, valor…"
            aria-label="Buscar nos gastos"
            autoComplete="off"
            className="pl-9 pr-10"
          />
          {filtros.busca && (
            <button
              type="button"
              onClick={() => onChange({ busca: null })}
              aria-label="Limpar busca"
              title="Limpar busca"
              className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
        <select
          className={SELECT}
          value={filtros.categoria ?? ""}
          onChange={(e) => onChange({ categoria: e.target.value || null })}
          aria-label="Categoria"
        >
          <option value="">Todas as categorias</option>
          {categorias.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          className={SELECT}
          value={filtros.desembolso ?? ""}
          onChange={(e) => onChange({ desembolso: e.target.value || null })}
          aria-label="Desembolso"
        >
          <option value="">Todos os desembolsos</option>
          {(Object.keys(DESEMBOLSO_FILTRO_LABELS) as DesembolsoFiltro[]).map((d) => (
            <option key={d} value={d}>
              {DESEMBOLSO_FILTRO_LABELS[d]}
            </option>
          ))}
        </select>
        {/* As setas existem para o celular, onde acertar o seletor nativo de mês com o dedo é a
            parte mais difícil (mesma lição de Pagamentos). */}
        {/* `flex-wrap`: com mês escolhido, setas + campo + "Todos os meses" somam 367px e passavam de
            375px no celular (rolagem lateral — achado G1 do converge). */}
        <div className="flex flex-wrap items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-10 w-10 p-0"
            aria-label="Mês anterior"
            onClick={() => andarMes(-1)}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </Button>
          <Input
            type="month"
            value={filtros.mes ?? ""}
            onChange={(e) => onChange({ mes: e.target.value || null })}
            className="h-10 w-[9.5rem]"
            aria-label="Mês do gasto"
          />
          <Button
            variant="outline"
            size="sm"
            className="h-10 w-10 p-0"
            aria-label="Mês seguinte"
            onClick={() => andarMes(1)}
          >
            <ChevronRight className="h-4 w-4" aria-hidden />
          </Button>
          {filtros.mes && (
            <Button variant="ghost" size="sm" onClick={() => onChange({ mes: null })}>
              Todos os meses
            </Button>
          )}
        </div>
      </div>
      {filtroAtivo && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold tabular-nums text-ink">
            {emExibicao} de {totalGastos} {totalGastos === 1 ? "gasto" : "gastos"} · {brl(somaEmExibicao)}
          </span>
          <Button variant="ghost" size="sm" onClick={onLimpar}>
            Limpar filtros
          </Button>
        </div>
      )}
    </div>
  );
}
