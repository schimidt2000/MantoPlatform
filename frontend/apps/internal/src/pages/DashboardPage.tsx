import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser, useLogout } from "../lib/useAuth";
import type { DashboardSummary } from "../lib/types";

function DashboardSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-32 w-full" />
      ))}
    </div>
  );
}

function CountCard({ title, done, total }: { title: string; done: number; total: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold text-ink">
          {done}
          <span className="text-lg text-muted"> / {total}</span>
        </p>
        <p className="mt-1 text-sm text-muted">concluídos</p>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const reduceMotion = useReducedMotion();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  const dashboard = useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<DashboardSummary>("/api/dashboard"),
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Início</h1>
          {user && <p className="text-sm text-muted">Olá, {user.name}</p>}
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/agenda">Agenda</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/talents">Talentos</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/figurinos">Figurino</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/vendas">Vendas</Link>
          </Button>
          {(user?.is_superadmin || user?.roles.includes("FINANCEIRO")) && (
            <Button asChild variant="outline" size="sm">
              <Link to="/financeiro">Financeiro</Link>
            </Button>
          )}
          <Button variant="outline" size="sm" loading={logout.isPending} onClick={() => logout.mutate()}>
            Sair
          </Button>
        </div>
      </header>

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
          className="grid gap-4 sm:grid-cols-2"
        >
          {dashboard.data.casting && (
            <CountCard
              title="Casting"
              done={dashboard.data.casting.done}
              total={dashboard.data.casting.total}
            />
          )}
          {dashboard.data.figurino && (
            <CountCard
              title="Figurino"
              done={dashboard.data.figurino.done}
              total={dashboard.data.figurino.total}
            />
          )}
          {dashboard.data.financeiro && (
            <Card>
              <CardHeader>
                <CardTitle>Contas do mês</CardTitle>
              </CardHeader>
              <CardContent>
                {dashboard.data.financeiro.recurring_expense_alerts.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma conta pendente.</p>
                ) : (
                  <ul className="space-y-1 text-sm text-ink">
                    {dashboard.data.financeiro.recurring_expense_alerts.map((alert) => (
                      <li key={alert.name} className="flex justify-between">
                        <span>
                          {alert.name} (dia {alert.due_day})
                        </span>
                        {alert.amount != null && (
                          <span className="tabular-nums">R$ {formatBRL(alert.amount)}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
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
