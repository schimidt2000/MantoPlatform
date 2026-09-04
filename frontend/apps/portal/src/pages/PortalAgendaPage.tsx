import { useState } from "react";
import { Link } from "react-router-dom";
import { MailQuestion, Shirt } from "lucide-react";
import { Card, CardContent, Button, Skeleton } from "@manto/ui";
import { CacheLine } from "../components/CacheLine";
import { RatingLink } from "../components/RatingLink";
import { formatDateTime, formatRelativeDay, formatWeekday } from "../lib/format";
import { useAckEventChange, useAgenda, type PortalRole } from "../lib/portalAgenda";
import { ErroDeCarregamento } from "../components/ErroDeCarregamento";

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

        {/* Desde a 230 "Próximos eventos" lista também escalação sem aceite, então o mesmo evento
            pode estar aqui e na aba Convites. Sem esta linha, a repetição parece defeito. Só
            `pending` tem o que responder — `null` é convite que o casting nunca enviou, e nesse
            caso o artista não tem o que fazer além de saber que está escalado. */}
        {upcoming && role.invite_status === "pending" && (
          <Link
            to="/convites"
            className="flex min-h-[44px] items-center gap-2 text-sm font-medium text-gold-ink"
          >
            <MailQuestion className="h-4 w-4 shrink-0" aria-hidden="true" />
            Falta responder este convite ›
          </Link>
        )}

        {/* Situação de pagamento só no histórico: em evento futuro, "a receber" é óbvio e vira ruído. */}
        <CacheLine role={role} payment={!upcoming} />

        {/* No celular não existe hover, então o título estilizado como link não anunciava
            nada — esta linha é o caminho explícito (e com 44px de alvo) para o figurino.
            Só aparece quando existe ficha do outro lado: o link para uma tela vazia era lido
            como "o figurino não subiu". */}
        {role.has_figurino && (
          <Link
            to={`/eventos/${role.event_id}/figurino`}
            className="flex min-h-[44px] items-center gap-2 text-sm font-medium text-accent"
          >
            <Shirt className="h-4 w-4 shrink-0" aria-hidden="true" />
            Ver ficha de figurino ›
          </Link>
        )}

        {/* Avaliar só faz sentido no que já passou — e é aqui que faltava (feature 229). A aba
            Histórico tinha o botão, esta seção não; as duas se chamam "Histórico", então quem
            estava olhando a Agenda concluía que não havia como avaliar. */}
        {!upcoming && <RatingLink eventId={role.event_id} />}
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
      <ErroDeCarregamento
        erro={agendaQuery.error}
        oQue="sua agenda"
        aoTentarDeNovo={() => void agendaQuery.refetch()}
        carregando={agendaQuery.isFetching}
      />
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
