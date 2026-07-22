import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { useImportarCatalogoStatus, useStartImportarCatalogo } from "../lib/adminConfig";

export function AdminImportarCatalogoPage() {
  const query = useImportarCatalogoStatus();
  const start = useStartImportarCatalogo();

  return (
    <div className="mx-auto max-w-lg space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/">‹ Início</Link>
      </Button>

      <header>
        <h1 className="text-2xl font-semibold text-ink">Importar catálogo</h1>
      </header>

      {query.isLoading && <Skeleton className="h-40 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o status.
        </div>
      )}

      {query.data && (
        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-ink">{query.data.total_items} item(ns) já importado(s).</p>
            {query.data.status.running ? (
              <p className="text-sm text-accent-dark">
                Importação em andamento: {query.data.status.processed}/{query.data.status.total}
              </p>
            ) : (
              <Button
                loading={start.isPending}
                onClick={() => {
                  if (window.confirm("Reimportar o catálogo a partir do CSV?")) {
                    start.mutate();
                  }
                }}
              >
                Iniciar importação
              </Button>
            )}
            {start.data && !start.data.started && (
              <p className="text-sm text-muted">A importação já está em andamento.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
