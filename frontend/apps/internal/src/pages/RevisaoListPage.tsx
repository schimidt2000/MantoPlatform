import { Link } from "react-router-dom";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useRevisaoSpaces } from "../lib/revisao";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function RevisaoListPage() {
  const query = useRevisaoSpaces();

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">‹ Início</Link>
        </Button>
        {query.data?.can_create && (
          <Button asChild size="sm">
            <Link to="/revisao/novo">+ Novo espaço</Link>
          </Button>
        )}
      </div>

      <header>
        <h1 className="text-2xl font-semibold text-ink">Revisão de mídia</h1>
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
          Não foi possível carregar os espaços.
        </div>
      )}

      {query.data && query.data.items.length === 0 && (
        <p className="text-sm text-muted">Nenhum espaço de revisão encontrado.</p>
      )}

      {query.data && query.data.items.length > 0 && (
        <div className="space-y-2">
          {query.data.items.map((space) => (
            <Card key={space.id}>
              <CardContent className="p-3">
                <Link
                  to={`/revisao/${space.id}`}
                  className="font-medium text-ink hover:underline"
                >
                  {space.title}
                </Link>
                <div className="text-sm text-muted">
                  {space.creator_name} · {formatDate(space.created_at)} · {space.asset_count}{" "}
                  material(is)
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
