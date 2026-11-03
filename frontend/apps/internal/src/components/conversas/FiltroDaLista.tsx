import { cn } from "@manto/ui";
import type { FiltroDaLista as Filtro } from "../../lib/conversas";

/**
 * "Todas", "Minhas" e "Sem responsável" (feature 328, FR-005). Botões de alternância, não abas: o
 * filtro muda a lista, não troca de painel. No celular, cada botão tem 44 px de altura (FR-017).
 */

const OPCOES: { valor: Filtro; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "minhas", rotulo: "Minhas" },
  { valor: "sem_responsavel", rotulo: "Sem responsável" },
];

interface FiltroDaListaProps {
  valor: Filtro;
  onMudar: (valor: Filtro) => void;
}

export function FiltroDaLista({ valor, onMudar }: FiltroDaListaProps) {
  return (
    <div role="group" aria-label="Filtrar conversas" className="flex gap-1 rounded-md bg-surface-2 p-1">
      {OPCOES.map((opcao) => (
        <button
          key={opcao.valor}
          type="button"
          aria-pressed={valor === opcao.valor}
          onClick={() => onMudar(opcao.valor)}
          className={cn(
            "min-h-11 flex-auto whitespace-nowrap rounded px-2 text-xs font-medium transition-colors md:min-h-8",
            valor === opcao.valor ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink",
          )}
        >
          {opcao.rotulo}
        </button>
      ))}
    </div>
  );
}
