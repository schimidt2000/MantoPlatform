import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useAdminSyncStatus, useRunSync } from "../lib/adminConfig";

export function AdminSyncPage() {
  const query = useAdminSyncStatus();
  const runSync = useRunSync();

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
<PageHeader title="Sync da agenda" className="mb-0" />

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          loading={runSync.isPending}
          onClick={() => runSync.mutate("sync_now")}
        >
          Sincronizar agora
        </Button>
        <Button
          variant="outline"
          size="sm"
          loading={runSync.isPending}
          onClick={() => {
            if (window.confirm("Limpar eventos fantasma de todos os meses no banco?")) {
              runSync.mutate("cleanup_past");
            }
          }}
        >
          Limpar eventos fantasma
        </Button>
      </div>

      {runSync.data && (
        <div className="rounded-md bg-accent-soft px-4 py-3 text-sm text-accent-dark">
          {runSync.data.message}
        </div>
      )}
      {runSync.isError && (
        <p className="text-sm text-red">Não foi possível concluir a ação.</p>
      )}

      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o status de sync.
        </div>
      )}

      {query.data && (
        <Card>
          <CardHeader>
            <CardTitle>Meses com eventos no banco</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-line text-sm">
              {query.data.months.map((m) => (
                <li key={m.ym} className="flex items-center justify-between py-1.5">
                  <span className="text-ink">
                    {m.ym} ({m.count} evento(s))
                  </span>
                  <span className={m.fresh ? "text-green" : "text-muted"}>
                    {m.age_min != null ? `${m.age_min} min atrás` : "nunca sincronizado"}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
