import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import {
  useDeletePackage,
  useDuplicatePackage,
  useEducaMantoPackages,
  type EducaMantoPackage,
} from "../lib/educamanto";

const CAN_VIEW_PACKAGES = ["COMERCIAL", "SUPERADMIN"];

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function PackageCard({
  pkg,
  canManage,
  onDuplicate,
  duplicating,
  onDelete,
  deleting,
}: {
  pkg: EducaMantoPackage;
  canManage: boolean;
  onDuplicate: () => void;
  duplicating: boolean;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-base">{pkg.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-ink">
          <p>
            <span className="text-muted">1 sessão:</span> {pkg.margin_1s.toFixed(2)}×
          </p>
          <p>
            <span className="text-muted">2 sessões:</span> {pkg.margin_2s.toFixed(2)}×
          </p>
          <p>
            <span className="text-muted">1S/dia (multi):</span> {pkg.margin_1s_days.toFixed(2)}×
          </p>
          <p>
            <span className="text-muted">2S/dia (multi):</span> {pkg.margin_2s_days.toFixed(2)}×
          </p>
        </div>

        <p className="text-xs text-gold">
          {(pkg.discount_pct * 100).toFixed(0)}% de desconto após {pkg.discount_days}{" "}
          {pkg.discount_days === 1 ? "dia" : "dias"}
        </p>

        <div className="rounded-md bg-surface-2 p-2 text-xs text-ink">
          <p className="mb-1 font-semibold uppercase text-muted">Matriz de custos</p>
          <p>
            {pkg.items.length} {pkg.items.length === 1 ? "item" : "itens"} · comissão{" "}
            {(pkg.commission_rate * 100).toFixed(0)}%
          </p>
          <p className="text-muted">
            Ensemble: {brl(pkg.ensemble_1s)} (1S) · {brl(pkg.ensemble_2s)} (2S)
          </p>
        </div>

        <div className="mt-auto flex flex-wrap justify-center gap-2 pt-2">
          <Button asChild size="sm">
            <Link to={`/educamanto?package_id=${pkg.id}`}>Usar</Link>
          </Button>
          {canManage && (
            <>
              <Button asChild variant="outline" size="sm">
                <Link to={`/educamanto/pacotes/${pkg.id}/editar`}>Editar</Link>
              </Button>
              <Button variant="outline" size="sm" loading={duplicating} onClick={onDuplicate}>
                Criar cópia
              </Button>
              <Button variant="ghost" size="sm" loading={deleting} onClick={onDelete}>
                Excluir
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

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
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-52 w-full" />
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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {packages.map((pkg) => (
            <PackageCard
              key={pkg.id}
              pkg={pkg}
              canManage={canManage}
              duplicating={duplicatePackage.isPending}
              onDuplicate={() => duplicatePackage.mutate(pkg.id)}
              deleting={deletePackage.isPending}
              onDelete={() => {
                if (window.confirm(`Excluir o pacote "${pkg.name}" definitivamente?`)) {
                  deletePackage.mutate(pkg.id);
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
