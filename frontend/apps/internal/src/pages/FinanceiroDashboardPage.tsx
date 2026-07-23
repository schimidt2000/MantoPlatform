import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  DenseCard,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useFinanceiroDashboard,
  type DreView,
  type EventoStatus,
  type PeriodFilter,
} from "../lib/financeiro";

const PERIOD_OPTIONS: { value: PeriodFilter; label: string }[] = [
  { value: "este_mes", label: "Este mês" },
  { value: "30d", label: "Últimos 30 dias" },
  { value: "mes_anterior", label: "Mês anterior" },
  { value: "custom", label: "Personalizado" },
];

const DRE_ROWS: { key: keyof DreView; label: string; pct?: keyof DreView }[] = [
  { key: "receita_bruta", label: "Receita bruta" },
  { key: "impostos", label: "Impostos" },
  { key: "receita_liquida", label: "Receita líquida" },
  { key: "cpv", label: "CPV (custo de talentos)" },
  { key: "lucro_bruto", label: "Lucro bruto", pct: "margem_bruta" },
  { key: "marketing", label: "Marketing (permutas)" },
  { key: "comissoes", label: "Comissões" },
  { key: "pessoal", label: "Pessoal" },
  { key: "ebitda", label: "EBITDA", pct: "margem_ebitda" },
  { key: "gastos_extras", label: "Gastos extras" },
  { key: "gastos_recorrentes", label: "Gastos recorrentes" },
  { key: "resultado_liquido", label: "Resultado líquido" },
];

const STATUS_LABEL: Record<EventoStatus, string> = {
  permuta: "Permuta",
  sem_valor: "Sem valor",
  pago_total: "Pago",
  parcial: "Parcial",
  pendente: "Pendente",
};

const STATUS_CLASS: Record<EventoStatus, string> = {
  permuta: "bg-surface-2 text-muted",
  sem_valor: "bg-surface-2 text-muted",
  pago_total: "bg-green-soft text-green",
  parcial: "bg-blue-soft text-blue",
  pendente: "bg-red-soft text-red",
};

function brl(v: number | null | undefined): string {
  if (!v) return "—";
  return `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function DreTable({ dre }: { dre: { realizado: DreView; projetado: DreView; total: DreView } }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
            <th className="px-3 py-2">Componente</th>
            <th className="px-3 py-2 text-right">Realizado</th>
            <th className="px-3 py-2 text-right">Projetado</th>
            <th className="px-3 py-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {DRE_ROWS.map((row) => (
            <tr key={row.key} className="border-b border-line last:border-0">
              <td className="px-3 py-2 text-ink">{row.label}</td>
              {(["realizado", "projetado", "total"] as const).map((view) => {
                const value = dre[view][row.key] as number;
                const pct = row.pct ? (dre[view][row.pct] as number) : null;
                return (
                  <td
                    key={view}
                    className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
                      value < 0 ? "text-red" : "text-ink"
                    }`}
                  >
                    {brl(value)}
                    {pct != null && <span className="ml-1 text-xs text-muted">({pct}%)</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <DenseCard stats={[{ label, value }]}>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </DenseCard>
  );
}

export function FinanceiroDashboardPage() {
  const [period, setPeriod] = useState<PeriodFilter>("este_mes");
  const [startDraft, setStartDraft] = useState("");
  const [endDraft, setEndDraft] = useState("");
  const [appliedRange, setAppliedRange] = useState<{ start: string; end: string } | null>(null);

  const query = useFinanceiroDashboard({
    period,
    start: appliedRange?.start,
    end: appliedRange?.end,
  });

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader title="Dashboard financeiro" className="mb-0" />

      <div className="flex flex-wrap items-center gap-2">
        {PERIOD_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            size="sm"
            variant={period === opt.value ? "default" : "outline"}
            onClick={() => {
              setPeriod(opt.value);
              if (opt.value !== "custom") setAppliedRange(null);
            }}
          >
            {opt.label}
          </Button>
        ))}
        {period === "custom" && (
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="date"
              value={startDraft}
              onChange={(e) => setStartDraft(e.target.value)}
              className="h-9 w-40"
            />
            <span className="text-sm text-muted">até</span>
            <Input
              type="date"
              value={endDraft}
              onChange={(e) => setEndDraft(e.target.value)}
              className="h-9 w-40"
            />
            <Button
              size="sm"
              variant="outline"
              disabled={!startDraft || !endDraft}
              onClick={() => setAppliedRange({ start: startDraft, end: endDraft })}
            >
              Aplicar
            </Button>
          </div>
        )}
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <div className="grid gap-4 sm:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o dashboard financeiro.
        </div>
      )}

      {query.data && (
        <>
          <p className="text-sm text-muted">
            {query.data.period_label} ({formatDate(query.data.start)} – {formatDate(query.data.end)})
          </p>

          <Card>
            <CardHeader>
              <CardTitle>DRE gerencial</CardTitle>
            </CardHeader>
            <CardContent>
              <DreTable dre={query.data.dre} />
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Ticket médio" value={brl(query.data.kpis.ticket_medio)} />
            <KpiCard
              label="Custo talento / receita"
              value={`${query.data.kpis.ratio_custo_talento}%`}
            />
            <KpiCard
              label="Break-even"
              value={`${query.data.kpis.breakeven_pct}%`}
              sub={query.data.kpis.breakeven_atingido ? "Atingido" : "Não atingido"}
            />
            <KpiCard
              label="Fator R"
              value={`${query.data.kpis.fator_r_pct}%`}
              sub={
                query.data.kpis.fator_r_protegido
                  ? `Protegido (limite ${query.data.kpis.fator_r_threshold}%)`
                  : `Em risco (limite ${query.data.kpis.fator_r_threshold}%)`
              }
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <KpiCard label="A receber de clientes" value={brl(query.data.paineis.a_receber_clientes)} />
            <KpiCard label="Cachês pendentes" value={brl(query.data.paineis.pagamentos_pendentes)} />
            <KpiCard label="Cachês pagos" value={brl(query.data.paineis.pagamentos_realizados)} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Receita por tipo de evento</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {Object.keys(query.data.paineis.receita_por_tipo).length === 0 ? (
                  <p className="text-sm text-muted">Sem receita no período.</p>
                ) : (
                  Object.entries(query.data.paineis.receita_por_tipo).map(([tipo, valor]) => (
                    <div key={tipo}>
                      <div className="flex justify-between text-sm text-ink">
                        <span>{tipo}</span>
                        <span className="tabular-nums">{brl(valor)}</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-surface-2">
                        <div
                          className="h-1.5 rounded-full bg-accent"
                          style={{
                            width: `${
                              query.data.paineis.receita_tipo_max
                                ? (valor / query.data.paineis.receita_tipo_max) * 100
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Top vendedores</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {query.data.paineis.top_sellers.length === 0 ? (
                  <p className="text-sm text-muted">Sem vendas no período.</p>
                ) : (
                  query.data.paineis.top_sellers.map((s) => (
                    <div key={s.user_id} className="flex justify-between text-sm text-ink">
                      <span>{s.user_name}</span>
                      <span className="tabular-nums">
                        {brl(s.receita)} <span className="text-muted">({brl(s.lucro)} lucro)</span>
                      </span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tendência (6 meses)</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto p-0">
                <table className="w-full min-w-[420px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                      <th className="px-3 py-2">Mês</th>
                      <th className="px-3 py-2 text-right">Receita</th>
                      <th className="px-3 py-2 text-right">Custo</th>
                      <th className="px-3 py-2 text-right">Lucro</th>
                      <th className="px-3 py-2 text-right">Margem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.paineis.monthly_trend.map((m) => (
                      <tr key={m.label} className="border-b border-line last:border-0">
                        <td className="px-3 py-2 text-ink">{m.label}</td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                          {brl(m.receita)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                          {brl(m.custo)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                          {brl(m.lucro)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted">
                          {m.margem}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Auditoria — eventos sem receita</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {query.data.paineis.auditoria.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma pendência.</p>
                ) : (
                  query.data.paineis.auditoria.map((a) => (
                    <div key={a.event_id} className="flex justify-between text-sm">
                      <Link to={`/events/${a.event_id}`} className="text-blue hover:underline">
                        {a.title}
                      </Link>
                      <span className="text-muted">{formatDate(a.start_at)}</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Eventos do período</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              {query.data.eventos.length === 0 ? (
                <p className="p-6 text-center text-sm text-muted">Nenhum evento no período.</p>
              ) : (
                <table className="w-full min-w-[760px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                      <th className="px-3 py-2">Evento</th>
                      <th className="px-3 py-2">Data</th>
                      <th className="px-3 py-2 text-right">Custo</th>
                      <th className="px-3 py-2 text-right">Lucro</th>
                      <th className="px-3 py-2 text-right">Comissão</th>
                      <th className="px-3 py-2 text-right">Taxa</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.eventos.map((e) => (
                      <tr key={e.event_id} className="border-b border-line last:border-0">
                        <td className="px-3 py-2 text-ink">
                          {e.group_label ?? e.title}
                          {e.group_label && (
                            <span className="ml-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                              grupo
                            </span>
                          )}
                          {e.is_projetado && (
                            <span className="ml-1 rounded-md bg-blue-soft px-1.5 py-0.5 text-xs text-blue">
                              projetado
                            </span>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDate(e.start_at)}</td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                          {brl(e.custo)}
                        </td>
                        <td
                          className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
                            e.lucro < 0 ? "text-red" : "text-ink"
                          }`}
                        >
                          {brl(e.lucro)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                          {brl(e.comissao)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted">
                          {e.rate}%
                        </td>
                        <td className="whitespace-nowrap px-3 py-2">
                          <span
                            className={`rounded-md px-1.5 py-0.5 text-xs ${STATUS_CLASS[e.status]}`}
                          >
                            {STATUS_LABEL[e.status]}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right">
                          <Link to={`/events/${e.event_id}`} className="text-sm text-blue hover:underline">
                            Ver
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>
                  Recebimentos previstos ({brl(query.data.pendencias.recebimentos_previstos_total)})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {query.data.pendencias.recebimentos_previstos.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma parcela a vencer no período.</p>
                ) : (
                  query.data.pendencias.recebimentos_previstos.map((r, idx) => (
                    <div key={`${r.event_id}-${idx}`} className="flex justify-between text-sm">
                      <Link to={`/events/${r.event_id}`} className="text-blue hover:underline">
                        {r.event_title}
                      </Link>
                      <span className="tabular-nums text-ink">
                        {formatDate(r.date)} · {brl(r.amount)}
                      </span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>
                  Notas fiscais a emitir ({brl(query.data.pendencias.nf_a_emitir_total)})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {query.data.pendencias.nf_a_emitir.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma nota pendente de emissão.</p>
                ) : (
                  query.data.pendencias.nf_a_emitir.map((nf) => (
                    <div key={nf.id} className="flex justify-between text-sm">
                      <Link to={`/events/${nf.event_id}`} className="text-blue hover:underline">
                        {nf.event_title}
                      </Link>
                      <span className="tabular-nums text-ink">{brl(nf.amount)}</span>
                    </div>
                  ))
                )}
                <p className="pt-2 text-xs text-muted">
                  Custo de notas emitidas no período: {brl(query.data.pendencias.custo_nota_total)}
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
