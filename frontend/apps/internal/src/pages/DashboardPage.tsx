import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import { Card, CardContent, CardHeader, CardTitle, MetricBadge, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import type { DashboardSummary, DashboardTaskRef, PendingPayment } from "../lib/types";
import { DonutChart } from "../components/DonutChart";
import { SectorPanel, urgencyBadge } from "../components/SectorPanel";

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
  const badge = urgencyBadge(task.start_at);
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <div>
        <div className="flex items-center gap-2 font-medium text-ink">
          {task.character_name}
          {badge && <MetricBadge tone={badge.tone} size="xs">{badge.label}</MetricBadge>}
        </div>
        <Link to={`/events/${task.event_id}`} className="text-muted hover:underline">
          {task.event_title}
          {task.start_at && ` — ${new Date(task.start_at).toLocaleDateString("pt-BR")}`}
        </Link>
      </div>
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

function PendingPaymentRow({ item }: { item: PendingPayment }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <div>
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
    </div>
  );
}

type PerfRange = "7" | "30" | "custom";

function PerformancePanel({ dashboard }: { dashboard: DashboardSummary }) {
  const [range, setRange] = useState<PerfRange>("7");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const perf = useQuery<DashboardSummary>({
    queryKey: ["dashboard", "performance", range, start, end],
    queryFn: () => {
      const params = new URLSearchParams({ perf_range: range });
      if (range === "custom" && start && end) {
        params.set("perf_start", start);
        params.set("perf_end", end);
      }
      return apiFetch<DashboardSummary>(`/api/dashboard?${params.toString()}`);
    },
    initialData: range === "7" ? dashboard : undefined,
  });

  const performance = perf.data?.performance ?? dashboard.performance;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={range}
            onChange={(e) => setRange(e.target.value as PerfRange)}
          >
            <option value="7">Últimos 7 dias</option>
            <option value="30">Últimos 30 dias</option>
            <option value="custom">Período personalizado</option>
          </select>
          {range === "custom" && (
            <>
              <input
                type="date"
                className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                aria-label="Data inicial"
              />
              <input
                type="date"
                className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                aria-label="Data final"
              />
            </>
          )}
        </div>

        {!performance ? (
          <p className="text-sm text-muted">Selecione um período válido.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-medium text-muted">Casting</div>
              <div className="text-lg font-bold text-ink tabular-nums">
                {performance.casting_done}
                <span className="text-sm font-medium text-muted">/{performance.casting_total}</span>
              </div>
              <div className="text-xs text-muted">roles preenchidos</div>
            </div>
            <div>
              <div className="text-xs font-medium text-muted">Figurino</div>
              <div className="text-lg font-bold text-ink tabular-nums">
                {performance.figurino_done}
                <span className="text-sm font-medium text-muted">/{performance.figurino_total}</span>
              </div>
              <div className="text-xs text-muted">separados</div>
            </div>
            <div className="col-span-2">
              <div className="text-xs font-medium text-muted">Entrada total</div>
              <div className="text-xl font-bold text-gold tabular-nums">
                R$ {formatBRL(performance.money_total)}
              </div>
              <div className="text-xs text-muted">soma dos cachês no período</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
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
    <div className="mx-auto max-w-4xl p-6">
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
          className="space-y-6"
        >
          {(dashboard.data.casting || dashboard.data.figurino) && (
            <div className="flex flex-wrap justify-center gap-8 rounded-lg border border-line bg-panel py-6 shadow-sm">
              {dashboard.data.casting && (
                <DonutChart
                  label="Casting"
                  done={dashboard.data.casting.done}
                  total={dashboard.data.casting.total}
                />
              )}
              {dashboard.data.figurino && (
                <DonutChart
                  label="Figurino"
                  done={dashboard.data.figurino.done}
                  total={dashboard.data.figurino.total}
                />
              )}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-3">
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
                <SectorPanel
                  title="💼 Comercial"
                  count={dashboard.data.comercial.pending_payments.length}
                >
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
                        className="flex justify-between border-b border-line py-2 text-sm last:border-b-0"
                      >
                        <span className="text-ink">
                          {alert.name} (dia {alert.due_day})
                        </span>
                        {alert.amount != null && (
                          <span className="tabular-nums text-ink">R$ {formatBRL(alert.amount)}</span>
                        )}
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
            </div>

            <div className="space-y-3">
              {user?.is_real_superadmin && <PerformancePanel dashboard={dashboard.data} />}

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
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
