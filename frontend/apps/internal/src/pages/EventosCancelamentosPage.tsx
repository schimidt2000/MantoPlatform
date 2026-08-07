import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCancelamentos } from "../lib/eventOps";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** `dd/mm/aaaa` sem passar por `new Date()` — data pura não pode escorregar de fuso. */
function data(iso: string | null): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : iso;
}

const STATUS_DEVOLUCAO: Record<string, { label: string; tone: "green" | "gold" }> = {
  pago: { label: "devolvido", tone: "green" },
  nao_pago: { label: "a devolver", tone: "gold" },
};

/**
 * Fila do Superadmin (feature 224): pedidos de exclusão do Comercial aguardando decisão, e o
 * histórico dos eventos cancelados com a situação da devolução. É por aqui que se chega a um
 * evento cancelado — ele sumiu da agenda de propósito.
 */
export function EventosCancelamentosPage() {
  const query = useCancelamentos();
  const pendentes = query.data?.pendentes ?? [];
  const cancelados = query.data?.cancelados ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Exclusões e cancelamentos"
        subtitle="Pedidos do Comercial e eventos cancelados, com a devolução de cada um"
        className="mb-0"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/agenda">← Agenda</Link>
          </Button>
        }
      />

      {query.isLoading && <Skeleton className="h-40 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar a lista. Esta tela é restrita ao Superadmin.
        </div>
      )}

      {query.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                Aguardando decisão{" "}
                {pendentes.length > 0 && <Badge tone="gold">{pendentes.length}</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {pendentes.length === 0 ? (
                <p className="p-4 text-sm text-muted">Nenhum pedido pendente.</p>
              ) : (
                <Table>
                  <thead>
                    <TableRow head>
                      <TableCell as="th">Evento</TableCell>
                      <TableCell as="th">Data</TableCell>
                      <TableCell as="th" align="right">
                        Venda
                      </TableCell>
                      <TableCell as="th">Pedido por</TableCell>
                      <TableCell as="th">Motivo</TableCell>
                      <TableCell as="th" align="right">
                        Ações
                      </TableCell>
                    </TableRow>
                  </thead>
                  <tbody>
                    {pendentes.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell className="text-ink">{p.title}</TableCell>
                        <TableCell className="tabular-nums">{data(p.start_at)}</TableCell>
                        <TableCell align="right" className="tabular-nums">
                          {brl(p.sale_value)}
                        </TableCell>
                        <TableCell>
                          {p.requested_by ?? "—"}
                          <span className="block text-xs text-muted">
                            {data(p.requested_at)}
                          </span>
                        </TableCell>
                        <TableCell className="text-muted">{p.reason ?? "—"}</TableCell>
                        <TableCell align="right">
                          <Button asChild size="sm" variant="outline">
                            <Link to={`/events/${p.id}`}>Abrir evento</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Eventos cancelados</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {cancelados.length === 0 ? (
                <p className="p-4 text-sm text-muted">Nenhum evento cancelado.</p>
              ) : (
                <Table className="min-w-[820px]">
                  <thead>
                    <TableRow head>
                      <TableCell as="th">Evento</TableCell>
                      <TableCell as="th">Data</TableCell>
                      <TableCell as="th" align="right">
                        Venda
                      </TableCell>
                      <TableCell as="th">Cancelado</TableCell>
                      <TableCell as="th">Motivo</TableCell>
                      <TableCell as="th">Devolução</TableCell>
                      <TableCell as="th" align="right">
                        Ações
                      </TableCell>
                    </TableRow>
                  </thead>
                  <tbody>
                    {cancelados.map((c) => {
                      const situacao = c.devolucao
                        ? STATUS_DEVOLUCAO[c.devolucao.payment_status] ??
                          STATUS_DEVOLUCAO.nao_pago
                        : null;
                      return (
                        <TableRow key={c.id}>
                          <TableCell className="text-ink">{c.title}</TableCell>
                          <TableCell className="tabular-nums">{data(c.start_at)}</TableCell>
                          <TableCell align="right" className="tabular-nums">
                            {brl(c.sale_value)}
                          </TableCell>
                          <TableCell>
                            {c.cancelled_by ?? "—"}
                            <span className="block text-xs text-muted">
                              {data(c.cancelled_at)}
                            </span>
                          </TableCell>
                          <TableCell className="text-muted">{c.reason ?? "—"}</TableCell>
                          <TableCell>
                            {c.devolucao && situacao ? (
                              <>
                                <span className="tabular-nums text-ink">
                                  {brl(c.devolucao.amount)}
                                </span>
                                <Badge tone={situacao.tone} className="ml-2">
                                  {situacao.label}
                                </Badge>
                                <span className="block text-xs text-muted">
                                  {c.devolucao.payee_name}
                                </span>
                              </>
                            ) : (
                              <span className="text-muted">nada a devolver</span>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            <Button asChild size="sm" variant="ghost">
                              <Link to={`/events/${c.id}`}>Abrir</Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </tbody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
