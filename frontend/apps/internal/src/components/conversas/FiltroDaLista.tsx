import { cn } from "@manto/ui";
import {
  DIAS_DO_PARADO,
  type Canal,
  type DiasDoParado,
  type FiltroDaLista as Filtro,
  type RecorteDaLista,
} from "../../lib/conversas";

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

// O rótulo curto cabe numa linha só em 390 px; o nome inteiro vai no `aria-label`.
const RECORTES: { valor: RecorteDaLista; rotulo: string; inteiro: string }[] = [
  { valor: "esperando", rotulo: "Esperando", inteiro: "Esperando resposta" },
  { valor: "orcamento_parado", rotulo: "Orçamento parado", inteiro: "Orçamento sem retorno" },
  { valor: "anuncio", rotulo: "Anúncio", inteiro: "Veio de anúncio" },
];

/**
 * Os recortes da venda (feature 349, FR-014): combinam com Todas/Minhas/Sem responsável e com o canal. Um de cada
 * vez; tocar no ativo desliga. No "Orçamento parado", os dias da régua (2, 5 ou 9) aparecem logo abaixo.
 */
export function FiltroDoRecorte({
  valor,
  onMudar,
  dias,
  onDias,
}: {
  valor: RecorteDaLista | null;
  onMudar: (valor: RecorteDaLista | null) => void;
  dias: DiasDoParado;
  onDias: (dias: DiasDoParado) => void;
}) {
  return (
    <div className="space-y-1">
      <div role="group" aria-label="Recortes da venda" className="flex gap-1">
        {RECORTES.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            aria-pressed={valor === opcao.valor}
            aria-label={opcao.inteiro}
            title={opcao.inteiro}
            onClick={() => onMudar(valor === opcao.valor ? null : opcao.valor)}
            className={cn(
              "min-h-11 flex-auto whitespace-nowrap rounded-full border px-3 text-xs font-medium transition-colors md:min-h-8",
              valor === opcao.valor
                ? "border-accent bg-accent-soft text-ink"
                : "border-line text-muted hover:text-ink",
            )}
          >
            {opcao.rotulo}
          </button>
        ))}
      </div>
      {valor === "orcamento_parado" ? (
        <div role="group" aria-label="Sem retorno há" className="flex items-center gap-1 text-xs">
          <span className="shrink-0 text-muted">Sem retorno há</span>
          {DIAS_DO_PARADO.map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={dias === d}
              onClick={() => onDias(d)}
              className={cn(
                "min-h-11 flex-1 rounded px-2 font-medium transition-colors md:min-h-8",
                dias === d ? "bg-panel text-ink shadow-sm ring-1 ring-line" : "text-muted hover:text-ink",
              )}
            >
              {d} dias
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

const CANAIS: { valor: Canal | null; rotulo: string }[] = [
  { valor: null, rotulo: "Todos" },
  { valor: "whatsapp", rotulo: "WhatsApp" },
  { valor: "instagram", rotulo: "Instagram" },
];

/** "Todos" · "WhatsApp" · "Instagram" (feature 330) — só aparece com os dois canais ligados. */
export function FiltroDoCanal({ valor, onMudar }: { valor: Canal | null; onMudar: (valor: Canal | null) => void }) {
  return (
    <div role="group" aria-label="Filtrar por canal" className="flex gap-1 rounded-md bg-surface-2 p-1">
      {CANAIS.map((opcao) => (
        <button
          key={opcao.rotulo}
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
