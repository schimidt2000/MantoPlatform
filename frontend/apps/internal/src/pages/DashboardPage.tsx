import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, MetricBadge, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import type {
  DashboardSummary,
  DashboardTaskRef,
  EnsaioEventRef,
  EnsaioSummary,
  MinhaPecaRef,
  PendingPayment,
  UnconfirmedInviteRef,
} from "../lib/types";
import { SectorPanel, getUrgency } from "../components/SectorPanel";

function DashboardSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-32 w-full" />
      ))}
    </div>
  );
}

function TaskRow({ task }: { task: DashboardTaskRef }) {
  const urgency = getUrgency(task.start_at);
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 font-medium text-ink">
          {task.character_name}
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
        </div>
        <Link to={`/events/${task.event_id}`} className="text-muted hover:underline">
          {task.event_title}
          {task.start_at && ` — ${new Date(task.start_at).toLocaleDateString("pt-BR")}`}
        </Link>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${task.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/**
 * Linha de "quem ainda não confirmou" (feature 231).
 *
 * Mostra a ação certa para cada caso, que é o que a lista existe para responder: convite enviado
 * e sem resposta vira cobrança no WhatsApp; convite nunca enviado é o casting que precisa mandar,
 * e aí o caminho é abrir o evento. Também diz quantos lembretes automáticos já saíram, para
 * ninguém cobrar de novo quem o robô acabou de cobrar.
 */
function UnconfirmedRow({ item }: { item: UnconfirmedInviteRef }) {
  const urgency = getUrgency(item.start_at);
  const nuncaEnviado = item.invite_status !== "pending";
  const zap = item.whatsapp
    ? `https://wa.me/${item.whatsapp.replace(/\D/g, "")}?text=${encodeURIComponent(
        `Oi, ${item.talent_name}! Falta você confirmar no portal a sua presença em "${item.event_title}". Consegue responder por lá?`,
      )}`
    : null;

  return (
    <div
      className="-mx-4 flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {item.talent_name}
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
          <MetricBadge tone={nuncaEnviado ? "red" : "neutral"} size="xs">
            {nuncaEnviado ? "convite não enviado" : "sem resposta"}
          </MetricBadge>
          {item.reminder_count > 0 && (
            <span className="text-[11px] text-muted">
              {item.reminder_count} lembrete{item.reminder_count > 1 ? "s" : ""} enviado
              {item.reminder_count > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <Link to={`/events/${item.event_id}`} className="text-muted hover:underline">
          {item.character_name} · {item.event_title}
          {item.start_at && ` — ${new Date(item.start_at).toLocaleDateString("pt-BR")}`}
        </Link>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {zap && !nuncaEnviado && (
          <Button asChild variant="outline" size="sm">
            <a href={zap} target="_blank" rel="noopener">
              Cobrar no WhatsApp
            </a>
          </Button>
        )}
        <Button asChild variant={nuncaEnviado ? "default" : "outline"} size="sm">
          <Link to={`/events/${item.event_id}`}>{nuncaEnviado ? "Enviar convite" : "Abrir"}</Link>
        </Button>
      </div>
    </div>
  );
}

/** Linha de evento do painel de Ensaio (sem cargo — o link é o próprio evento). */
function EnsaioEventRow({ item, extra }: { item: EnsaioEventRef; extra?: string }) {
  const urgency = getUrgency(item.start_at);
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 font-medium text-ink">
          <Link to={`/events/${item.event_id}`} className="min-w-0 truncate hover:underline">
            {item.event_title}
          </Link>
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
        </div>
        <div className="text-muted">
          {item.start_at && new Date(item.start_at).toLocaleDateString("pt-BR")}
          {extra && ` — ${extra}`}
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${item.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/** Sub-lista com título dentro do painel de Ensaio. */
function EnsaioGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-1 pt-2 first:pt-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {children}
    </div>
  );
}

/**
 * Painel do papel ENSAIO — as quatro listas restauradas da home Jinja (206): shows a
 * agendar, agendados, ensaios órfãos e a vaga de Técnico de Som (Presença) sem talento.
 */
function EnsaioPanel({ summary }: { summary: EnsaioSummary }) {
  const pendencias =
    summary.pending.length + summary.orphans.length + summary.pending_presence.length;
  return (
    <SectorPanel title="🎭 Ensaio" count={pendencias}>
      <div className="space-y-3">
        <EnsaioGroup title={`A agendar (${summary.pending.length})`}>
          {summary.pending.length === 0 ? (
            <p className="py-1 text-sm text-muted">Nenhum show esperando ensaio.</p>
          ) : (
            summary.pending.map((item) => <EnsaioEventRow key={item.event_id} item={item} />)
          )}
        </EnsaioGroup>

        <EnsaioGroup title={`Presença pendente (${summary.pending_presence.length})`}>
          {summary.pending_presence.length === 0 ? (
            <p className="py-1 text-sm text-muted">Técnico definido em todos os shows.</p>
          ) : (
            summary.pending_presence.map((t) => (
              <TaskRow key={t.role_id ?? `${t.event_id}-presenca`} task={t} />
            ))
          )}
        </EnsaioGroup>

        {summary.orphans.length > 0 && (
          <EnsaioGroup title={`Ensaios órfãos (${summary.orphans.length})`}>
            {summary.orphans.map((item) => (
              <EnsaioEventRow key={item.event_id} item={item} extra="show original removido" />
            ))}
          </EnsaioGroup>
        )}

        {summary.scheduled.length > 0 && (
          <EnsaioGroup title={`Agendados (${summary.scheduled.length})`}>
            {summary.scheduled.map((item) => (
              <EnsaioEventRow
                key={item.event_id}
                item={item}
                extra={`ensaio: ${item.ensaios
                  .filter(Boolean)
                  .map((iso) =>
                    new Date(iso as string).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                    }),
                  )
                  .join(", ")}`}
              />
            ))}
          </EnsaioGroup>
        )}
      </div>
    </SectorPanel>
  );
}

const SEVERITY_TONE: Record<PendingPayment["severity"], "red" | "gold" | "neutral"> = {
  atrasado: "red",
  vencido: "red",
  urgent: "red",
  warn: "gold",
  info: "neutral",
};

const SEVERITY_ROW_BG: Partial<Record<PendingPayment["severity"], string>> = {
  atrasado: "rgba(228,88,88,0.06)",
  vencido: "rgba(228,88,88,0.06)",
  urgent: "rgba(228,88,88,0.06)",
  warn: "rgba(245,200,66,0.06)",
};

function PendingPaymentRow({ item }: { item: PendingPayment }) {
  const rowBg = SEVERITY_ROW_BG[item.severity];
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={rowBg ? { background: rowBg } : undefined}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 font-medium text-ink">
          <Link to={`/events/${item.event_id}`} className="hover:underline">
            {item.event_title}
          </Link>
          <MetricBadge tone={SEVERITY_TONE[item.severity]} size="xs">
            {item.severity.toUpperCase()}
          </MetricBadge>
        </div>
        <div className="text-muted">
          Recebido R$ {formatBRL(item.received)} de R$ {formatBRL(item.sale)} — falta R${" "}
          {formatBRL(item.saldo)}
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${item.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/**
 * Uma peça de figurino sob responsabilidade de quem está logado (feature 225).
 *
 * Não reusa `TaskRow` porque a urgência aqui não vem de `start_at` do evento e sim do prazo do
 * pedido — que pode ser bem antes do show, e é justamente o que se perde de vista hoje.
 */
function MinhaPecaRow({ item }: { item: MinhaPecaRef }) {
  const dias = item.dias_para_prazo;
  // "Não pode ir para evento" é crítico mesmo sem prazo apertado: o boneco está fora de uso.
  const critico = item.impede_uso || item.is_late || (dias != null && dias <= 2);
  const rotulo = item.is_late
    ? `ATRASADO ${Math.abs(dias ?? 0)}d`
    : dias == null
      ? null
      : dias === 0
        ? "HOJE"
        : `${dias}d`;
  const contexto = item.figurino_sheet_name ?? item.event_title;

  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={critico ? { background: "rgba(228,88,88,0.06)" } : undefined}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {item.title}
          {item.impede_uso && (
            <MetricBadge tone="red" size="xs">
              NÃO PODE IR
            </MetricBadge>
          )}
          {rotulo && (
            <MetricBadge tone={critico ? "red" : "neutral"} size="xs">
              {rotulo}
            </MetricBadge>
          )}
        </div>
        <span className="text-muted">
          {item.kind_label} · {item.status_label}
          {contexto && ` — ${contexto}`}
        </span>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/figurinos/producao/${item.id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

export function DashboardPage() {
  const reduceMotion = useReducedMotion();
  const { data: user } = useCurrentUser();

  const dashboard = useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<DashboardSummary>("/api/dashboard"),
  });

  return (
    <div className="w-full px-6 py-6 sm:px-8">
      <PageHeader title="Início" subtitle={user ? `Olá, ${user.name}` : undefined} />

      {dashboard.isLoading && <DashboardSkeleton />}

      {dashboard.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o resumo. Tente novamente em instantes.
        </div>
      )}

      {dashboard.data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-3"
        >
          {/* Primeiro painel da home de propósito (feature 225): é o único pessoal — o que está
              nas mãos de quem está lendo. Só aparece para quem tem peça sob sua responsabilidade. */}
          {dashboard.data.figurino_producao && (
            <SectorPanel
              title="🧵 Minhas peças e compras"
              count={dashboard.data.figurino_producao.pending}
            >
              {dashboard.data.figurino_producao.items.map((item) => (
                <MinhaPecaRow key={item.id} item={item} />
              ))}
            </SectorPanel>
          )}

          {/* Caixa de entrada do setor (225b): manutenção quase sempre nasce sem dono, porque
              quem relata o defeito recebeu o feedback do evento e não é quem vai consertar. */}
          {dashboard.data.figurino_oficina && (
            <SectorPanel
              title="🪡 Oficina — sem responsável"
              count={dashboard.data.figurino_oficina.pending}
            >
              {dashboard.data.figurino_oficina.items.map((item) => (
                <MinhaPecaRow key={item.id} item={item} />
              ))}
            </SectorPanel>
          )}

          {dashboard.data.casting && (
            <SectorPanel title="👥 Casting" count={dashboard.data.casting.pending.length}>
              {dashboard.data.casting.pending.length === 0 ? (
                <p className="py-2 text-sm text-muted">Nenhuma pendência.</p>
              ) : (
                dashboard.data.casting.pending.map((t) => (
                  <TaskRow key={t.role_id ?? `${t.event_id}-${t.character_name}`} task={t} />
                ))
              )}
            </SectorPanel>
          )}

          {dashboard.data.casting && (
            <SectorPanel
              title="🙋 Confirmações pendentes"
              count={dashboard.data.casting.unconfirmed.length}
            >
              {dashboard.data.casting.unconfirmed.length === 0 ? (
                <p className="py-2 text-sm text-muted">Todo mundo confirmado. ✓</p>
              ) : (
                <>
                  {/* O robô só cobra quem JÁ recebeu convite, e só na semana do evento — quem
                      está com "convite não enviado" depende de alguém aqui. Dizer isso na tela
                      evita a suposição de que o automático resolve tudo. */}
                  <p className="py-2 text-xs text-muted">
                    A cobrança automática por e-mail alcança só quem já recebeu o convite, na
                    semana do evento, no máximo 2 vezes. Quem está como{" "}
                    <strong className="text-ink">convite não enviado</strong> depende de você.
                  </p>
                  {dashboard.data.casting.unconfirmed.map((item) => (
                    <UnconfirmedRow key={item.role_id ?? `${item.event_id}-${item.talent_id}`} item={item} />
                  ))}
                </>
              )}
            </SectorPanel>
          )}

          {dashboard.data.figurino && (
            <SectorPanel title="👗 Figurino" count={dashboard.data.figurino.pending.length}>
              {dashboard.data.figurino.pending.length === 0 ? (
                <p className="py-2 text-sm text-muted">Nenhuma pendência.</p>
              ) : (
                dashboard.data.figurino.pending.map((t) => (
                  <TaskRow key={t.role_id ?? `${t.event_id}-${t.character_name}`} task={t} />
                ))
              )}
            </SectorPanel>
          )}

          {dashboard.data.ensaio && <EnsaioPanel summary={dashboard.data.ensaio} />}

          {dashboard.data.comercial && (
            <SectorPanel title="💼 Comercial" count={dashboard.data.comercial.pending_payments.length}>
              {dashboard.data.comercial.pending_payments.length === 0 ? (
                <p className="py-2 text-sm text-muted">Nenhuma pendência comercial.</p>
              ) : (
                dashboard.data.comercial.pending_payments.map((p) => (
                  <PendingPaymentRow key={p.event_id} item={p} />
                ))
              )}
            </SectorPanel>
          )}

          {dashboard.data.financeiro && (
            <SectorPanel
              title="🔁 Contas recorrentes"
              count={dashboard.data.financeiro.recurring_expense_alerts.length}
            >
              {dashboard.data.financeiro.recurring_expense_alerts.length === 0 ? (
                <p className="py-2 text-sm text-muted">Nenhuma conta pendente.</p>
              ) : (
                dashboard.data.financeiro.recurring_expense_alerts.map((alert) => (
                  <div
                    key={alert.name}
                    className="flex items-center justify-between gap-3 border-b border-line py-2 text-sm last:border-b-0"
                  >
                    <span className="text-ink">
                      {alert.name} (dia {alert.due_day})
                    </span>
                    <div className="flex items-center gap-3">
                      {alert.amount != null && (
                        <span className="tabular-nums text-ink">R$ {formatBRL(alert.amount)}</span>
                      )}
                      <Button asChild variant="outline" size="sm" className="shrink-0">
                        <a href="/gastos/recorrentes" target="_blank" rel="noopener">
                          Abrir
                        </a>
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </SectorPanel>
          )}

          {!dashboard.data.casting &&
            !dashboard.data.figurino &&
            !dashboard.data.ensaio &&
            !dashboard.data.comercial &&
            !dashboard.data.financeiro && (
              <Card>
                <CardContent className="p-5">
                  <p className="text-sm text-muted">Tudo em dia! ✓</p>
                </CardContent>
              </Card>
            )}

          {user?.is_superadmin && dashboard.data.dismissed_casting.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Cargos dispensados</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted">
                  {dashboard.data.dismissed_casting.length} cargo(s) marcados como dispensados.
                </p>
              </CardContent>
            </Card>
          )}
        </motion.div>
      )}
    </div>
  );
}
