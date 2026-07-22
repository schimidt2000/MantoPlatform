import { useState } from "react";
import { Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useAdminCatalogo, useDeleteCatalogItem, useToggleCatalogItemActive } from "../lib/adminCatalogo";

export function AdminCatalogoListPage() {
  const [q, setQ] = useState("");
  const [categoria, setCategoria] = useState("");
  const [status, setStatus] = useState("todos");
  const query = useAdminCatalogo({ q, categoria, status });
  const toggleActive = useToggleCatalogItemActive();
  const deleteItem = useDeleteCatalogItem();

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">‹ Início</Link>
        </Button>
        <Button asChild size="sm">
          <Link to="/admin/catalogo/novo">+ Novo produto</Link>
        </Button>
      </div>

      <header>
        <h1 className="text-2xl font-semibold text-ink">Catálogo</h1>
      </header>

      <div className="flex flex-wrap gap-2">
        <input
          className="h-9 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Buscar por nome…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {query.data && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
          >
            <option value="">Todas as categorias</option>
            {query.data.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        <select
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="todos">Todos os status</option>
          <option value="ativo">Ativos</option>
          <option value="inativo">Inativos</option>
        </select>
      </div>

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o catálogo.
        </div>
      )}

      {query.data && query.data.items.length === 0 && (
        <p className="text-sm text-muted">Nenhum produto encontrado.</p>
      )}

      {query.data && query.data.items.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {query.data.items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex gap-3 p-3">
                <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-surface-2">
                  {item.cover_url && (
                    <img
                      src={assetUrl(item.cover_url)}
                      alt={item.name}
                      className="h-full w-full object-cover"
                    />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <Link
                    to={`/admin/catalogo/${item.id}/editar`}
                    className="font-medium text-ink hover:underline"
                  >
                    {item.name}
                  </Link>
                  {!item.is_active && (
                    <span className="ml-2 rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                      inativo
                    </span>
                  )}
                  <div className="mt-1 text-xs text-muted">
                    {item.category_names.join(", ")}
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={toggleActive.isPending}
                      onClick={() => toggleActive.mutate(item.id)}
                    >
                      {item.is_active ? "Inativar" : "Ativar"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={deleteItem.isPending}
                      onClick={() => {
                        if (window.confirm(`Excluir "${item.name}" definitivamente?`)) {
                          deleteItem.mutate(item.id);
                        }
                      }}
                    >
                      Excluir
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
