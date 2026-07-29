import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import {
  AvatarThumb,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
  formatShortDate,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  daysUntilDeadline,
  formatDeadline,
  GIFT_3D_STATUSES,
  GIFT_3D_STATUS_LABELS,
  GIFT_3D_STATUS_TONES,
  useFila3D,
  useUpdateEvent3DGift,
  type Fila3DEntry,
  type Gift3DStatus,
} from "../lib/impressoes3d";

const INPUT_CLASS = "h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Selo de urgência do prazo — é a informação que ordena o trabalho do dia. */
function DeadlineBadge({ deadline }: { deadline: string | null }) {
  const days = daysUntilDeadline(deadline);
  if (days === null) return <span className="text-muted">Sem prazo</span>;
  if (days < 0) return <Badge tone="red">Atrasado {Math.abs(days)}d</Badge>;
  if (days === 0) return <Badge tone="red">Hoje</Badge>;
  if (days <= 7) return <Badge tone="gold">Em {days}d</Badge>;
  return <Badge tone="neutral">Em {days}d</Badge>;
}

/** Seletor rápido de status (4 opções — abaixo do limite de 10 do Princípio X.1). */
function StatusSelect({ entry }: { entry: Fila3DEntry }) {
  const update = useUpdateEvent3DGift();
  return (
    <div className="flex items-center gap-2">
      <select
        className={INPUT_CLASS}
        value={entry.status}
        disabled={update.isPending}
        aria-label={`Status do presente ${entry.item?.name ?? ""}`}
        onChange={(e) =>
          update.mutate({
            eventId: entry.event_id,
            giftId: entry.id,
            input: { status: e.target.value as Gift3DStatus },
          })
        }
      >
        {GIFT_3D_STATUSES.map((status) => (
          <option key={status} value={status}>
            {GIFT_3D_STATUS_LABELS[status]}
          </option>
        ))}
      </select>
      {update.isPending && <span className="text-xs text-muted">Salvando…</span>}
      {update.isError && <span className="text-xs text-red">Erro ao salvar</span>}
    </div>
  );
}

/** Extrato do formulário de pré-contrato — onde estão idade e nº de aniversariantes. */
function FormResponseExtract({ entry }: { entry: Fila3DEntry }) {
  const response = entry.form_response;
  if (!response) {
    return (
      <p className="text-sm text-muted">
        Nenhum formulário de pré-contrato vinculado a este evento.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        {response.form_type_label} · {response.contact_name}
        {response.contact_phone_display ? ` · ${response.contact_phone_display}` : ""}
      </p>
      {response.sections.map((section, index) => (
        <div key={`${section.secao}-${index}`}>
          <h4 className="mb-1 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
            {section.secao || "Respostas"}
          </h4>
          <dl className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
            {section.campos.map((campo, fieldIndex) => (
              <div key={`${campo.chave}-${fieldIndex}`} className="contents">
                <dt className="truncate text-muted">{campo.rotulo}</dt>
                <dd className="font-medium text-ink">{campo.valor}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}

/** Personagens contratados do evento — com miniatura quadrada (Princípio X.2). */
function RolesList({ entry }: { entry: Fila3DEntry }) {
  const characters = entry.roles.filter((role) => role.role_type === "character");
  if (characters.length === 0) {
    return <p className="text-sm text-muted">Nenhum personagem cadastrado no evento.</p>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {characters.map((role) => (
        <li
          key={role.id}
          className="flex items-center gap-2 rounded-md border border-line bg-surface-2/60 px-2 py-1"
        >
          <AvatarThumb
            src={assetUrl(role.talent_photo_url)}
            name={role.character_name}
            shape="square"
            size="sm"
            fallbackIcon="🎭"
          />
          <span className="text-sm text-ink">
            {role.character_name}
            {role.talent_name && <span className="text-muted"> · {role.talent_name}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Dialog "Ver Detalhes para Impressão": cruza elenco + formulário da cliente. */
function DetalhesDialog({ entry, onClose }: { entry: Fila3DEntry | null; onClose: () => void }) {
  const open = entry !== null;
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Detalhes para impressão</DialogTitle>
          <DialogDescription>
            {entry?.event.title} · {formatShortDate(entry?.event.start_at)}
          </DialogDescription>
        </DialogHeader>
        {entry && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-md border border-line bg-surface-2/60 p-3">
              <AvatarThumb
                src={assetUrl(entry.item?.photo_url)}
                name={entry.item?.name}
                shape="square"
                size="lg"
              />
              <div className="min-w-0">
                <div className="font-medium text-ink">{entry.item?.name ?? "Peça removida"}</div>
                <div className="text-sm text-muted">
                  {entry.quantity}x · prazo {formatDeadline(entry.deadline_date)} ·{" "}
                  {GIFT_3D_STATUS_LABELS[entry.status]}
                </div>
              </div>
            </div>

            {entry.notes && (
              <div>
                <h3 className="mb-1 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
                  Observações
                </h3>
                <p className="whitespace-pre-line text-sm text-ink">{entry.notes}</p>
              </div>
            )}

            <div>
              <h3 className="mb-1 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
                Personagens contratados
              </h3>
              <RolesList entry={entry} />
            </div>

            <div>
              <h3 className="mb-1 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
                Formulário de pré-contrato
              </h3>
              <FormResponseExtract entry={entry} />
            </div>

            <Button asChild variant="outline" size="sm">
              <Link to={`/events/${entry.event_id}`}>Abrir evento ↗</Link>
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Fila de Impressão (`/3d/fila`) — painel operacional do Artista 3D (feature 200).
 *
 * Tabela densa ordenada por prazo (mais apertado primeiro), com seletor rápido de status e o
 * Dialog "Ver Detalhes para Impressão", que cruza os personagens contratados com o extrato do
 * formulário de pré-contrato — é lá que estão a idade e a quantidade de aniversariantes.
 */
export function Fila3DPage() {
  const reduceMotion = useReducedMotion();
  const query = useFila3D();
  const [detalhe, setDetalhe] = useState<Fila3DEntry | null>(null);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Fila de Impressão"
        subtitle="Presentes 3D pendentes dos eventos SHOW, do prazo mais apertado ao mais folgado."
        className="mb-0"
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a fila de impressão.
        </div>
      )}
      {query.data && query.data.items.length === 0 && (
        <p className="text-sm text-muted">
          Nenhum presente 3D pendente. Tudo entregue por aqui. 🎉
        </p>
      )}

      {query.data && query.data.items.length > 0 && (
        <motion.div
          className="rounded-lg border border-line bg-panel"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <Table>
            <thead>
              <TableRow head>
                <TableCell as="th">Peça</TableCell>
                <TableCell as="th">Evento</TableCell>
                <TableCell as="th">Data do evento</TableCell>
                <TableCell as="th">Prazo</TableCell>
                <TableCell as="th" align="right">
                  Qtd.
                </TableCell>
                <TableCell as="th">Status</TableCell>
                <TableCell as="th" />
              </TableRow>
            </thead>
            <tbody>
              {query.data.items.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <AvatarThumb
                        src={assetUrl(entry.item?.photo_url)}
                        name={entry.item?.name}
                        shape="square"
                        size="md"
                      />
                      <span className="font-medium text-ink">
                        {entry.item?.name ?? "Peça removida"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Link to={`/events/${entry.event_id}`} className="text-blue hover:underline">
                      {entry.event.title}
                    </Link>
                    {entry.event.location && (
                      <div className="text-xs text-muted">{entry.event.location}</div>
                    )}
                  </TableCell>
                  <TableCell>{formatShortDate(entry.event.start_at)}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <span>{formatDeadline(entry.deadline_date)}</span>
                      <DeadlineBadge deadline={entry.deadline_date} />
                    </div>
                  </TableCell>
                  <TableCell align="right">{entry.quantity}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <Badge tone={GIFT_3D_STATUS_TONES[entry.status]}>
                        {GIFT_3D_STATUS_LABELS[entry.status]}
                      </Badge>
                      <StatusSelect entry={entry} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" onClick={() => setDetalhe(entry)}>
                      Ver Detalhes para Impressão
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
        </motion.div>
      )}

      <DetalhesDialog entry={detalhe} onClose={() => setDetalhe(null)} />
    </div>
  );
}
