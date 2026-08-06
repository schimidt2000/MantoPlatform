import { useState } from "react";
import { Button, PageHeader, Skeleton, Table, TableCell, TableRow } from "@manto/ui";
import { useAdminLogs } from "../lib/adminConfig";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

export function AdminLogsPage() {
  const [entityType, setEntityType] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(1);
  const query = useAdminLogs(entityType, actor, page);

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-6">
      <PageHeader title="Logs de auditoria" className="mb-0" />

      <div className="flex flex-wrap gap-2">
        {query.data && (
          <select
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos os tipos</option>
            {query.data.entity_types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
        <input
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Filtrar por quem executou…"
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os logs.
        </div>
      )}

      {query.data && (
        <>
          {/* Tabela e não cards empilhados: log é dado tabular — quem/quando/o quê alinhados em
              colunas dá para varrer de cima a baixo, e a coluna de detalhe usa a largura da tela. */}
          <div className="rounded-md border border-line bg-panel">
            <Table>
              <thead>
                <TableRow head>
                  <TableCell as="th" className="w-40">
                    Quando
                  </TableCell>
                  <TableCell as="th" className="w-48">
                    Quem
                  </TableCell>
                  <TableCell as="th" className="w-24">
                    Ação
                  </TableCell>
                  <TableCell as="th" className="hidden w-56 md:table-cell">
                    Entidade
                  </TableCell>
                  <TableCell as="th">Detalhe</TableCell>
                </TableRow>
              </thead>
              <tbody>
                {query.data.items.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-muted">
                      {formatDate(log.created_at)}
                    </TableCell>
                    <TableCell className="font-medium text-ink">{log.actor_name}</TableCell>
                    <TableCell className="text-ink">{log.action}</TableCell>
                    <TableCell className="hidden text-muted md:table-cell">
                      {log.entity_name ? `${log.entity_type}: ${log.entity_name}` : "—"}
                    </TableCell>
                    <TableCell className="text-muted">{log.detail || "—"}</TableCell>
                  </TableRow>
                ))}
              </tbody>
            </Table>
          </div>
          {query.data.pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ‹ Anterior
              </Button>
              <span className="text-sm text-muted">
                Página {query.data.page} de {query.data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= query.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima ›
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
