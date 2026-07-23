import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, MetricBadge, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import type { DashboardSummary, DashboardTaskRef, PendingPayment } from "../lib/types";
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
