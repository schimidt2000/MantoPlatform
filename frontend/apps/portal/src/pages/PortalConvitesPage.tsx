import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useAcceptInvite, useAgenda, useRejectInvite } from "../lib/portalAgenda";

function formatDateTime(iso: string | null): string {
  if (!iso) return "Data a confirmar";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function PortalConvitesPage() {
  const agendaQuery = useAgenda();
  const acceptInvite = useAcceptInvite();
  const rejectInvite = useRejectInvite();

  if (agendaQuery.isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (agendaQuery.isError) {
    return (
      <div className="p-4">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar seus convites.
        </div>
      </div>
    );
  }

  const invites = agendaQuery.data?.pending_invites ?? [];

  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold uppercase text-muted">Convites pendentes</h2>

      {invites.length === 0 && (
        <p className="text-sm text-muted">Nenhum convite pendente por enquanto.</p>
      )}

      {invites.map((role) => (
        <Card key={role.role_id}>
          <CardContent className="space-y-3 p-4">
            <div>
              <p className="font-medium text-ink">{role.title}</p>
              <p className="text-xs text-muted">
                {formatDateTime(role.start_at)}
                {role.location ? ` · ${role.location}` : ""}
              </p>
              <p className="text-xs text-muted">Personagem: {role.character_name}</p>
            </div>
            <div className="flex gap-2">
              <Button
                className="flex-1"
                loading={acceptInvite.isPending}
                onClick={() => acceptInvite.mutate(role.role_id)}
              >
                Aceitar
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                loading={rejectInvite.isPending}
                onClick={() => {
                  if (window.confirm(`Recusar o convite para "${role.title}"?`)) {
                    rejectInvite.mutate(role.role_id);
                  }
                }}
              >
                Recusar
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
