import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Badge, Button } from "@manto/ui";
import type { EventoDetalhe } from "../../lib/agenda";
import { useDeleteClientFeedback } from "../../lib/clientes";
import { Empty, formatDay, Panel, Stars } from "./parts";

/** Rótulo curto de cada critério avaliado pelos artistas no portal. */
/**
 * Rótulos das sub-avaliações — precisam bater com `RATING_CATEGORIES`
 * (`app/talents/rating_ops.py`), que é a fonte única lida pelo panorama de avaliações.
 *
 * `texto` é "Show no geral" e não "Texto": é a pergunta que o artista respondeu no portal
 * (coreografia, posicionamento, texto e interações). "Texto" fazia o leitor entender falas/roteiro
 * (feature 232). `coordenacao` fica abreviado porque aqui o rótulo vive dentro de um badge.
 */
const CATEGORY_LABELS: Record<string, string> = {
  som: "Som",
  figurino: "Figurino",
  texto: "Show no geral",
  coordenacao: "Coord.",
  maquiagem: "Maquiagem",
  artista: "Artista",
};

/** Avaliações dos artistas sobre o evento (portal do talento) — média + lista individual. */
function RatingsPanel({ data }: { data: EventoDetalhe }) {
  const ratings = data.ratings;
  if (!ratings) return null;

  return (
    <Panel
      title="Avaliações dos artistas"
      actions={
        ratings.count > 0 ? (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-lg font-semibold text-ink tabular-nums">{ratings.average}</span>
            <Stars score={Math.round(ratings.average ?? 0)} />
            <span className="text-xs text-muted">{ratings.count} avaliações</span>
          </span>
        ) : null
      }
    >
      {ratings.items.length === 0 ? (
        <Empty>Nenhuma avaliação recebida ainda.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {ratings.items.map((rating) => (
            <li key={rating.id} className="py-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{rating.talent_name}</span>
                <Stars score={rating.score} />
                <span className="text-xs text-muted tabular-nums">
                  {formatDay(rating.submitted_at)}
                </span>
              </div>
              {rating.comment && (
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-muted">{rating.comment}</p>
              )}
              {rating.sub_ratings.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {rating.sub_ratings.map((sub, index) => (
                    <span key={index} title={sub.comment ?? undefined}>
                      <Badge className="max-w-full truncate">
                        {CATEGORY_LABELS[sub.category] ?? sub.category}
                        {sub.subject_name ? ` · ${sub.subject_name}` : ""} {"★".repeat(sub.score)}
                      </Badge>
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** Feedback da cliente (link público `/avaliar/<token>`). */
function ClientFeedbackPanel({ data }: { data: EventoDetalhe }) {
  const feedbacks = data.client_feedbacks;
  // Exclusão manual de feedback incorreto — só SUPERADMIN (o endpoint valida de novo).
  const canDelete = Boolean(data.flags.is_superadmin);
  const deleteFeedback = useDeleteClientFeedback();
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  if (!feedbacks) return null;

  return (
    <Panel title="Feedback da cliente">
      {feedbacks.length === 0 ? (
        <Empty>
          Nenhum feedback recebido ainda. Use “Ferramentas” → “Pedir feedback da cliente” para
          copiar o link e enviar à cliente.
        </Empty>
      ) : (
        <ul className="divide-y divide-line">
          {feedbacks.map((feedback) => (
            <li key={feedback.id} className="py-2">
              <div className="flex flex-wrap items-center gap-2">
                <Stars score={feedback.score} />
                <span className="font-medium text-ink">{feedback.client_name ?? "Cliente"}</span>
                <span className="text-xs text-muted tabular-nums">
                  {formatDay(feedback.submitted_at)}
                </span>
                {canDelete && confirmingId !== feedback.id && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto text-muted hover:text-red"
                    aria-label="Excluir avaliação"
                    onClick={() => setConfirmingId(feedback.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                )}
              </div>
              {confirmingId === feedback.id && (
                <div className="mt-1.5 flex flex-wrap items-center gap-2 rounded-md border border-red bg-red-soft p-2 text-sm">
                  <span className="text-red">Excluir esta avaliação? A ação não pode ser desfeita.</span>
                  <Button variant="outline" size="sm" onClick={() => setConfirmingId(null)}>
                    Cancelar
                  </Button>
                  <Button
                    size="sm"
                    loading={deleteFeedback.isPending}
                    onClick={() =>
                      deleteFeedback.mutate(feedback.id, {
                        onSettled: () => setConfirmingId(null),
                      })
                    }
                  >
                    Excluir
                  </Button>
                </div>
              )}
              {feedback.comment && (
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-muted">{feedback.comment}</p>
              )}
              {feedback.tags.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {feedback.tags.map((tag) => (
                    <Badge key={tag} tone="green">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export interface FeedbackSectionProps {
  data: EventoDetalhe;
}

/** Avaliações dos artistas + feedback da cliente (rodapé da tela, feature 190). */
export function FeedbackSection({ data }: FeedbackSectionProps) {
  return (
    <>
      <RatingsPanel data={data} />
      <ClientFeedbackPanel data={data} />
    </>
  );
}
