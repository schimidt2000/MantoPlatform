import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useDeleteOrcamentoHistorico,
  useEnviarEmailOrcamento,
  useOrcamentoDetalhe,
  useOrcamentoHistorico,
  useOrcamentoPdf,
  type OrcamentoHistoricoEntry,
  type OrcamentoHistoricoFilters,
} from "../lib/orcamento";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

const EMPTY_FILTERS: OrcamentoHistoricoFilters = {
  q: "",
  date_from: "",
  date_to: "",
  min_val: "",
  max_val: "",
  user_id: "",
  has_show: "",
};

const FIELD =
  "h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function VerDialog({ entry, onClose }: { entry: OrcamentoHistoricoEntry; onClose: () => void }) {
  const detalhe = useOrcamentoDetalhe(entry.id);
  const pdf = useOrcamentoPdf();
  const email = useEnviarEmailOrcamento();
  const [emailTo, setEmailTo] = useState("");

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent open className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{entry.client_name || "Sem cliente"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          {detalhe.isLoading && <Skeleton className="h-24 w-full" />}
          {detalhe.data && (
            <pre className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-xs text-ink">
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
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function OrcamentoHistoricoPage() {
  const [filters, setFilters] = useState<OrcamentoHistoricoFilters>(EMPTY_FILTERS);
  const [draft, setDraft] = useState<OrcamentoHistoricoFilters>(EMPTY_FILTERS);
  const [verEntry, setVerEntry] = useState<OrcamentoHistoricoEntry | null>(null);
  const query = useOrcamentoHistorico(filters);
  const del = useDeleteOrcamentoHistorico();

  const applyFilters = () => setFilters(draft);
  const clearFilters = () => {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
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

      <div className="rounded-md border border-line bg-panel p-3">
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <Input
            className={FIELD}
            placeholder="Cliente ou local…"
            value={draft.q}
            onChange={(e) => setDraft({ ...draft, q: e.target.value })}
          />
          <Input
            className={FIELD}
            type="date"
            aria-label="Data inicial (gerado em)"
            value={draft.date_from}
            onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
          />
          <Input
            className={FIELD}
            type="date"
            aria-label="Data final (gerado em)"
            value={draft.date_to}
            onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
          />
          <Input
            className={FIELD}
            placeholder="Valor mín. (4h)"
            value={draft.min_val}
            onChange={(e) => setDraft({ ...draft, min_val: e.target.value })}
          />
          <Input
            className={FIELD}
            placeholder="Valor máx. (4h)"
            value={draft.max_val}
            onChange={(e) => setDraft({ ...draft, max_val: e.target.value })}
          />
          <select
            className={FIELD}
            value={draft.has_show}
            onChange={(e) => setDraft({ ...draft, has_show: e.target.value })}
          >
            <option value="">Todos os tipos</option>
            <option value="1">Com show</option>
            <option value="0">Sem show</option>
          </select>
          {query.data?.is_superadmin && (
            <select
              className={FIELD}
              value={draft.user_id}
              onChange={(e) => setDraft({ ...draft, user_id: e.target.value })}
            >
              <option value="">Todos os vendedores</option>
              {query.data.users.map((u) => (
                <option key={u.id} value={String(u.id)}>
                  {u.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={applyFilters}>
            Filtrar
          </Button>
          <Button size="sm" variant="ghost" onClick={clearFilters}>
            Limpar
          </Button>
        </div>
      </div>

      {query.isLoading && <Skeleton className="h-64 w-full" />}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o histórico.
        </div>
      )}

      {query.data && query.data.entries.length === 0 && (
        <p className="text-sm text-muted">Nenhum orçamento encontrado.</p>
      )}

      {query.data && query.data.entries.length > 0 && (
        <Table className="min-w-[980px]">
          <thead>
            <TableRow head>
              <TableCell as="th">Data/Hora</TableCell>
              {query.data.is_superadmin && <TableCell as="th">Vendedor</TableCell>}
              <TableCell as="th">Cliente</TableCell>
              <TableCell as="th">Local</TableCell>
              <TableCell as="th">Tipo</TableCell>
              <TableCell as="th" align="right">
                1h
              </TableCell>
              <TableCell as="th" align="right">
                2h
              </TableCell>
              <TableCell as="th" align="right">
                3h
              </TableCell>
              <TableCell as="th" align="right">
                4h
              </TableCell>
              <TableCell as="th" align="right">
                Ações
              </TableCell>
            </TableRow>
          </thead>
          <tbody>
            {query.data.entries.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="whitespace-nowrap text-ink">{formatDateTime(e.created_at)}</TableCell>
                {query.data!.is_superadmin && (
                  <TableCell className="text-ink">{e.user_name || "—"}</TableCell>
                )}
                <TableCell className="text-ink">{e.client_name || "Sem cliente"}</TableCell>
                <TableCell className="text-ink">{e.event_location || "—"}</TableCell>
                <TableCell>
                  <Badge tone={e.has_show ? "gold" : "neutral"}>{e.has_show ? "Com show" : "Sem show"}</Badge>
                </TableCell>
                <TableCell align="right">{brl(e.total_1h)}</TableCell>
                <TableCell align="right">{brl(e.total_2h)}</TableCell>
                <TableCell align="right">{brl(e.total_3h)}</TableCell>
                <TableCell align="right" className="font-medium">
                  {brl(e.total_4h)}
                </TableCell>
                <TableCell align="right">
                  <div className="flex flex-wrap justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setVerEntry(e)}>
                      Ver
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link to={`/orcamento?recalcular_id=${e.id}`}>Recalcular</Link>
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link to={`/events/new?orcamento_id=${e.id}`}>Criar evento</Link>
                    </Button>
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
                </TableCell>
              </TableRow>
            ))}
          </tbody>
        </Table>
      )}

      {verEntry && <VerDialog entry={verEntry} onClose={() => setVerEntry(null)} />}
    </div>
  );
}
