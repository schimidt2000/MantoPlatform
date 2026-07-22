import { Link } from "react-router-dom";
import { formatBRL } from "@manto/money";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useAdminUsers } from "../lib/adminUsers";
import { useCurrentUser } from "../lib/useAuth";

export function AdminUsersListPage() {
  const query = useAdminUsers();
  const { data: me } = useCurrentUser();

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">‹ Início</Link>
        </Button>
        {me?.is_superadmin && (
          <Button asChild size="sm">
            <Link to="/admin/usuarios/novo">+ Novo usuário</Link>
          </Button>
        )}
      </div>

      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-ink">Usuários</h1>
      </header>

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os usuários.
        </div>
      )}

      {query.data && (
        <div className="space-y-2">
          {query.data.items.map((u) => (
            <Card key={u.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div className="min-w-0">
                  <Link
                    to={`/admin/usuarios/${u.id}`}
                    className="font-medium text-ink hover:underline"
                  >
                    {u.name}
                  </Link>
                  <div className="text-sm text-muted">
                    {u.email || "sem email"} · {u.has_access ? "com acesso" : "só pagamento"}
                    {!u.is_active && " · inativo"}
                  </div>
                  {u.role_names.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {u.role_names.map((r) => (
                        <span
                          key={r}
                          className="rounded-md bg-accent-soft px-1.5 py-0.5 text-xs text-accent-dark"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {u.salary && (
                  <span className="shrink-0 text-sm tabular-nums text-ink">
                    R$ {formatBRL(u.salary.amount)}
                  </span>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
