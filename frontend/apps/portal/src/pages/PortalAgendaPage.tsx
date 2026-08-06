import { useState } from "react";
import { Link } from "react-router-dom";
import { Shirt } from "lucide-react";
import { Card, CardContent, Button, Skeleton } from "@manto/ui";
import { CacheLine } from "../components/CacheLine";
import { formatDateTime, formatRelativeDay, formatWeekday } from "../lib/format";
import { useAckEventChange, useAgenda, type PortalRole } from "../lib/portalAgenda";

function RoleCard({ role, upcoming = false }: { role: PortalRole; upcoming?: boolean }) {
  const ackChange = useAckEventChange();
  // Sem isto o "Ciente" falhava em silêncio: o spinner sumia, nada mudava na tela e o
  // artista concluía que tinha confirmado a leitura da alteração (Princípio V).
  const [ackError, setAckError] = useState<string | null>(null);

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            {/* Título deixou de ser link: quem navega é a linha "Ver ficha de figurino" no
                rodapé do card, com alvo de 44px. Dois links para o mesmo destino no mesmo
                card só confundem — e o título nunca teve afordância de toque. */}
            <p className="font-medium text-ink">{role.title}</p>
            {/* text-sm (14px) e não text-xs: quando/onde é a informação que o artista abre o
                portal para ler, quase sempre no celular e na rua. 12px fica para rótulo
                decorativo, não para dado operacional. */}
            <p className="text-sm text-muted">
              {formatWeekday(role.start_at)}, {formatDateTime(role.start_at)}
              {role.location ? ` · ${role.location}` : ""}
            </p>
            {/* "amanhã" / "em 5 dias" só ajuda no que ainda vai acontecer — no histórico vira ruído. */}
            {upcoming && (
              <p className="text-sm font-medium text-accent">{formatRelativeDay(role.start_at)}</p>
            )}
            <p className="text-sm text-muted">Personagem: {role.character_name}</p>
          </div>
        </div>

        {role.has_unacknowledged_change && (
          <div className="rounded-md bg-red-soft px-3 py-2 text-sm text-red">
            <p className="mb-1 font-medium">
              Este evento teve uma alteração: {role.change_description || "confira os detalhes."}
            </p>
            <Button
              variant="outline"
              loading={ackChange.isPending}
              onClick={() => {
                setAckError(null);
                ackChange.mutate(role.role_id, {
                  onError: (error) => setAckError(error.message),
                });
              }}
            >
              Ciente
            </Button>
            {ackError && (
              <p className="mt-2 font-medium" role="alert">
                Não foi possível confirmar: {ackError}
              </p>
            )}
          </div>
        )}

        {/* Situação de pagamento só no histórico: em evento futuro, "a receber" é óbvio e vira ruído. */}
        <CacheLine role={role} payment={!upcoming} />

        {/* No celular não existe hover, então o título estilizado como link não anunciava
            nada — esta linha é o caminho explícito (e com 44px de alvo) para o figurino. */}
        <Link
          to={`/eventos/${role.event_id}/figurino`}
          className="flex min-h-[44px] items-center gap-2 text-sm font-medium text-accent"
        >
          <Shirt className="h-4 w-4 shrink-0" aria-hidden="true" />
          Ver ficha de figurino ›
        </Link>
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
