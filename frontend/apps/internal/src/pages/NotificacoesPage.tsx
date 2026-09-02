import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton, Tabs, TabsList, TabsTrigger } from "@manto/ui";
import { NotificacaoItem } from "../components/notificacoes/NotificacaoItem";
import {
  agruparPorDia,
  useMarcarLida,
  useMarcarTodasLidas,
  useNotificacoes,
  type Notificacao,
} from "../lib/notificacoes";

type Aba = "nao-lidas" | "todas";

/**
 * `/notificacoes` (feature 272) — a caixa completa, acessível pelo "Ver todas" do sino; sem item
 * de menu de propósito (a sidebar já tem ~30 itens e no celular o item sumiria no drawer).
 * Abas "Não lidas"/"Todas", paginação por cursor ("Carregar mais") e a mesma `NotificacaoItem` do
 * popover. Na aba "Não lidas" a linha sai da lista ao ser lida (200 ms, respeitando reduced motion).
 */
export function NotificacoesPage() {
  const [aba, setAba] = useState<Aba>("nao-lidas");
  const somenteNaoLidas = aba === "nao-lidas";
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const lista = useNotificacoes(somenteNaoLidas);
  const marcarLida = useMarcarLida();
  const marcarTodas = useMarcarTodasLidas();

  const itens = lista.data?.pages.flatMap((p) => p.items) ?? [];
  const naoLidas = lista.data?.pages[0]?.unread_count ?? 0;
  const maiorId = itens[0]?.id;
  const grupos = agruparPorDia(itens);

  function abrir(item: Notificacao) {
    if (item.read_at === null) marcarLida.mutate(item.id);
    if (item.link_path) navigate(item.link_path);
  }

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <PageHeader
        title="Notificações"
        subtitle="Respostas de formulário, avaliações de clientes e recusas de convite — o que antes chegava por e-mail."
        actions={
          <Button
            type="button"
            disabled={naoLidas === 0 || !maiorId || marcarTodas.isPending}
            loading={marcarTodas.isPending}
            onClick={() => maiorId && marcarTodas.mutate(maiorId)}
          >
            Marcar todas como lidas
          </Button>
        }
        filters={
          <Tabs value={aba} onValueChange={(valor) => setAba(valor as Aba)}>
            <TabsList>
              <TabsTrigger value="nao-lidas">
                Não lidas{naoLidas > 0 ? ` (${naoLidas})` : ""}
              </TabsTrigger>
              <TabsTrigger value="todas">Todas</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />

      {marcarTodas.isError && (
        <p role="alert" className="mb-3 rounded-md bg-red-soft px-3 py-2 text-sm text-red">
          Não foi possível marcar como lidas. Tente de novo.
        </p>
      )}

      <div className="rounded-lg border border-line bg-panel">
        {lista.isLoading && (
          <div className="space-y-3 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-3.5 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        )}
        {lista.isError && (
          <div className="p-8 text-center text-sm text-muted">
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
          <p className="p-10 text-center text-sm text-muted">
            {somenteNaoLidas
              ? "Tudo lido. Quando chegar uma resposta de formulário, uma avaliação de cliente ou uma recusa de convite, ela aparece aqui."
              : "Nenhuma notificação ainda."}
          </p>
        )}
        {grupos.map((grupo) => (
          <section key={grupo.rotulo} aria-label={grupo.rotulo}>
            <h2 className="border-b border-line bg-surface-2/60 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
              {grupo.rotulo}
            </h2>
            <ul className="divide-y divide-line">
              <AnimatePresence initial={false}>
                {grupo.itens.map((item) => (
                  <motion.li
                    key={item.id}
                    layout={!reduceMotion}
                    initial={false}
                    exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <NotificacaoItem item={item} onOpen={abrir} />
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </section>
        ))}
        {lista.hasNextPage && (
          <div className="border-t border-line p-3 text-center">
            <Button
              type="button"
              variant="outline"
              onClick={() => void lista.fetchNextPage()}
              disabled={lista.isFetchingNextPage}
              loading={lista.isFetchingNextPage}
            >
              Carregar mais
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
