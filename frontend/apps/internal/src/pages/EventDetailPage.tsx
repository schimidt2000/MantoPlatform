import { Link, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Skeleton } from "@manto/ui";
import { useEvent, type EventoDetalhe } from "../lib/agenda";
import { CastingSection } from "../components/EventDetail/CastingSection";
import { ComercialSection } from "../components/EventDetail/ComercialSection";
import { EventHeader } from "../components/EventDetail/EventHeader";
import { FeedbackSection } from "../components/EventDetail/FeedbackSection";
import { FigurinoSection } from "../components/EventDetail/FigurinoSection";
import { FinanceiroSection } from "../components/EventDetail/FinanceiroSection";
import { LogisticaSection } from "../components/EventDetail/LogisticaSection";
import {
  LogsSection,
  ObservacoesSection,
  WhatsAppSummary,
} from "../components/EventDetail/ObservacoesSection";
import { Empty, formatRange, Panel } from "../components/EventDetail/parts";

/**
 * Painel simplificado de ENSAIO: o servidor não serializa os blocos de show para esse tipo
 * de evento, então a tela mostra só o que existe (dados básicos + histórico).
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
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
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

/**
 * Detalhe do evento (`/events/:id`) — layout de duas colunas de alta densidade (feature 190).
 *
 * Coluna esquerda: operação (casting, equipe de apoio, figurino, logística/trajeto,
 * materiais de ensaio, observações). Coluna direita: comercial e financeiro (venda, grade de
 * resultado, contratos, notas, pagamentos, reembolsos). Abaixo das colunas, avaliações,
 * feedback da cliente e — só para SUPERADMIN — o log de atividades.
 *
 * Cada bloco só é renderizado quando o servidor o inclui no JSON: o RBAC decide o que existe
 * no payload, e a tela não tenta adivinhar permissões por conta própria.
 */
export function EventDetailPage() {
  const reduceMotion = useReducedMotion();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = useEvent(id);

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

      {query.data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <EventHeader data={query.data} />

          {query.data.event.is_ensaio ? (
            <div className="space-y-4">
              <EnsaioPanel data={query.data} />
              <LogsSection data={query.data} />
            </div>
          ) : (
            <>
              <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div className="space-y-4">
                  <WhatsAppSummary data={query.data} />
                  <CastingSection data={query.data} />
                  <FigurinoSection data={query.data} />
                  <LogisticaSection data={query.data} />
                  <ObservacoesSection data={query.data} />
                </div>
                <div className="space-y-4">
                  <ComercialSection data={query.data} />
                  <FinanceiroSection data={query.data} />
                </div>
              </div>

              <div className="mt-4 space-y-4">
                <FeedbackSection data={query.data} />
                <LogsSection data={query.data} />
              </div>
            </>
          )}
        </motion.div>
      )}
    </div>
  );
}
