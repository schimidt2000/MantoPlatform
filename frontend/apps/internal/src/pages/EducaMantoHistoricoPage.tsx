import { useState } from "react";
import { Link } from "react-router-dom";
import { formatBRL } from "@manto/money";
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import {
  useEducaMantoHistorico,
  useEducaMantoQuoteDetalhe,
  useOrcamentoPdf,
  type EducaMantoHistoricoEntry,
} from "../lib/educamanto";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function VerDialog({ entry, onClose }: { entry: EducaMantoHistoricoEntry; onClose: () => void }) {
  const detalhe = useEducaMantoQuoteDetalhe(entry.id);

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent open className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{entry.client_name || "Cliente não informado"}</DialogTitle>
        </DialogHeader>
        {detalhe.isLoading && <Skeleton className="h-40 w-full" />}
        {detalhe.data && (
          <div className="space-y-3 text-sm text-ink">
            <p>
              <span className="text-muted">Dias:</span> {detalhe.data.d1} × 1 sessão,{" "}
              {detalhe.data.d2} × 2 sessões
            </p>
            <p>
              <span className="text-muted">Ensemble:</span> {detalhe.data.ensemble}
            </p>
            <p>
              <span className="text-muted">Comissão do vendedor:</span> {brl(detalhe.data.acrescimo)}
            </p>
            {detalhe.data.transporte?.total > 0 && (
              <p>
                <span className="text-muted">Transporte:</span> {brl(detalhe.data.transporte.total)} —{" "}
                {detalhe.data.transporte.label}
              </p>
            )}
            <Table>
              <thead>
                <TableRow head>
                  <TableCell as="th">Pacote</TableCell>
                  <TableCell as="th" align="right">
                    Sem nota
                  </TableCell>
                  <TableCell as="th" align="right">
                    Com nota
                  </TableCell>
                </TableRow>
              </thead>
              <tbody>
                {detalhe.data.packages.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="text-ink">{p.name}</TableCell>
                    <TableCell align="right">{brl(p.sem_nota)}</TableCell>
                    <TableCell align="right">{brl(p.com_nota)}</TableCell>
                  </TableRow>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function EducaMantoHistoricoPage() {
  const [q, setQ] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [userId, setUserId] = useState("");
  const [verEntry, setVerEntry] = useState<EducaMantoHistoricoEntry | null>(null);

  const historicoQuery = useEducaMantoHistorico({
    q: q || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    user_id: userId || undefined,
  });
  const openPdf = useOrcamentoPdf();

  const entries = historicoQuery.data?.entries ?? [];
  const users = historicoQuery.data?.users;
  const isSuperadmin = users !== undefined;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Histórico de orçamentos"
        className="mb-0"
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/educamanto">‹ Calculadora</Link>
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2">
        <input
          className="h-9 min-w-[200px] flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Buscar por cliente ou pacote…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <input
          type="date"
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          aria-label="De"
        />
        <input
          type="date"
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          aria-label="Até"
        />
        {isSuperadmin && users && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          >
            <option value="">Todos os usuários</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {historicoQuery.isLoading && <Skeleton className="h-64 w-full" />}

      {historicoQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o histórico.
        </div>
      )}

      {historicoQuery.data && entries.length === 0 && (
        <p className="text-sm text-muted">Nenhum orçamento encontrado.</p>
      )}

      {entries.length > 0 && (
        <Table className="min-w-[760px]">
          <thead>
            <TableRow head>
              <TableCell as="th">Data/Hora</TableCell>
              <TableCell as="th">Cliente</TableCell>
              <TableCell as="th">Pacotes Usados</TableCell>
              {isSuperadmin && <TableCell as="th">Gerado Por</TableCell>}
              <TableCell as="th" align="right">
                Ações
              </TableCell>
            </TableRow>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="whitespace-nowrap text-ink">{formatDateTime(entry.created_at)}</TableCell>
                <TableCell className="text-ink">{entry.client_name || "Cliente não informado"}</TableCell>
                <TableCell className="text-ink">{entry.packages_label}</TableCell>
                {isSuperadmin && <TableCell className="text-ink">{entry.user_name || "—"}</TableCell>}
                <TableCell align="right">
                  <div className="flex flex-wrap justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setVerEntry(entry)}>
                      Ver
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link to={`/educamanto?recalcular_id=${entry.id}`}>Recalcular</Link>
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={openPdf.isPending}
                      onClick={() => openPdf.mutate(entry.id)}
                    >
                      Baixar PDF
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
