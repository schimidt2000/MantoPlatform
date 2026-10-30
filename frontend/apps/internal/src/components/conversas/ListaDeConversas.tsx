import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Search } from "lucide-react";
import { Button, Input, Skeleton, cn } from "@manto/ui";
import { horaNaLista, type ConversaResumo } from "../../lib/conversas";

/**
 * A lista de conversas (feature 325, FR-013): da última mensagem para trás, com a busca por nome
 * ou telefone, o telefone, o trecho da última mensagem e a contagem de não lidas da equipe.
 * O topo se atualiza sozinho; as páginas antigas vêm pelo "Carregar mais", sem polling.
 */

interface ListaDeConversasProps {
  busca: string;
  onBusca: (valor: string) => void;
  conversas: ConversaResumo[] | undefined;
  carregando: boolean;
  falhou: boolean;
  buscando: boolean;
  onTentarDeNovo: () => void;
  temMais: boolean;
  carregandoMais: boolean;
  onCarregarMais: () => void;
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

function ItemDaLista({
  conversa,
  selecionada,
  onSelecionar,
}: {
  conversa: ConversaResumo;
  selecionada: boolean;
  onSelecionar: (id: number) => void;
}) {
  const mostrarTelefone = conversa.telefone_legivel && conversa.telefone_legivel !== conversa.nome;
  return (
    <button
      type="button"
      onClick={() => onSelecionar(conversa.id)}
      aria-current={selecionada ? "true" : undefined}
      className={cn(
        "flex min-h-16 w-full items-center gap-3 border-b border-line px-3 py-2 text-left transition-colors hover:bg-surface-2",
        selecionada && "bg-surface-2",
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
        {mostrarTelefone ? <span className="block truncate text-xs text-muted">{conversa.telefone_legivel}</span> : null}
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
  );
}

export function ListaDeConversas({
  busca,
  onBusca,
  conversas,
  carregando,
  falhou,
  buscando,
  onTentarDeNovo,
  temMais,
  carregandoMais,
  onCarregarMais,
  selecionada,
  onSelecionar,
}: ListaDeConversasProps) {
  const reduzir = useReducedMotion();
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
            <Button type="button" variant="outline" loading={buscando} onClick={onTentarDeNovo}>
              Tentar novamente
            </Button>
          </div>
        ) : !conversas?.length ? (
          <p className="p-6 text-center text-sm text-muted">Nenhuma conversa encontrada.</p>
        ) : (
          <>
            <ul>
              <AnimatePresence initial={false}>
                {conversas.map((conversa) => (
                  <motion.li
                    key={conversa.id}
                    layout={reduzir ? false : "position"}
                    initial={reduzir ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.18 }}
                  >
                    <ItemDaLista
                      conversa={conversa}
                      selecionada={selecionada === conversa.id}
                      onSelecionar={onSelecionar}
                    />
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
            {temMais ? (
              <div className="p-3 text-center">
                <Button type="button" variant="outline" size="sm" loading={carregandoMais} onClick={onCarregarMais}>
                  Carregar mais
                </Button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
