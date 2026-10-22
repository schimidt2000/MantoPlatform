import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
import { useCancelamentos, type EventoCancelado, type FiltroDevolucao } from "../lib/eventOps";
import { INPUT_CLASS } from "../components/EventDetail/parts";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** `dd/mm/aaaa` sem passar por `new Date()` — data pura não pode escorregar de fuso. */
function data(iso: string | null): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : iso;
}

/** `dd/mm` de uma data `AAAA-MM-DD…`. */
function diaMes(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes ? `${dia}/${mes}` : iso;
}

const STATUS_DEVOLUCAO: Record<string, { label: string; tone: "green" | "gold" | "blue" }> = {
  pago: { label: "devolvida", tone: "green" },
  no_banco: { label: "no banco", tone: "blue" },
  nao_pago: { label: "a devolver", tone: "gold" },
};

const OPCOES_DEVOLUCAO: { valor: FiltroDevolucao | ""; rotulo: string }[] = [
  { valor: "", rotulo: "Todas as devoluções" },
  { valor: "nao_pago", rotulo: "A devolver" },
  { valor: "no_banco", rotulo: "No banco" },
  { valor: "pago", rotulo: "Devolvida" },
  { valor: "sem", rotulo: "Sem devolução" },
];

const MES_VALIDO = /^\d{4}-(0[1-9]|1[0-2])$/;
const DEVOLUCOES_VALIDAS = new Set<string>(["nao_pago", "no_banco", "pago", "sem"]);

/** Sem acento e em minúsculas, para a busca casar "Timão" com "timao". */
function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** A célula das devoluções: uma linha por devolução, com o estado e o destinatário. */
function Devolucoes({ c }: { c: EventoCancelado }) {
  const r = c.resumo;
  if (!r) return <span className="text-muted">—</span>;
  if (r.regime === "satelite") {
    // Converge (T111, 306): o dinheiro do "todos" está no 1º dia; repetir aqui contava N vezes.
    return (
      <span className="text-xs text-muted">
        dinheiro no 1º dia do grupo
        {r.principal && (
          <>
            {": "}
            <Link to={`/events/${r.principal.id}`} className="text-blue underline">
              {r.principal.titulo}
            </Link>
          </>
        )}
      </span>
    );
  }
  if (r.devolucoes.length === 0) return <span className="text-muted">sem devolução</span>;
  return (
    <>
      {r.devolucoes.map((d) => {
        const estado = STATUS_DEVOLUCAO[d.estado] ?? STATUS_DEVOLUCAO.nao_pago;
        return (
          <span key={d.id} className="block">
            <span className="tabular-nums text-ink">{brl(d.valor)}</span>
            <Badge tone={estado.tone} className="ml-2">
              {estado.label}
            </Badge>
            <span className="block text-xs text-muted">
              {d.nome ?? "—"}
              {d.pix ? ` · PIX ${d.pix}` : ""}
            </span>
          </span>
        );
      })}
    </>
  );
}

/**
 * A página de Cancelamentos (features 224, 306 e 312): pedidos de exclusão do Comercial aguardando
 * decisão e os eventos cancelados com o dinheiro de cada um. É "a parte específica do sistema" da
 * resposta do dono (Q4): o cancelado sai da agenda, da busca e das listas, e aqui se filtra e se vê o
 * que houve. Abre para Superadmin e Financeiro. Filtros na URL (o card do período chega com `?mes=`).
 */
export function EventosCancelamentosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const mesUrl = searchParams.get("mes") ?? "";
  const devUrl = searchParams.get("devolucao") ?? "";
  const mes = MES_VALIDO.test(mesUrl) ? mesUrl : null;
  const devolucao = DEVOLUCOES_VALIDAS.has(devUrl) ? (devUrl as FiltroDevolucao) : null;
  const [busca, setBusca] = useState("");
  // O rascunho do mês: no Firefox e no Safari de desktop o `type="month"` é um campo de texto, e
  // gravar na URL a cada tecla ("2", "20"…) fazia o efeito abaixo apagar o que se digitava.
  const [mesRascunho, setMesRascunho] = useState(mes ?? "");
  useEffect(() => setMesRascunho(mes ?? ""), [mes]);

  // Valor inválido digitado na URL volta ao padrão em vez de virar erro.
  useEffect(() => {
    if ((mesUrl && !mes) || (devUrl && !devolucao)) {
      const proximo = new URLSearchParams(searchParams);
      if (mesUrl && !mes) proximo.delete("mes");
      if (devUrl && !devolucao) proximo.delete("devolucao");
      setSearchParams(proximo, { replace: true });
    }
  }, [mesUrl, devUrl, mes, devolucao, searchParams, setSearchParams]);

  const query = useCancelamentos({ mes, devolucao });
  const pendentes = query.data?.pendentes ?? [];
  const todos = query.data?.cancelados ?? [];
  const cancelados = useMemo(() => {
    const termo = normalizar(busca.trim());
    if (!termo) return todos;
    return todos.filter((c) => normalizar(`${c.title} ${c.reason ?? ""}`).includes(termo));
  }, [todos, busca]);
  const comFiltro = Boolean(mes || devolucao || busca.trim());

  function filtrar(chave: "mes" | "devolucao", valor: string) {
    const proximo = new URLSearchParams(searchParams);
    if (valor) proximo.set(chave, valor);
    else proximo.delete(chave);
    setSearchParams(proximo, { replace: true });
  }

  function limpar() {
    setBusca("");
    setSearchParams(new URLSearchParams(), { replace: true });
  }

  const totalRetido = query.data?.total_retido;
  const escopo = query.data?.total_retido_escopo;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Exclusões e cancelamentos"
        subtitle="Pedidos do Comercial e eventos cancelados, com a devolução e o retido de cada um"
        className="mb-0"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/agenda">← Agenda</Link>
          </Button>
        }
      />

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          {query.error?.message || "Não foi possível carregar a lista."}
        </div>
      )}

      {query.data && (
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
      )}

      {/* Converge (312): os filtros ficam de pé com erro e durante a troca — é por eles que se sai. */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <CardTitle>Eventos cancelados</CardTitle>
            {totalRetido !== undefined && (
              <span className="text-sm text-muted">
                Retido:{" "}
                <span className="tabular-nums font-medium text-ink">{brl(totalRetido)}</span>
                {escopo === "listados" ? ` nos ${todos.length} listados` : " no mês"}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="text-xs text-muted">
              Mês do cancelamento
              <input
                type="month"
                className={`${INPUT_CLASS} mt-1 block w-44`}
                value={mesRascunho}
                placeholder="AAAA-MM"
                onChange={(e) => {
                  const valor = e.target.value;
                  setMesRascunho(valor);
                  if (!valor || MES_VALIDO.test(valor)) filtrar("mes", valor);
                }}
                aria-label="Mês do cancelamento"
              />
            </label>
            <label className="text-xs text-muted">
              Devolução
              <select
                className={`${INPUT_CLASS} mt-1 block w-48`}
                value={devolucao ?? ""}
                onChange={(e) => filtrar("devolucao", e.target.value)}
                aria-label="Situação da devolução"
              >
                {OPCOES_DEVOLUCAO.map((o) => (
                  <option key={o.valor} value={o.valor}>
                    {o.rotulo}
                  </option>
                ))}
              </select>
            </label>
            <label className="min-w-0 flex-1 text-xs text-muted">
              Buscar
              <input
                type="search"
                className={`${INPUT_CLASS} mt-1 block w-full`}
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Título do evento ou motivo"
                aria-label="Buscar por título ou motivo"
              />
            </label>
            {comFiltro && (
              <Button variant="ghost" size="sm" onClick={limpar}>
                Limpar filtros
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {!query.data ? (
            query.isError ? null : <Skeleton className="m-4 h-40" />
          ) : cancelados.length === 0 ? (
            <div className="flex flex-wrap items-center gap-2 p-4 text-sm text-muted">
              {comFiltro ? "Nenhum cancelamento com estes filtros." : "Nenhum evento cancelado."}
              {comFiltro && (
                <Button variant="outline" size="sm" onClick={limpar}>
                  Limpar filtros
                </Button>
              )}
            </div>
          ) : (
            <Table className="min-w-[1100px]">
              <thead>
                <TableRow head>
                  <TableCell as="th">Evento</TableCell>
                  <TableCell as="th">Data do evento</TableCell>
                  <TableCell as="th">Cancelado em</TableCell>
                  <TableCell as="th" align="right">
                    Venda
                  </TableCell>
                  <TableCell as="th" align="right">
                    Pago
                  </TableCell>
                  <TableCell as="th">Devoluções</TableCell>
                  <TableCell as="th" align="right">
                    Retido
                  </TableCell>
                  <TableCell as="th" align="right">
                    Comissão
                  </TableCell>
                  <TableCell as="th" align="right">
                    BV
                  </TableCell>
                  <TableCell as="th" align="right">
                    Imposto
                  </TableCell>
                  <TableCell as="th" align="right">
                    <span className="sr-only">Ações</span>
                  </TableCell>
                </TableRow>
              </thead>
              <tbody>
                {cancelados.map((c) => {
                  const r = c.resumo;
                  const semVendaPropria = r?.regime === "satelite" || r?.regime === "dia";
                  const bv = (r?.bvs ?? []).reduce((soma, b) => soma + (b.conta ?? 0), 0);
                  return (
                    <TableRow key={c.id}>
                      <TableCell className="text-ink">
                        {c.title}
                        {r?.regime === "dia" && (
                          <span className="block text-xs text-muted">
                            dia cortado da venda de{" "}
                            {r.principal ? (
                              <Link to={`/events/${r.principal.id}`} className="text-blue underline">
                                {diaMes(r.principal.data)}
                              </Link>
                            ) : (
                              diaMes(undefined)
                            )}
                          </span>
                        )}
                        {r?.venda_passou_para && (
                          <span className="block text-xs text-muted">
                            a venda passou para {diaMes(r.venda_passou_para.data)}
                          </span>
                        )}
                        {c.reason && <span className="block text-xs text-muted">{c.reason}</span>}
                      </TableCell>
                      <TableCell className="tabular-nums">{data(c.start_at)}</TableCell>
                      <TableCell>
                        <span className="tabular-nums">{data(c.cancelled_at)}</span>
                        {c.cancelled_by && (
                          <span className="block text-xs text-muted">por {c.cancelled_by}</span>
                        )}
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {/* O satélite e o dia cortado não têm venda própria: ela mora no 1º dia. */}
                        {semVendaPropria ? <span className="text-muted">no 1º dia</span> : brl(c.sale_value)}
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {/* No dia cortado o pago é o do grupo (o dinheiro mora no 1º dia, como na 306). */}
                        {!r || r.regime === "satelite" ? (
                          "—"
                        ) : r.regime === "dia" ? (
                          <span className="text-xs text-muted">
                            pago no grupo {brl(r.pago)}
                            {r.principal && (
                              <>
                                {" · venda no "}
                                <Link to={`/events/${r.principal.id}`} className="text-blue underline">
                                  1º dia
                                </Link>
                              </>
                            )}
                          </span>
                        ) : (
                          brl(r.pago)
                        )}
                      </TableCell>
                      <TableCell>
                        <Devolucoes c={c} />
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {r ? brl(r.retido) : "—"}
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {r?.comissao ? brl(r.comissao.retido) : "—"}
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {r?.bvs ? brl(bv) : "—"}
                      </TableCell>
                      <TableCell align="right" className="tabular-nums">
                        {r?.imposto != null ? brl(r.imposto) : "—"}
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
    </div>
  );
}
