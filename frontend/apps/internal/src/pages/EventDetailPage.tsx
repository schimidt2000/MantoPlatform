import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@manto/ui";
import { useEvent, type EventoDetalhe } from "../lib/agenda";
import { CastingSection } from "../components/EventDetail/CastingSection";
import { ComercialSection } from "../components/EventDetail/ComercialSection";
import { EnsaioSection } from "../components/EventDetail/EnsaioSection";
import { EventHeader } from "../components/EventDetail/EventHeader";
import { FeedbackSection } from "../components/EventDetail/FeedbackSection";
import { FigurinoSection } from "../components/EventDetail/FigurinoSection";
import { FinanceiroSection } from "../components/EventDetail/FinanceiroSection";
import { LogisticaSection } from "../components/EventDetail/LogisticaSection";
import { Presente3DSection } from "../components/EventDetail/Presente3DSection";
import { PedidoVirtualSection } from "../components/EventDetail/PedidoVirtualSection";
import { DadosEventoPanel, PendenciasStrip } from "../components/EventDetail/ResumoSection";
import {
  LogsSection,
  ObservacoesSection,
  WhatsAppSummary,
} from "../components/EventDetail/ObservacoesSection";
import { Empty, formatRange, Panel } from "../components/EventDetail/parts";

/**
 * Grade de duas colunas no desktop; no mobile tudo empilha em coluna única.
 *
 * `[&>*]:min-w-0` não é enfeite: item de grid nasce com `min-width: auto`, ou seja, se recusa a
 * encolher abaixo da largura intrínseca do conteúdo. O `minmax(0,1fr)` do template só entra em
 * cena a partir do `xl` — abaixo disso a coluna única estourava a viewport do celular (o card
 * de casting empurrava a página para 413px num aparelho de 375) e a tela rolava na horizontal.
 */
const DUAS_COLUNAS =
  "grid items-start gap-4 [&>*]:min-w-0 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]";

/**
 * Painel simplificado de ENSAIO: o servidor não serializa os blocos de show para esse tipo
 * de evento, então a tela mostra só o que existe (dados básicos + histórico) — sem abas, que
 * não teriam o que separar.
 */
function EnsaioPanel({ data }: { data: EventoDetalhe }) {
  return (
    <Panel title="Ensaio">
      <p className="text-sm text-ink">{formatRange(data.event.start_at, data.event.end_at)}</p>
      {data.event.location && <p className="text-sm text-muted">{data.event.location}</p>}
      {!data.event.location && <Empty>Sem local definido.</Empty>}
    </Panel>
  );
}

/** Esqueleto de carregamento com a mesma silhueta de duas colunas da tela final. */
function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-9 w-80" />
      <div className={DUAS_COLUNAS}>
        <div className="space-y-4">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    </div>
  );
}

interface AbaDef {
  value: string;
  label: string;
  render: () => JSX.Element;
}

/**
 * Abas disponíveis para este evento e este usuário (feature 215).
 *
 * A aba só existe se o payload trouxe algum bloco dela: o RBAC do servidor decide o que
 * existe, e a tela não tenta adivinhar permissão por conta própria (mesma regra que já valia
 * painel a painel). "Resumo" e "Produção" são universais — todo mundo que abre o evento vê o
 * cabeçalho e a operação.
 */
function montarAbas(data: EventoDetalhe, irPara: (tab: string) => void): AbaDef[] {
  const abas: AbaDef[] = [
    {
      value: "resumo",
      label: "Resumo",
      render: () => (
        <>
          <PendenciasStrip data={data} onNavigate={irPara} />
          <div className={DUAS_COLUNAS}>
            <div className="space-y-4">
              <DadosEventoPanel data={data} />
            </div>
            <div className="space-y-4">
              <WhatsAppSummary data={data} />
              <ObservacoesSection data={data} />
            </div>
          </div>
        </>
      ),
    },
    {
      value: "producao",
      label: "Produção",
      render: () => (
        <div className="space-y-4">
          <div className={DUAS_COLUNAS}>
            <div className="space-y-4">
              <CastingSection data={data} />
            </div>
            <div className="space-y-4">
              <FigurinoSection data={data} />
              <EnsaioSection data={data} />
            </div>
          </div>
          <LogisticaSection data={data} />
          <Presente3DSection data={data} />
          <PedidoVirtualSection data={data} />
        </div>
      ),
    },
  ];

  const temComercial = Boolean(
    data.venda ||
      data.kpi ||
      data.contratos ||
      data.notas_fiscais ||
      data.pagamentos ||
      data.reembolsos,
  );
  if (temComercial) {
    abas.push({
      value: "comercial",
      label: "Comercial",
      render: () => (
        <div className={DUAS_COLUNAS}>
          <div className="space-y-4">
            <ComercialSection data={data} />
          </div>
          <div className="space-y-4">
            <FinanceiroSection data={data} />
          </div>
        </div>
      ),
    });
  }

  const temHistorico = Boolean(data.ratings || data.client_feedbacks || data.logs);
  if (temHistorico) {
    abas.push({
      value: "historico",
      label: "Histórico",
      render: () => (
        <div className="space-y-4">
          <FeedbackSection data={data} />
          <LogsSection data={data} />
        </div>
      ),
    });
  }

  return abas;
}

/**
 * Detalhe do evento (`/events/:id`) — tela de abas (feature 215, sucede o mural de duas
 * colunas da 190).
 *
 * A 190 empilhava os 16 painéis de uma vez; para o superadmin, que recebe todos, a tela virava
 * uma parede de ~4000px sem hierarquia, e no mobile uma coluna só, interminável. Aqui o evento
 * é lido em quatro atos — **Resumo** (o que é e o que falta), **Produção** (casting, figurino,
 * logística, ensaios), **Comercial** (venda, resultado e anexos financeiros) e **Histórico** —
 * e cada bloco é editado onde é exibido, sem desviar para o formulário grande.
 *
 * A aba ativa vive na URL (`?aba=producao`): recarregar, voltar no navegador ou mandar o link
 * para alguém cai na mesma aba. Os chips de pendência do Resumo navegam por aqui.
 */
export function EventDetailPage() {
  const reduceMotion = useReducedMotion();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = useEvent(id);
  const [searchParams, setSearchParams] = useSearchParams();

  // `replace` para a troca de aba não encher o histórico de voltas; os demais parâmetros da
  // URL são preservados (a aba é só mais um deles, não a query inteira).
  const irPara = (tab: string) =>
    setSearchParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        proximo.set("aba", tab);
        return proximo;
      },
      { replace: true },
    );
  const data = query.data;
  const abas = useMemo(() => (data ? montarAbas(data, irPara) : []), [data]);

  // Uma `?aba=` inexistente (link antigo, papel sem aquele bloco) cai no Resumo em vez de
  // renderizar uma tela vazia.
  const pedida = searchParams.get("aba");
  const abaAtiva = abas.some((a) => a.value === pedida) ? pedida! : "resumo";

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6">
      {query.isLoading && <DetailSkeleton />}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o evento.{" "}
          <Button asChild variant="ghost" size="sm">
            <Link to="/agenda">Voltar para a Agenda</Link>
          </Button>
        </div>
      )}

      {data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <EventHeader data={data} />

          {data.event.is_ensaio ? (
            <div className="space-y-4">
              <EnsaioPanel data={data} />
              {/* Gestão do ensaio (editar/cancelar/vincular órfão) — restaurada na 206. */}
              <EnsaioSection data={data} />
              <LogsSection data={data} />
            </div>
          ) : (
            <Tabs value={abaAtiva} onValueChange={irPara}>
              {/* Fica colada no topo ao rolar: com painéis longos, trocar de aba não pode
                  exigir voltar ao começo da página. `top-14` desvia da barra do app, que é
                  sticky só abaixo de `lg` (`AppLayout`); a partir daí o topo está livre. O
                  -mx/px devolve a sangria no mobile, onde a régua rola na horizontal em vez
                  de quebrar em duas linhas. */}
              <div className="sticky top-14 z-20 -mx-4 mb-4 overflow-x-auto bg-surface/95 px-4 py-2 backdrop-blur sm:mx-0 sm:px-0 lg:top-0">
                <TabsList className="w-max">
                  {/* `px-3` no mobile é o que faz as quatro abas caberem em 375px sem rolar
                      (com `px-4` a régua dava 382px e a última ficava cortada). */}
                  {abas.map((aba) => (
                    <TabsTrigger key={aba.value} value={aba.value} className="h-9 px-3 sm:px-4">
                      {aba.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </div>

              {abas.map((aba) => (
                <TabsContent key={aba.value} value={aba.value} className="mt-0">
                  {aba.render()}
                </TabsContent>
              ))}
            </Tabs>
          )}
        </motion.div>
      )}
    </div>
  );
}
