import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useRhDashboard } from "../lib/rh";

export function RhDashboardPage() {
  const query = useRhDashboard();

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <PageHeader title="RH" className="mb-0" />

      {query.isLoading && <Skeleton className="h-32 w-full" />}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o painel de RH.
        </div>
      )}

      {query.data && (
        <Card>
          <CardHeader>
            <CardTitle>Painel</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted">
              Módulo de RH em construção — mais funcionalidades chegam em fatias futuras.
            </p>
            {query.data.can_manage_users && (
              <Button asChild variant="outline" size="sm">
                <Link to="/admin/usuarios">Gerenciar usuários</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
