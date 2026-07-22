import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useAdminLogs } from "../lib/adminConfig";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

export function AdminLogsPage() {
  const [entityType, setEntityType] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(1);
  const query = useAdminLogs(entityType, actor, page);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/">‹ Início</Link>
      </Button>

      <header>
        <h1 className="text-2xl font-semibold text-ink">Logs de auditoria</h1>
      </header>

      <div className="flex flex-wrap gap-2">
        {query.data && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos os tipos</option>
            {query.data.entity_types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
        <input
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Filtrar por quem executou…"
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os logs.
        </div>
      )}

      {query.data && (
        <>
          <div className="space-y-2">
            {query.data.items.map((log) => (
              <Card key={log.id}>
                <CardContent className="p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink">
                      {log.actor_name} · {log.action}
                    </span>
                    <span className="text-xs text-muted">{formatDate(log.created_at)}</span>
                  </div>
                  {log.entity_name && (
                    <p className="text-muted">
                      {log.entity_type}: {log.entity_name}
                    </p>
                  )}
                  {log.detail && <p className="text-muted">{log.detail}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
          {query.data.pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ‹ Anterior
              </Button>
              <span className="text-sm text-muted">
                Página {query.data.page} de {query.data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= query.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima ›
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
