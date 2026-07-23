import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { useClients } from "../lib/clientes";

export function ClientsListPage() {
  const [q, setQ] = useState("");
  const query = useClients(q);

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <PageHeader
        title="Clientes"
        className="mb-4"
        subtitle={
          query.data ? `${query.data.total_clients} cliente(s) cadastrado(s)` : undefined
        }
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/clientes/avaliacoes">Avaliações ›</Link>
          </Button>
        }
      />

      <input
        className="mb-4 h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
        placeholder="Buscar por nome ou telefone…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Buscar cliente"
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os clientes.
        </div>
      )}

      {query.data && query.data.items.length === 0 && (
        <p className="text-sm text-muted">Nenhum cliente encontrado.</p>
      )}

      {query.data && query.data.items.length > 0 && (
        <div className="space-y-2">
          {query.data.items.map((c) => (
            <Card key={c.id}>
              <CardContent className="flex items-center justify-between gap-3 p-3">
                <div className="min-w-0">
                  <Link to={`/clientes/${c.id}`} className="font-medium text-ink hover:underline">
                    {c.name}
                  </Link>
                  <div className="text-sm text-muted">
                    {[c.phone_display, c.company].filter(Boolean).join(" · ")}
                  </div>
                </div>
                <span className="shrink-0 rounded-md bg-surface-2 px-2 py-1 text-xs text-muted">
                  {c.event_count} evento(s)
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
