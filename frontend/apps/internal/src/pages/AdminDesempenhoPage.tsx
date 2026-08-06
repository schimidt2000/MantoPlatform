import { useState } from "react";
import { formatBRL } from "@manto/money";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useAdminDesempenho } from "../lib/adminConfig";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function AdminDesempenhoPage() {
  const [month, setMonth] = useState(currentMonth());
  const query = useAdminDesempenho(month);

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Desempenho"
        className="mb-0"
        actions={
          <input
            type="month"
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          />
        }
      />

      {query.isLoading && (
        <div className="grid gap-4 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o desempenho.
        </div>
      )}

      {query.data && (
        // Três rankings independentes do mesmo mês: lado a lado dá para comparar sem rolar.
        <div className="grid items-start gap-4 [&>*]:min-w-0 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Casting</CardTitle>
            </CardHeader>
            <CardContent>
              {query.data.casting.length === 0 ? (
                <p className="text-sm text-muted">Sem escalações no período.</p>
              ) : (
                <ul className="divide-y divide-line text-sm">
                  {query.data.casting.map((c) => (
                    <li key={c.name} className="flex justify-between py-1.5">
                      <span className="text-ink">{c.name}</span>
                      <span className="text-muted">{c.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Figurino</CardTitle>
            </CardHeader>
            <CardContent>
              {query.data.figurino.length === 0 ? (
                <p className="text-sm text-muted">Sem registros no período.</p>
              ) : (
                <ul className="divide-y divide-line text-sm">
                  {query.data.figurino.map((f) => (
                    <li key={f.name} className="flex justify-between py-1.5">
                      <span className="text-ink">{f.name}</span>
                      <span className="text-muted">{f.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Vendas</CardTitle>
            </CardHeader>
            <CardContent>
              {query.data.vendas.length === 0 ? (
                <p className="text-sm text-muted">Sem vendas no período.</p>
              ) : (
                <ul className="divide-y divide-line text-sm">
                  {query.data.vendas.map((v) => (
                    <li key={v.name} className="flex justify-between py-1.5">
                      <span className="text-ink">
                        {v.name} ({v.count})
                      </span>
                      <span className="tabular-nums text-ink">
                        R$ {formatBRL(v.total ?? 0)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
