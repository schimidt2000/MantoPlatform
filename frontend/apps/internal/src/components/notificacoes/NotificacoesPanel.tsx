import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Skeleton } from "@manto/ui";
import {
  agruparPorDia,
  useMarcarLida,
  useMarcarTodasLidas,
  useNotificacoes,
  type Notificacao,
} from "../../lib/notificacoes";
import { NotificacaoItem } from "./NotificacaoItem";

interface NotificacoesPanelProps {
  id: string;
  aberto: boolean;
  onFechar: () => void;
}

/** O popover mostra as últimas 20; a página `/notificacoes` tem o resto. */
const MAX_NO_PAINEL = 20;

/**
 * Popover do sino (feature 272). Implementação própria calcada no `FilterDropdown`/`KebabMenu`
 * (fechar em clique fora e Esc fica no `NotificacoesBell`, que é dono do estado). `z-30` é a
 * camada de popover do app — abaixo de diálogo, acima do cromo fixo das páginas.
 *
 * Posição: no desktop abre para a DIREITA da linha da marca da sidebar (`lg:left-full`), sobre o
 * `main`; no mobile, sob a barra superior, ancorado à direita. Dados só são pedidos com o painel
 * aberto (`enabled`), e a cada abertura vêm frescos (`staleTime: 0`).
 */
export function NotificacoesPanel({ id, aberto, onFechar }: NotificacoesPanelProps) {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const tituloRef = useRef<HTMLHeadingElement>(null);
  const lista = useNotificacoes(false, aberto);
  const marcarLida = useMarcarLida();
  const marcarTodas = useMarcarTodasLidas();

  const itens = (lista.data?.pages.flatMap((p) => p.items) ?? []).slice(0, MAX_NO_PAINEL);
  const naoLidas = lista.data?.pages[0]?.unread_count ?? 0;
  const maiorId = itens[0]?.id;
  const grupos = agruparPorDia(itens);

  // Foco no título ao abrir: leitor de tela anuncia o diálogo; o `NotificacoesBell` devolve o
  // foco ao sino ao fechar.
  useEffect(() => {
    if (aberto) tituloRef.current?.focus();
  }, [aberto]);

  function abrir(item: Notificacao) {
    if (item.read_at === null) marcarLida.mutate(item.id);
    onFechar();
    if (item.link_path) navigate(item.link_path);
  }

  return (
    <AnimatePresence>
      {aberto && (
        <motion.div
          id={id}
          role="dialog"
          aria-label="Notificações"
          initial={reduceMotion ? undefined : { opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="absolute right-0 top-full z-30 mt-2 flex max-h-[70vh] w-[22rem] max-w-[calc(100vw-1rem)] flex-col overflow-hidden rounded-md border border-line bg-panel text-ink shadow-lg lg:left-full lg:right-auto lg:top-0 lg:ml-3 lg:mt-0"
        >
          <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
            <h2 ref={tituloRef} tabIndex={-1} className="text-sm font-semibold outline-none">
              Notificações
            </h2>
            <button
              type="button"
              disabled={naoLidas === 0 || !maiorId || marcarTodas.isPending}
              onClick={() => maiorId && marcarTodas.mutate(maiorId)}
              className="text-xs font-semibold text-accent hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
            >
              {marcarTodas.isPending ? "Marcando..." : "Marcar todas como lidas"}
            </button>
          </div>
          {marcarTodas.isError && (
            <p role="alert" className="border-b border-line px-3 py-1.5 text-xs text-red">
              Não foi possível marcar como lidas. Tente de novo.
            </p>
          )}

          <div className="flex-1 overflow-y-auto py-1">
            {lista.isLoading && (
              <div className="space-y-2 px-3 py-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-8 w-8 rounded-full" />
                    <div className="flex-1 space-y-1">
                      <Skeleton className="h-3.5 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {lista.isError && (
              <div className="px-3 py-6 text-center text-sm text-muted">
                Não foi possível carregar as notificações.
                <button
                  type="button"
                  onClick={() => void lista.refetch()}
                  className="ml-2 font-semibold text-accent hover:underline"
                >
                  Tentar de novo
                </button>
              </div>
            )}
            {!lista.isLoading && !lista.isError && itens.length === 0 && (
              // O vazio de um sistema novo precisa ensinar o que vai aparecer.
              <p className="px-4 py-8 text-center text-sm text-muted">
                Nada por aqui. Quando chegar uma resposta de formulário, uma avaliação de cliente
                ou uma recusa de convite, o aviso aparece neste sino.
              </p>
            )}
            {grupos.map((grupo) => (
              <div key={grupo.rotulo}>
                <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  {grupo.rotulo}
                </div>
                {grupo.itens.map((item) => (
                  <NotificacaoItem key={item.id} item={item} onOpen={abrir} />
                ))}
              </div>
            ))}
          </div>

          <div className="border-t border-line px-3 py-2 text-right">
            <Link
              to="/notificacoes"
              onClick={onFechar}
              className="text-xs font-semibold text-accent hover:underline"
            >
              Ver todas
            </Link>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
