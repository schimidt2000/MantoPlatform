import { Link } from "react-router-dom";
import { Card, CardContent, Button, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { formatDateTime, formatRelativeDay, formatWeekday } from "../lib/format";
import { useAckEventChange, useAgenda, type PortalRole } from "../lib/portalAgenda";

function RoleCard({ role, upcoming = false }: { role: PortalRole; upcoming?: boolean }) {
  const ackChange = useAckEventChange();

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <Link
              to={`/eventos/${role.event_id}/figurino`}
              className="font-medium text-ink hover:underline"
            >
              {role.title}
            </Link>
            <p className="text-xs text-muted">
              {formatWeekday(role.start_at)}, {formatDateTime(role.start_at)}
              {role.location ? ` · ${role.location}` : ""}
            </p>
            {/* "amanhã" / "em 5 dias" só ajuda no que ainda vai acontecer — no histórico vira ruído. */}
            {upcoming && (
              <p className="text-xs font-medium text-accent">{formatRelativeDay(role.start_at)}</p>
            )}
            <p className="text-xs text-muted">Personagem: {role.character_name}</p>
          </div>
        </div>

        {role.has_unacknowledged_change && (
          <div className="rounded-md bg-red-soft px-3 py-2 text-xs text-red">
            <p className="mb-1 font-medium">
              Este evento teve uma alteração: {role.change_description || "confira os detalhes."}
            </p>
            <Button
              variant="outline"
              loading={ackChange.isPending}
              onClick={() => ackChange.mutate(role.role_id)}
            >
              Ciente
            </Button>
          </div>
        )}

        {typeof role.cache_total === "number" && (
          <p className="text-xs text-ink">
            Cachê: <strong>R$ {formatBRL(role.cache_total)}</strong>{" "}
            <span className={role.payment_status === "pago" ? "text-green" : "text-muted"}>
              ({role.payment_status === "pago" ? "pago" : "pendente"})
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function PortalAgendaPage() {
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
          Não foi possível carregar sua agenda.
        </div>
      </div>
    );
  }

  const agenda = agendaQuery.data;
  if (!agenda) return null;

  return (
    <div className="space-y-6 p-4">
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase text-muted">Próximos eventos</h2>
        {agenda.upcoming.length === 0 ? (
          <p className="text-sm text-muted">Nenhum evento confirmado por enquanto.</p>
        ) : (
          <div className="space-y-3">
            {agenda.upcoming.map((role) => (
              <RoleCard key={role.role_id} role={role} upcoming />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase text-muted">Histórico</h2>
        {agenda.history.length === 0 ? (
          <p className="text-sm text-muted">Nenhum evento passado ainda.</p>
        ) : (
          <div className="space-y-3">
            {agenda.history.map((role) => (
              <RoleCard key={role.role_id} role={role} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
