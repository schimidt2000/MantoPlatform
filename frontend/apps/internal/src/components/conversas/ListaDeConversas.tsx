import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Search } from "lucide-react";
import { Button, Input, Skeleton, cn } from "@manto/ui";
import {
  contatoLegivel,
  horaNaLista,
  tempoDeEspera,
  type Canal,
  type ConversaResumo,
  type DiasDoParado,
  type FiltroDaLista as Filtro,
  type RecorteDaLista,
} from "../../lib/conversas";
import { AvisosNoCelular } from "./AvisosNoCelular";
import { FiltroDaLista, FiltroDoCanal, FiltroDoRecorte } from "./FiltroDaLista";
import { IconeDoCanal } from "./IconeDoCanal";
import { SelosDaVenda } from "./SelosDaVenda";

/**
 * A lista de conversas (feature 325, FR-013): da última mensagem para trás, com a busca por nome
 * ou telefone, o telefone, o trecho da última mensagem e a contagem de não lidas da equipe.
 * O topo se atualiza sozinho; as páginas antigas vêm pelo "Carregar mais", sem polling.
 *
 * Feature 328: o filtro por responsável, o nome de quem atende e, com a cliente esperando, "há N
 * min" — em vermelho a partir de 15 min, recontado a cada minuto sem nova requisição.
 */

interface ListaDeConversasProps {
  busca: string;
  onBusca: (valor: string) => void;
  filtro: Filtro;
  onFiltro: (valor: Filtro) => void;
  canal: Canal | null;
  onCanal: (valor: Canal | null) => void;
  /** Feature 330: o filtro de canal só aparece com mais de um canal ligado. */
  canaisLigados: Canal[];
  /** Feature 349: o recorte da venda e os dias do orçamento parado. */
  recorte: RecorteDaLista | null;
  onRecorte: (valor: RecorteDaLista | null) => void;
  dias: DiasDoParado;
  onDias: (dias: DiasDoParado) => void;
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

/** O relógio da espera: um "agora" que anda de minuto em minuto. */
function useAgoraPorMinuto(): number {
  const [agora, setAgora] = useState(() => Date.now());
  useEffect(() => {
    const relogio = setInterval(() => setAgora(Date.now()), 60_000);
    return () => clearInterval(relogio);
  }, []);
  return agora;
}

function LinhaDaEquipe({ conversa, agora }: { conversa: ConversaResumo; agora: number }) {
  const espera = tempoDeEspera(conversa.aguardando_desde, agora);
  return (
    <span className="flex items-center justify-between gap-2 text-xs">
      <span className="truncate text-muted">
        {conversa.responsavel ? conversa.responsavel.nome : "Sem responsável"}
      </span>
      {espera ? (
        <span className={cn("shrink-0", espera.urgente ? "font-semibold text-red" : "text-muted")}>
          Esperando {espera.texto}
        </span>
      ) : null}
    </span>
  );
}

function ItemDaLista({
  conversa,
  selecionada,
  onSelecionar,
  agora,
}: {
  conversa: ConversaResumo;
  selecionada: boolean;
  onSelecionar: (id: number) => void;
  agora: number;
}) {
  const contato = contatoLegivel(conversa);
  const mostrarContato = contato && contato !== conversa.nome;
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
          <span className="flex min-w-0 items-center gap-1.5">
            <IconeDoCanal canal={conversa.canal} />
            <span className={cn("truncate text-sm", conversa.nao_lidas > 0 ? "font-semibold" : "font-medium")}>
              {conversa.nome}
            </span>
          </span>
          <span className="shrink-0 text-xs text-muted">{horaNaLista(conversa.ultima_mensagem_em)}</span>
        </span>
        {mostrarContato ? <span className="block truncate text-xs text-muted">{contato}</span> : null}
        <span className="flex items-center justify-between gap-2">
          <span className="truncate text-xs text-muted">{conversa.ultima_previa ?? ""}</span>
          {conversa.nao_lidas > 0 ? (
            <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-on-color">
              <span className="sr-only">Não lidas: </span>
              {conversa.nao_lidas}
            </span>
          ) : null}
        </span>
        <LinhaDaEquipe conversa={conversa} agora={agora} />
        <SelosDaVenda venda={conversa.venda} />
      </span>
    </button>
  );
}

export function ListaDeConversas({
  busca,
  onBusca,
  filtro,
  onFiltro,
  canal,
  onCanal,
  canaisLigados,
  recorte,
  onRecorte,
  dias,
  onDias,
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
  const agora = useAgoraPorMinuto();
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="space-y-2 border-b border-line bg-panel p-3">
        <label htmlFor="busca-conversas" className="sr-only">
          Buscar conversa
        </label>
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
            <Input
              id="busca-conversas"
              value={busca}
              onChange={(e) => onBusca(e.target.value)}
              placeholder="Buscar por nome ou telefone"
              className="pl-9"
            />
          </div>
          <AvisosNoCelular />
        </div>
        <FiltroDaLista valor={filtro} onMudar={onFiltro} />
        {canaisLigados.length > 1 ? <FiltroDoCanal valor={canal} onMudar={onCanal} /> : null}
        <FiltroDoRecorte valor={recorte} onMudar={onRecorte} dias={dias} onDias={onDias} />
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
          <p className="p-6 text-center text-sm text-muted">
            {recorte === "esperando"
              ? "Nenhuma conversa esperando resposta."
              : recorte === "orcamento_parado"
                ? `Nenhum orçamento parado há ${dias} dias ou mais.`
                : recorte === "anuncio"
                  ? "Nenhuma conversa de anúncio encontrada."
                  : filtro === "minhas"
                    ? "Nenhuma conversa sua encontrada."
                    : filtro === "sem_responsavel"
                      ? "Nenhuma conversa sem responsável encontrada."
                      : "Nenhuma conversa encontrada."}
          </p>
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
                      agora={agora}
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
