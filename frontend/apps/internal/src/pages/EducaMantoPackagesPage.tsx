import { Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import {
  useDeletePackage,
  useDuplicatePackage,
  useEducaMantoPackages,
} from "../lib/educamanto";

const CAN_VIEW_PACKAGES = ["COMERCIAL", "SUPERADMIN"];

export function EducaMantoPackagesPage() {
  const user = useCurrentUser();
  const canManage = Boolean(user.data?.is_superadmin);
  const canViewPackages = Boolean(
    user.data && (user.data.is_superadmin || user.data.roles.some((r) => CAN_VIEW_PACKAGES.includes(r))),
  );

  const packagesQuery = useEducaMantoPackages();
  const duplicatePackage = useDuplicatePackage();
  const deletePackage = useDeletePackage();

  const packages = packagesQuery.data?.packages ?? [];

  if (user.data && !canViewPackages) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <PageHeader title="EducaManto — Pacotes" className="mb-0" />
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Você não tem permissão para acessar a gestão de pacotes do EducaManto.
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Pacotes"
        className="mb-0"
        actions={
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link to="/educamanto">‹ Calculadora</Link>
            </Button>
            {canManage && (
              <Button asChild size="sm">
                <Link to="/educamanto/pacotes/novo">+ Novo pacote</Link>
              </Button>
            )}
          </div>
        }
      />

      {packagesQuery.isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {packagesQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os pacotes. Confira se você tem permissão para acessar o
          EducaManto.
        </div>
      )}

      {packagesQuery.data && packages.length === 0 && (
        <p className="text-sm text-muted">Nenhum pacote cadastrado ainda.</p>
      )}

      {packages.length > 0 && (
        <div className="space-y-3">
          {packages.map((pkg) => (
            <Card key={pkg.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium text-ink">{pkg.name}</p>
                  <p className="text-xs text-muted">
                    {pkg.items.length} {pkg.items.length === 1 ? "item" : "itens"} · comissão{" "}
                    {formatBRL(pkg.commission_rate * 100)}%
                  </p>
                </div>
                {canManage && (
                  <div className="flex gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/educamanto/pacotes/${pkg.id}/editar`}>Editar</Link>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      loading={duplicatePackage.isPending}
                      onClick={() => duplicatePackage.mutate(pkg.id)}
                    >
                      Duplicar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={deletePackage.isPending}
                      onClick={() => {
                        if (window.confirm(`Excluir o pacote "${pkg.name}" definitivamente?`)) {
                          deletePackage.mutate(pkg.id);
                        }
                      }}
                    >
                      Excluir
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
