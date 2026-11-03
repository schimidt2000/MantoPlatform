import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { MessageCircle } from "lucide-react";
import { cn } from "@manto/ui";
import { ConversaAberta } from "../components/conversas/ConversaAberta";
import { ListaDeConversas } from "../components/conversas/ListaDeConversas";
import {
  intervaloDaLista,
  useConversas,
  useConversasAnteriores,
  type ConversaResumo,
  type FiltroDaLista,
} from "../lib/conversas";

/**
 * Conversas (feature 325) — o WhatsApp da Manto dentro da Plataforma.
 *
 * No computador, lista e conversa lado a lado; no celular (até 767 px), uma de cada vez, com
 * "Voltar" (FR-020). A conversa aberta, a busca e o filtro moram no endereço (`?c=`, `?busca=`,
 * `?filtro=`, sempre `replace` — feature 320), então recarregar ou voltar não perde o lugar.
 */

const ESPERA_DA_BUSCA_MS = 300;
const FILTROS: FiltroDaLista[] = ["todas", "minhas", "sem_responsavel"];

function filtroDoEndereco(valor: string | null): FiltroDaLista {
  return FILTROS.find((f) => f === valor) ?? "todas";
}

/** Topo (com polling) + páginas antigas, sem repetir a conversa que subiu para o topo. */
function juntarPaginas(topo: ConversaResumo[] | undefined, antigas: ConversaResumo[][]): ConversaResumo[] | undefined {
  if (!topo) return undefined;
  const vistas = new Set(topo.map((c) => c.id));
  return [...topo, ...antigas.flat().filter((c) => (vistas.has(c.id) ? false : (vistas.add(c.id), true)))];
}

export function ConversasPage() {
  const reduzir = useReducedMotion();
  const [params, setParams] = useSearchParams();
  const selecionada = Number(params.get("c")) || null;
  const [busca, setBusca] = useState(params.get("busca") ?? "");
  const [buscaEfetiva, setBuscaEfetiva] = useState(busca);
  const filtro = filtroDoEndereco(params.get("filtro"));
  const [cursorDaLista, setCursorDaLista] = useState<string | null>(null);
  const lista = useConversas(buscaEfetiva, filtro);
  const anteriores = useConversasAnteriores(buscaEfetiva, filtro, cursorDaLista);

  useEffect(() => {
    const espera = setTimeout(() => {
      setBuscaEfetiva(busca.trim());
      setCursorDaLista(null);
      setParams(
        (atuais) => {
          const novos = new URLSearchParams(atuais);
          if (busca.trim()) novos.set("busca", busca.trim());
          else novos.delete("busca");
          return novos;
        },
        { replace: true },
      );
    }, ESPERA_DA_BUSCA_MS);
    return () => clearTimeout(espera);
  }, [busca, setParams]);

  const conversas = useMemo(
    () => juntarPaginas(lista.data?.conversas, (anteriores.data?.pages ?? []).map((p) => p.conversas)),
    [lista.data, anteriores.data],
  );
  const temMais = cursorDaLista === null ? Boolean(lista.data?.proximo) : Boolean(anteriores.hasNextPage);

  const filtrar = (valor: FiltroDaLista) => {
    setCursorDaLista(null);
    setParams(
      (atuais) => {
        const novos = new URLSearchParams(atuais);
        if (valor === "todas") novos.delete("filtro");
        else novos.set("filtro", valor);
        return novos;
      },
      { replace: true },
    );
  };

  const selecionar = (id: number | null) =>
    setParams(
      (atuais) => {
        const novos = new URLSearchParams(atuais);
        if (id) novos.set("c", String(id));
        else novos.delete("c");
        return novos;
      },
      { replace: true },
    );

  if (lista.data && !lista.data.configurado) {
    return (
      <div className="mx-auto max-w-xl p-6 text-center">
        <MessageCircle className="mx-auto mb-3 h-10 w-10 text-muted" aria-hidden />
        <h1 className="text-lg font-semibold">Conversas</h1>
        <p className="mt-2 text-sm text-muted">
          O WhatsApp ainda não foi configurado. Peça ao Superadmin para preencher as chaves no Render.
        </p>
      </div>
    );
  }

  return (
    // Altura da janela menos a barra do topo do celular (56 px); no computador não há barra.
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-[420px] flex-col md:h-[100dvh]">
      {lista.data?.envio_travado ? (
        <p role="status" className="border-b border-gold bg-gold-50 px-4 py-2 text-xs text-gold-ink">
          O envio pelo WhatsApp está travado neste ambiente: as mensagens não saem para o celular da cliente.
        </p>
      ) : null}
      <div className="grid min-h-0 flex-1 md:grid-cols-[minmax(280px,360px)_1fr] [&>*]:min-w-0">
        <section
          aria-label="Lista de conversas"
          className={cn("min-h-0 border-r border-line bg-panel", selecionada ? "hidden md:block" : "block")}
        >
          <ListaDeConversas
            busca={busca}
            onBusca={setBusca}
            filtro={filtro}
            onFiltro={filtrar}
            conversas={conversas}
            carregando={lista.isLoading}
            falhou={lista.isError}
            buscando={lista.isFetching}
            onTentarDeNovo={() => void lista.refetch()}
            temMais={temMais}
            carregandoMais={anteriores.isFetching}
            onCarregarMais={() =>
              cursorDaLista === null ? setCursorDaLista(lista.data?.proximo ?? null) : void anteriores.fetchNextPage()
            }
            selecionada={selecionada}
            onSelecionar={selecionar}
          />
        </section>
        <section
          aria-label="Conversa aberta"
          className={cn("min-h-0 bg-surface", selecionada ? "block" : "hidden md:block")}
        >
          {/* Só entrada (a `key` remonta): uma saída com `AnimatePresence mode="wait"` trava a troca
              quando a aba não pinta quadros — a conversa nova nunca entrava. */}
          <motion.div
            key={selecionada ?? "nenhuma"}
            className="h-full"
            initial={reduzir ? false : { opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            {selecionada ? (
              <ConversaAberta
                conversaId={selecionada}
                intervaloMs={intervaloDaLista(lista.data)}
                onVoltar={() => selecionar(null)}
              />
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted">
                Selecione uma conversa para ler e responder.
              </div>
            )}
          </motion.div>
        </section>
      </div>
    </div>
  );
}
