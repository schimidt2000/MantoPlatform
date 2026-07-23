import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useMigrarArquivosStatus, useStartMigrarArquivos } from "../lib/adminConfig";

export function AdminMigrarArquivosPage() {
  const query = useMigrarArquivosStatus();
  const start = useStartMigrarArquivos();

  return (
    <div className="mx-auto max-w-lg space-y-4 p-4 sm:p-6">
<PageHeader title="Migrar arquivos do Drive" className="mb-0" />

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
            <p className="text-sm text-ink">
              {query.data.pending_count} arquivo(s) pendente(s) de migração.
            </p>
            {query.data.status.running ? (
              <p className="text-sm text-accent-dark">
                Migração em andamento: {query.data.status.processed}/{query.data.status.total}
              </p>
            ) : (
              <Button
                loading={start.isPending}
                onClick={() => start.mutate()}
                disabled={query.data.pending_count === 0}
              >
                Iniciar migração
              </Button>
            )}
            {start.data && !start.data.started && (
              <p className="text-sm text-muted">A migração já está em andamento.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
