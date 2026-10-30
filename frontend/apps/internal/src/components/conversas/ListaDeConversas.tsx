import { Search } from "lucide-react";
import { Input, Skeleton, cn } from "@manto/ui";
import { horaNaLista, type ConversaResumo } from "../../lib/conversas";

/**
 * A lista de conversas (feature 325, FR-013): da última mensagem para trás, com a busca por nome
 * ou telefone, o trecho da última mensagem e a contagem de não lidas da equipe.
 */

interface ListaDeConversasProps {
  busca: string;
  onBusca: (valor: string) => void;
  conversas: ConversaResumo[] | undefined;
  carregando: boolean;
  falhou: boolean;
  onTentarDeNovo: () => void;
  selecionada: number | null;
  onSelecionar: (id: number) => void;
}

function Inicial({ nome }: { nome: string }) {
  return (
    <span
      aria-hidden
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-ink"
    >
      {(nome.trim()[0] ?? "?").toUpperCase()}
    </span>
  );
}

export function ListaDeConversas({
  busca,
  onBusca,
  conversas,
  carregando,
  falhou,
  onTentarDeNovo,
  selecionada,
  onSelecionar,
}: ListaDeConversasProps) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-line bg-panel p-3">
        <label htmlFor="busca-conversas" className="sr-only">
          Buscar conversa
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input
            id="busca-conversas"
            value={busca}
            onChange={(e) => onBusca(e.target.value)}
            placeholder="Buscar por nome ou telefone"
            className="pl-9"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {carregando ? (
          <div className="space-y-2 p-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : falhou ? (
          <div className="space-y-2 p-4">
            <p role="alert" className="text-sm text-red">
              Não foi possível carregar as conversas. Tente novamente.
            </p>
            <button type="button" className="text-sm font-medium text-accent underline" onClick={onTentarDeNovo}>
              Tentar novamente
            </button>
          </div>
        ) : !conversas?.length ? (
          <p className="p-6 text-center text-sm text-muted">Nenhuma conversa encontrada.</p>
        ) : (
          <ul>
            {conversas.map((conversa) => (
              <li key={conversa.id}>
                <button
                  type="button"
                  onClick={() => onSelecionar(conversa.id)}
                  aria-current={selecionada === conversa.id ? "true" : undefined}
                  className={cn(
                    "flex min-h-16 w-full items-center gap-3 border-b border-line px-3 py-2 text-left transition-colors hover:bg-surface-2",
                    selecionada === conversa.id && "bg-surface-2",
                  )}
                >
                  <Inicial nome={conversa.nome} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className={cn("truncate text-sm", conversa.nao_lidas > 0 ? "font-semibold" : "font-medium")}>
                        {conversa.nome}
                      </span>
                      <span className="shrink-0 text-xs text-muted">{horaNaLista(conversa.ultima_mensagem_em)}</span>
                    </span>
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-muted">{conversa.ultima_previa ?? ""}</span>
                      {conversa.nao_lidas > 0 ? (
                        <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-on-color">
                          <span className="sr-only">Não lidas: </span>
                          {conversa.nao_lidas}
                        </span>
                      ) : null}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
