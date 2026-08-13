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
  isSnapshotV2,
  useEducaMantoHistorico,
  useEducaMantoQuoteDetalhe,
  useOrcamentoPdf,
  type EducaMantoHistoricoEntry,
  type SnapshotV1,
  type SnapshotV2,
} from "../lib/educamanto";

const RESP_LABELS: Record<string, string> = {
  som: "Sonorização",
  iluminacao: "Iluminação",
  alimentacao: "Alimentação",
  cenario: "Cenário",
};

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

/** Snapshot v1 (legado, por pacote) — mantido idêntico para orçamentos antigos. */
function DetalheV1({ snap }: { snap: SnapshotV1 }) {
  return (
    <div className="space-y-3 text-sm text-ink">
      <p>
        <span className="text-muted">Dias:</span> {snap.d1} × 1 sessão, {snap.d2} × 2 sessões
      </p>
      <p>
        <span className="text-muted">Ensemble:</span> {snap.ensemble}
      </p>
      <p>
        <span className="text-muted">Comissão do vendedor:</span> {brl(snap.acrescimo)}
      </p>
      {(snap.transporte?.total ?? 0) > 0 && snap.transporte && (
        <p>
          <span className="text-muted">Transporte:</span> {brl(snap.transporte.total)} —{" "}
          {snap.transporte.label}
        </p>
      )}
      <Table>
        <thead>
          <TableRow head>
            <TableCell as="th">Pacote</TableCell>
            <TableCell as="th" align="right">Sem nota</TableCell>
            <TableCell as="th" align="right">Com nota</TableCell>
          </TableRow>
        </thead>
        <tbody>
          {snap.packages.map((p) => (
            <TableRow key={p.id}>
              <TableCell className="text-ink">{p.name}</TableCell>
              <TableCell align="right">{brl(p.sem_nota)}</TableCell>
              <TableCell align="right">{brl(p.com_nota)}</TableCell>
            </TableRow>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

/** Snapshot v2 (feature 235) — uma seção por configuração (página do PDF). */
function DetalheV2({ snap }: { snap: SnapshotV2 }) {
  return (
    <div className="space-y-4 text-sm text-ink">
      {snap.configs.map((config, i) => (
        <div key={i} className="rounded-md border border-line p-3">
          <p className="mb-1 font-semibold">
            Página {i + 1} — {config.musical_name}
          </p>
          <p className="text-xs text-muted">
            {config.d1 > 0 && `${config.d1} × 1 sessão`}
            {config.d1 > 0 && config.d2 > 0 && " · "}
            {config.d2 > 0 && `${config.d2} × 2 sessões`}
            {config.ensemble > 0 && ` · ensemble ${config.ensemble}`}
            {` · equipe ${config.resultado.headcount}`}
          </p>
          <p className="mt-1 text-xs">
            {Object.entries(config.responsabilidades)
              .map(([chave, resp]) => `${RESP_LABELS[chave] ?? chave}: ${resp === "manto" ? "Manto" : "contratante"}`)
              .join(" · ")}
          </p>
          <p className="mt-2">
            <span className="text-muted">Sem NF:</span>{" "}
            <strong>{brl(config.resultado.sem_nota)}</strong>{" "}
            <span className="text-muted">· Com NF:</span>{" "}
            <strong>{brl(config.resultado.com_nota)}</strong>
          </p>
          <p className="text-xs text-muted">
            À vista: {brl(config.resultado.a_vista_sem_nota)} sem NF ·{" "}
            {brl(config.resultado.a_vista_com_nota)} com NF
            {config.acrescimo > 0 && ` · comissão ${brl(config.resultado.acrescimo_efetivo)}`}
          </p>
          {(config.resultado.transporte?.total ?? 0) > 0 && (
            <p className="text-xs text-muted">
              Transporte fora de SP: {brl(config.resultado.transporte?.total ?? 0)}
            </p>
          )}
          {config.contratacao_manto && (
            <div className="mt-2 rounded bg-surface-2 p-2 text-xs">
              <p className="font-semibold text-ink">+ Contratação Manto</p>
              {Object.entries(config.resultado.combinados).map(([dur, tot]) => (
                <p key={dur} className="text-muted">
                  Total com {dur}: {brl(tot.sem_nota)} sem NF · {brl(tot.com_nota)} com NF
                </p>
              ))}
            </div>
          )}
        </div>
      ))}
      {snap.observacao && (
        <p className="text-xs text-muted">
          <span className="font-semibold text-ink">Observação:</span> {snap.observacao}
        </p>
      )}
    </div>
  );
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
        {detalhe.data &&
          (isSnapshotV2(detalhe.data) ? (
            <DetalheV2 snap={detalhe.data} />
          ) : (
            <DetalheV1 snap={detalhe.data} />
          ))}
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
          placeholder="Buscar por cliente ou musical…"
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
              <TableCell as="th">Musicais</TableCell>
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
                <TableCell className="text-ink">{entry.packages_label || "—"}</TableCell>
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
