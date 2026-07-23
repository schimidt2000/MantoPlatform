import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { useEducaMantoHistorico, useOrcamentoPdf } from "../lib/educamanto";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function EducaMantoHistoricoPage() {
  const [q, setQ] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userId, setUserId] = useState("");

  const historicoQuery = useEducaMantoHistorico({
    q: q || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    user_id: userId || undefined,
  });
  const openPdf = useOrcamentoPdf();

  const entries = historicoQuery.data?.entries ?? [];
  const users = historicoQuery.data?.users;
  const isSuperadmin = users !== undefined;

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Histórico de orçamentos"
        className="mb-0"
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/educamanto">‹ Calculadora</Link>
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2">
        <input
          className="h-9 min-w-[200px] flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Buscar por cliente ou pacote…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <input
          type="date"
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          aria-label="De"
        />
        <input
          type="date"
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          aria-label="Até"
        />
        {isSuperadmin && users && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          >
            <option value="">Todos os usuários</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {historicoQuery.isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {historicoQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o histórico.
        </div>
      )}

      {historicoQuery.data && entries.length === 0 && (
        <p className="text-sm text-muted">Nenhum orçamento encontrado.</p>
      )}

      {entries.length > 0 && (
        <div className="space-y-2">
          {entries.map((entry) => (
            <Card key={entry.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-3">
                <div>
                  <p className="font-medium text-ink">
                    {entry.client_name || "Cliente não informado"}
                  </p>
                  <p className="text-xs text-muted">
                    {entry.packages_label} · {formatDateTime(entry.created_at)}
                    {entry.user_name && ` · Gerado por ${entry.user_name}`}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  loading={openPdf.isPending}
                  onClick={() => openPdf.mutate(entry.id)}
                >
                  Reabrir PDF
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
