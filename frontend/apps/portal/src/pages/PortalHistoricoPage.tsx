import { Link } from "react-router-dom";
import { Card, CardContent, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { Star } from "lucide-react";
import { formatShortDate } from "../lib/format";
import { useHistorico, type PortalHistoricoItem } from "../lib/portalHistorico";
import { usePendingRatings } from "../lib/portalRatings";

function TotalCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`text-base font-semibold ${tone}`}>R$ {formatBRL(value)}</p>
    </div>
  );
}

function HistoricoRow({
  item,
  canRate,
  canEditRating,
}: {
  item: PortalHistoricoItem;
  canRate: boolean;
  canEditRating: boolean;
}) {
  const paid = item.payment_status === "pago";

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium text-ink">{item.title}</p>
            <p className="text-xs text-muted">
              {formatShortDate(item.start_at)}
              {item.location ? ` · ${item.location}` : ""}
            </p>
            <p className="text-xs text-muted">Personagem: {item.character_name}</p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-semibold text-ink">R$ {formatBRL(item.cache_total)}</p>
            <p className={`text-xs ${paid ? "text-green" : "text-muted"}`}>
              {paid ? "pago" : "pendente"}
            </p>
          </div>
        </div>

        {item.travel_cache > 0 && (
          <p className="text-xs text-muted">
            Cachê R$ {formatBRL(item.cache_value)} + deslocamento R$ {formatBRL(item.travel_cache)}
          </p>
        )}

        {(canRate || canEditRating) && (
          <Link
            to={`/eventos/${item.event_id}/avaliar`}
            className="inline-flex min-h-[44px] items-center gap-2 text-sm font-medium text-accent hover:underline"
          >
            <Star className="h-4 w-4" aria-hidden="true" />
            {canRate ? "Avaliar este evento" : "Editar minha avaliação"}
          </Link>
        )}
      </CardContent>
    </Card>
  );
}

/** Histórico completo de apresentações, com somatórios de cachê recebido e pendente. */
export function PortalHistoricoPage() {
  const historicoQuery = useHistorico();
  const ratingsQuery = usePendingRatings();

  if (historicoQuery.isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (historicoQuery.isError || !historicoQuery.data) {
    return (
      <div className="p-4">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar seu histórico.
        </div>
      </div>
    );
  }

  const { items, totals } = historicoQuery.data;
  const rateable = new Set(ratingsQuery.data?.rateable_event_ids ?? []);
  const editable = new Set(ratingsQuery.data?.editable_event_ids ?? []);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-lg font-semibold text-ink">Histórico de apresentações</h1>

      <section aria-label="Somatórios de cachê" className="grid grid-cols-2 gap-2">
        <TotalCard label="Recebido" value={totals.paid} tone="text-green" />
        <TotalCard label="A receber" value={totals.pending} tone="text-ink" />
        <div className="col-span-2 rounded-lg border border-line bg-panel p-3">
          <p className="text-xs text-muted">
            Total acumulado em {totals.count} {totals.count === 1 ? "apresentação" : "apresentações"}
          </p>
          <p className="text-lg font-semibold text-accent">R$ {formatBRL(totals.overall)}</p>
        </div>
      </section>

      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">
          Você ainda não tem apresentações no histórico. Assim que participar de um evento, ele
          aparece aqui.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <HistoricoRow
              key={item.role_id}
              item={item}
              canRate={rateable.has(item.event_id)}
              canEditRating={editable.has(item.event_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
