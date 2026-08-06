import { useState } from "react";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { CacheLine } from "../components/CacheLine";
import { FormError } from "../components/FormField";
import { formatDateTime, formatRelativeDay, formatWeekday } from "../lib/format";
import { useAcceptInvite, useAgenda, useRejectInvite, type PortalRole } from "../lib/portalAgenda";

/**
 * Um convite pendente, com o cachê em destaque.
 *
 * Cada card é dono do próprio estado de envio: as mutations são compartilhadas entre todos os
 * convites, então usar `isPending` direto colocaria *todos* os botões da lista em carregamento ao
 * responder um único convite. Comparar com o `role_id` em voga restringe o feedback ao card certo.
 */
function InviteCard({ role }: { role: PortalRole }) {
  const acceptInvite = useAcceptInvite();
  const rejectInvite = useRejectInvite();
  const [confirmando, setConfirmando] = useState(false);

  const respondendo = acceptInvite.isPending || rejectInvite.isPending;
  const erro = acceptInvite.error ?? rejectInvite.error;

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="space-y-0.5">
          <p className="font-medium text-ink">{role.title}</p>
          <p className="text-sm text-muted">
            {formatWeekday(role.start_at)}, {formatDateTime(role.start_at)}
          </p>
          {role.location && <p className="text-sm text-muted">{role.location}</p>}
          <p className="text-sm font-medium text-accent">{formatRelativeDay(role.start_at)}</p>
          <p className="text-sm text-muted">Personagem: {role.character_name}</p>
        </div>

        <CacheLine role={role} variant="destaque" />

        {erro && <FormError>{erro.message}</FormError>}

        {confirmando ? (
          <div className="space-y-2 rounded-lg border border-line bg-surface-2 p-3">
            <p className="text-sm text-ink">Recusar o convite para este evento?</p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="min-h-11 flex-1"
                loading={rejectInvite.isPending}
                onClick={() => rejectInvite.mutate(role.role_id)}
              >
                Sim, recusar
              </Button>
              <Button
                variant="ghost"
                className="min-h-11 flex-1"
                disabled={respondendo}
                onClick={() => setConfirmando(false)}
              >
                Voltar
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <Button
              className="min-h-11 flex-1"
              loading={acceptInvite.isPending}
              disabled={respondendo}
              onClick={() => acceptInvite.mutate(role.role_id)}
            >
              Aceitar
            </Button>
            <Button
              variant="outline"
              className="min-h-11 flex-1"
              disabled={respondendo}
              onClick={() => setConfirmando(true)}
            >
              Recusar
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PortalConvitesPage() {
  const agendaQuery = useAgenda();

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
        <InviteCard key={role.role_id} role={role} />
      ))}
    </div>
  );
}
