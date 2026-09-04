import { Card, CardContent, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { RatingLink } from "../components/RatingLink";
import { formatShortDate } from "../lib/format";
import { useHistorico, type PortalHistoricoItem } from "../lib/portalHistorico";
import { ErroDeCarregamento } from "../components/ErroDeCarregamento";

function TotalCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`text-base font-semibold ${tone}`}>R$ {formatBRL(value)}</p>
    </div>
  );
}

// `rotuloAvaliacao` e o link com a estrela nasceram aqui e foram promovidos para
// `components/RatingLink.tsx` na feature 229, quando a seção Histórico da Agenda passou a
// precisar exatamente do mesmo botão (fonte única, Princípio I).

function HistoricoRow({ item }: { item: PortalHistoricoItem }) {
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

        <RatingLink eventId={item.event_id} />
      </CardContent>
    </Card>
  );
}

/** Histórico completo de apresentações, com somatórios de cachê recebido e pendente. */
export function PortalHistoricoPage() {
  const historicoQuery = useHistorico();

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
      <ErroDeCarregamento
        erro={historicoQuery.error}
        oQue="seu histórico"
        aoTentarDeNovo={() => void historicoQuery.refetch()}
        carregando={historicoQuery.isFetching}
      />
    );
  }

  const { items, totals } = historicoQuery.data;

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
            <HistoricoRow key={item.role_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
