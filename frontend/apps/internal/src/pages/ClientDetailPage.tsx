import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useClientDetail, useDeleteClient, useUpdateClient } from "../lib/clientes";
import { useCurrentUser } from "../lib/useAuth";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const query = useClientDetail(id);
  const update = useUpdateClient(id);
  const del = useDeleteClient();
  const { data: user } = useCurrentUser();

  const [cpf, setCpf] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [address, setAddress] = useState("");

  useEffect(() => {
    if (query.data) {
      setCpf(query.data.cpf);
      setCnpj(query.data.cnpj);
      setAddress(query.data.address);
    }
  }, [query.data]);

  const canDelete = Boolean(user?.is_superadmin || user?.roles.includes("FINANCEIRO"));

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o cliente.
        </div>
      )}

      {query.data && (
        <>
          <header className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-ink">{query.data.name}</h1>
              <p className="text-sm text-muted">
                {[query.data.phone_display, query.data.company].filter(Boolean).join(" · ")}
              </p>
            </div>
            {canDelete && (
              <Button
                variant="outline"
                size="sm"
                loading={del.isPending}
                onClick={() => {
                  if (
                    window.confirm(
                      `Excluir o cliente "${query.data.name}"? Os eventos associados serão desvinculados, não excluídos.`,
                    )
                  ) {
                    del.mutate(id, { onSuccess: () => navigate("/clientes") });
                  }
                }}
              >
                Excluir
              </Button>
            )}
          </header>

          <Card>
            <CardHeader>
              <CardTitle>Contato</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted">Telefone</dt>
                <dd className="text-ink">{query.data.phone_display}</dd>
                {query.data.email && (
                  <>
                    <dt className="text-muted">E-mail</dt>
                    <dd className="text-ink">{query.data.email}</dd>
                  </>
                )}
                {query.data.company && (
                  <>
                    <dt className="text-muted">Empresa</dt>
                    <dd className="text-ink">{query.data.company}</dd>
                  </>
                )}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>CPF/CNPJ e endereço</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  placeholder="CPF"
                  value={cpf}
                  onChange={(e) => setCpf(e.target.value)}
                  aria-label="CPF"
                />
                <input
                  className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  placeholder="CNPJ"
                  value={cnpj}
                  onChange={(e) => setCnpj(e.target.value)}
                  aria-label="CNPJ"
                />
              </div>
              <textarea
                className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
                placeholder="Endereço"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                aria-label="Endereço"
              />
              <div>
                <Button
                  size="sm"
                  loading={update.isPending}
                  onClick={() => update.mutate({ cpf, cnpj, address })}
                >
                  Salvar
                </Button>
              </div>
              {update.isError && (
                <p className="text-sm text-red">Não foi possível salvar os dados.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Eventos</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-2 text-sm text-muted">
                {query.data.event_count} evento(s) · total vendido:{" "}
                <span className="tabular-nums text-ink">
                  R$ {formatBRL(query.data.total_sales)}
                </span>
              </p>
              {query.data.events.length === 0 ? (
                <p className="text-sm text-muted">Nenhum evento associado.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {query.data.events.map((e) => (
                    <li
                      key={e.id}
                      className="flex items-center justify-between gap-3 py-1.5 text-sm"
                    >
                      <div>
                        <span className="text-muted">{formatDate(e.start_at)}</span>{" "}
                        <Link to={`/events/${e.id}`} className="text-ink hover:underline">
                          {e.title}
                        </Link>
                      </div>
                      <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                        {e.relation}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
