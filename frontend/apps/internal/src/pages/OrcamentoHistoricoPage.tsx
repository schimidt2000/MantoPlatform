import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useDeleteOrcamentoHistorico,
  useEnviarEmailOrcamento,
  useOrcamentoDetalhe,
  useOrcamentoHistorico,
  useOrcamentoPdf,
  type OrcamentoHistoricoEntry,
} from "../lib/orcamento";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function EntryDetail({ entry, onClose }: { entry: OrcamentoHistoricoEntry; onClose: () => void }) {
  const detalhe = useOrcamentoDetalhe(entry.id);
  const pdf = useOrcamentoPdf();
  const email = useEnviarEmailOrcamento();
  const [emailTo, setEmailTo] = useState("");

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between">
          <p className="font-medium text-ink">
            {entry.client_name || "Sem cliente"} — {entry.event_location || "sem local"}
          </p>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Fechar
          </Button>
        </div>
        {detalhe.isLoading && <Skeleton className="h-24 w-full" />}
        {detalhe.data && (
          <pre className="whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-xs text-ink">
            {detalhe.data.quote.message}
          </pre>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            loading={pdf.isPending}
            onClick={() => pdf.mutate({ id: entry.id, clientName: entry.client_name })}
          >
            Baixar PDF
          </Button>
          <input
            type="email"
            placeholder="E-mail do cliente"
            className="h-8 w-56 rounded-md border border-line bg-panel px-2 text-xs"
            value={emailTo}
            onChange={(e) => setEmailTo(e.target.value)}
          />
          <Button
            size="sm"
            variant="ghost"
            loading={email.isPending}
            onClick={() => email.mutate({ id: entry.id, to: emailTo })}
          >
            Enviar por e-mail
          </Button>
        </div>
        {email.isSuccess && <p className="text-xs text-green">E-mail enviado.</p>}
        {email.isError && <p className="text-xs text-red">Não foi possível enviar o e-mail.</p>}
      </CardContent>
    </Card>
  );
}

export function OrcamentoHistoricoPage() {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<OrcamentoHistoricoEntry | null>(null);
  const query = useOrcamentoHistorico({ q });
  const del = useDeleteOrcamentoHistorico();

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Orçamentos"
        subtitle="Histórico de orçamentos calculados"
        className="mb-0"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/orcamento">Calculadora ›</Link>
          </Button>
        }
      />

      <input
        className="h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
        placeholder="Buscar por cliente ou local…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o histórico.
        </div>
      )}

      {query.data && query.data.entries.length === 0 && (
        <p className="text-sm text-muted">Nenhum orçamento encontrado.</p>
      )}

      {query.data && (
        <div className="space-y-2">
          {query.data.entries.map((e) => (
            <div key={e.id}>
              <Card>
                <CardContent className="flex items-center justify-between gap-3 p-3">
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => setSelected(selected?.id === e.id ? null : e)}
                  >
                    <p className="truncate font-medium text-ink">{e.client_name || "Sem cliente"}</p>
                    <p className="text-xs text-muted">
                      {formatDateTime(e.created_at)}
                      {query.data!.is_superadmin && e.user_name && ` · ${e.user_name}`}
                    </p>
                  </button>
                  <div className="text-right">
                    <p className="text-sm font-medium tabular-nums text-ink">{brl(e.total_4h)}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={del.isPending}
                      onClick={() => {
                        if (window.confirm("Excluir este orçamento?")) del.mutate(e.id);
                      }}
                    >
                      Excluir
                    </Button>
                  </div>
                </CardContent>
              </Card>
              {selected?.id === e.id && <EntryDetail entry={e} onClose={() => setSelected(null)} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
