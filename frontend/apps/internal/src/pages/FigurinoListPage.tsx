import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useFigurinoSheets } from "../lib/figurino";
import { useCurrentUser } from "../lib/useAuth";

export function FigurinoListPage() {
  const query = useFigurinoSheets();
  const { data: user } = useCurrentUser();
  const canEdit = Boolean(user?.is_superadmin || user?.roles.includes("FIGURINO"));
  const [q, setQ] = useState("");

  const items = (query.data?.items ?? []).filter((s) =>
    s.character_name.toLowerCase().includes(q.toLowerCase()),
  );

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
<header className="flex items-center justify-between">
        <PageHeader title="Figurino" className="mb-0" />
        {canEdit && (
          <Button asChild size="sm">
            <Link to="/figurinos/new">+ Nova ficha</Link>
          </Button>
        )}
      </header>

      {query.data && query.data.chars_without_sheet.length > 0 && (
        <Card>
          <CardContent className="border-l-4 border-red p-4">
            <p className="mb-1 text-sm font-medium text-ink">Personagens sem ficha</p>
            <div className="flex flex-wrap gap-1.5">
              {query.data.chars_without_sheet.map((name) => (
                <span key={name} className="rounded-md bg-red-soft px-2 py-0.5 text-xs text-red">
                  {name}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <input
        className="h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
        placeholder="Buscar ficha por nome…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Buscar ficha de figurino"
      />

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as fichas.
        </div>
      )}

      {query.data && items.length === 0 && (
        <p className="text-sm text-muted">Nenhuma ficha encontrada.</p>
      )}

      {items.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          {items.map((sheet) => (
            <Card key={sheet.id}>
              <CardContent className="p-3">
                <div className="mb-2 flex h-32 items-center justify-center overflow-hidden rounded-md bg-surface-2">
                  {sheet.photo_url ? (
                    <img
                      src={assetUrl(sheet.photo_url)}
                      alt={sheet.character_name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="text-3xl">📷</span>
                  )}
                </div>
                <div className="font-medium text-ink">{sheet.character_name}</div>
                <div className="text-xs text-muted">{sheet.pieces.length} peça(s)</div>
                {canEdit && (
                  <div className="mt-2 flex gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/figurinos/${sheet.id}/edit`}>Editar</Link>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
