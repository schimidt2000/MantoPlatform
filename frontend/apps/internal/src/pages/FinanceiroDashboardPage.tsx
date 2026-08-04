import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useFinanceiroDashboard,
  type DreView,
  type EventoStatus,
  type FinanceiroDashboard,
  type PeriodFilter,
} from "../lib/financeiro";

const PERIOD_OPTIONS: { value: PeriodFilter; label: string }[] = [
  { value: "este_mes", label: "Este mês" },
  { value: "30d", label: "Últimos 30 dias" },
  { value: "mes_anterior", label: "Mês anterior" },
  { value: "custom", label: "Personalizado" },
];

/** Papel de cada linha na cascata da DRE — define recuo, peso e cor (feature 189). */
type DreRowKind = "base" | "deducao" | "subtotal" | "final";

interface DreRowSpec {
  key: keyof DreView;
  label: string;
  /** Detalhe entre parênteses, em texto menor (ex.: "eventos com nota"). */
  hint?: string;
  kind: DreRowKind;
  /** Campo de margem exibido ao lado do valor (ex.: `margem_bruta`). */
  pct?: keyof DreView;
}

function dreRows(taxRate: number): DreRowSpec[] {
  return [
    { key: "receita_bruta", label: "Receita Bruta", kind: "base" },
    {
      key: "impostos",
      label: "Impostos Provisionados",
      hint: `${taxRate}% · eventos com nota`,
      kind: "deducao",
    },
    { key: "receita_liquida", label: "Receita Líquida Operacional", kind: "subtotal" },
    { key: "cpv", label: "CPV", hint: "cachês — eventos normais", kind: "deducao" },
    { key: "lucro_bruto", label: "Lucro Bruto", kind: "subtotal", pct: "margem_bruta" },
    { key: "marketing", label: "Custos de Marketing", hint: "permutas/cortesias", kind: "deducao" },
    { key: "comissoes", label: "Comissões de Vendas", kind: "deducao" },
    { key: "pessoal", label: "Custos de Pessoal", hint: "salários", kind: "deducao" },
    {
      key: "ebitda",
      label: "EBITDA / Resultado Operacional",
      kind: "subtotal",
      pct: "margem_ebitda",
    },
    { key: "gastos_extras", label: "Gastos Extras", hint: "aprovados", kind: "deducao" },
    { key: "gastos_recorrentes", label: "Gastos Recorrentes", hint: "contas do mês", kind: "deducao" },
    { key: "resultado_liquido", label: "Resultado Líquido", kind: "final" },
  ];
}

const STATUS_LABEL: Record<EventoStatus, string> = {
  permuta: "Permuta/Cortesia",
  sem_valor: "Sem valor",
  pago_total: "Pago total",
  parcial: "Parcial",
  pendente: "Pendente",
};

const STATUS_CLASS: Record<EventoStatus, string> = {
  permuta: "bg-accent-soft text-accent",
  sem_valor: "bg-surface-2 text-muted",
  pago_total: "bg-green-soft text-green",
  parcial: "bg-gold-soft text-gold",
  pendente: "bg-red-soft text-red",
};

/** Formata em BRL sempre com prefixo (Princípio VII) — 0 vira "R$ 0,00", não travessão. */
function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

/** Faixa de cor por percentual: verde acima de `good`, âmbar acima de `warn`, vermelho abaixo. */
function pctTone(value: number, good: number, warn: number, inverted = false): string {
  const isGood = inverted ? value <= good : value >= good;
  const isWarn = inverted ? value <= warn : value >= warn;
  if (isGood) return "text-green";
  if (isWarn) return "text-gold";
  return "text-red";
}

interface KpiCardProps {
  label: string;
  value: string;
  sub: string;
  tone?: string;
}

function KpiCard({ label, value, sub, tone = "text-ink" }: KpiCardProps) {
  return (
    <Card className="p-4">
      <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-extrabold tabular-nums ${tone}`}>{value}</p>
      <p className="mt-0.5 text-[11px] text-muted">{sub}</p>
    </Card>
  );
}

/** Barra de progresso do design system (Tailwind puro) — usada no break-even e no Fator R. */
function ProgressBar({ pct, tone, label }: { pct: number; tone: string; label: string }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div
      className="h-3 w-full overflow-hidden rounded-full bg-surface-2"
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={`h-full rounded-full transition-[width] duration-300 ${tone}`}
        style={{ width: `${clamped}%`, minWidth: clamped > 0 ? "2px" : undefined }}
      />
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-xs font-bold uppercase tracking-wide text-muted">{children}</h3>
  );
}

function DreTable({ dre, taxRate }: { dre: FinanceiroDashboard["dre"]; taxRate: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-[13px]">
        <thead>
          <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="px-3 py-2">Linha</th>
            <th className="px-3 py-2 text-right">Realizado</th>
            <th className="px-3 py-2 text-right">Projetado</th>
            <th className="px-3 py-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {dreRows(taxRate).map((row) => {
            const isDeducao = row.kind === "deducao";
            const isSubtotal = row.kind === "subtotal" || row.kind === "final";
            return (
              <tr
                key={row.key}
                className={[
                  "border-b border-line last:border-0",
                  isSubtotal ? "bg-surface font-bold" : "",
                  row.kind === "final" ? "border-t-2 border-t-line text-sm" : "",
                  row.key === "ebitda" ? "border-t-2 border-t-line" : "",
                ].join(" ")}
              >
                <td className={`px-3 py-2 text-ink ${isDeducao ? "pl-7" : ""}`}>
                  {isDeducao && <span className="mr-1 font-bold text-muted">(–)</span>}
                  {isSubtotal && <span className="mr-1 text-muted">=</span>}
                  {row.label}
                  {row.hint && <span className="ml-1 text-[11px] font-normal text-muted">({row.hint})</span>}
                </td>
                {(["realizado", "projetado", "total"] as const).map((view) => {
                  const value = dre[view][row.key] as number;
                  const pct = row.pct ? (dre[view][row.pct] as number) : null;
                  const negative = isDeducao || value < 0;
                  const tone = view === "projetado" ? "text-muted" : negative ? "text-red" : "text-ink";
                  return (
                    <td
                      key={view}
                      className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${tone} ${
                        view === "total" ? "font-bold" : ""
                      }`}
                    >
                      {isDeducao && "– "}
                      {brl(value)}
                      {pct != null && (
                        <span className="ml-1 text-[10px] font-semibold text-muted">{pct}%</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function FinanceiroDashboardPage() {
  const [period, setPeriod] = useState<PeriodFilter>("este_mes");
  const [startDraft, setStartDraft] = useState("");
  const [endDraft, setEndDraft] = useState("");
  const [appliedRange, setAppliedRange] = useState<{ start: string; end: string } | null>(null);
  // Opt-in explícito da Loja Virtual nos indicadores de evento (feature 205, FR-055). Começa
  // desligado: a receita da loja já está no DRE, e o ticket médio de evento presencial é o
  // número que a operação usa para precificar show.
  const [incluirLojaVirtual, setIncluirLojaVirtual] = useState(false);

  const query = useFinanceiroDashboard({
    period,
    start: appliedRange?.start,
    end: appliedRange?.end,
    incluirLojaVirtual,
  });

  const data = query.data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Painel Financeiro"
        subtitle="Resultado mês a mês — regime de competência (data do evento)"
        className="mb-0"
      />

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
              aria-label="Data inicial"
            />
            <span className="text-sm text-muted">até</span>
            <Input
              type="date"
              value={endDraft}
              onChange={(e) => setEndDraft(e.target.value)}
              className="h-9 w-40"
              aria-label="Data final"
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
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <div className="grid gap-3 sm:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o dashboard financeiro.
        </div>
      )}

      {data && (
        <>
          <p className="text-sm text-muted">
            {data.period_label} ({formatDate(data.start)} – {formatDate(data.end)})
          </p>

          <div className="grid items-start gap-4 lg:grid-cols-3">
            {/* ══ COLUNA PRINCIPAL (2/3) — KPIs, termômetros e DRE ══ */}
            <div className="space-y-4 lg:col-span-2">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <KpiCard
                  label="Ticket Médio"
                  value={brl(data.kpis.ticket_medio)}
                  sub="por evento com venda"
                />
                <KpiCard
                  label="Custo Talento / Receita"
                  value={`${data.kpis.ratio_custo_talento}%`}
                  sub="CPV ÷ receita líquida"
                  tone={pctTone(data.kpis.ratio_custo_talento, 45, 60, true)}
                />
                <KpiCard
                  label="Margem Bruta"
                  value={`${data.kpis.margem_bruta}%`}
                  sub="lucro bruto ÷ receita líquida"
                  tone={pctTone(data.kpis.margem_bruta, 40, 20)}
                />
                <KpiCard
                  label="Margem Operacional (EBITDA)"
                  value={`${data.kpis.margem_ebitda}%`}
                  sub="após pessoal e comissões"
                  tone={pctTone(data.kpis.margem_ebitda, 20, 5)}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {/* Termômetro de break-even */}
                <Card className="p-4">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-muted">
                    Termômetro de Break-even
                  </p>
                  <div className="mt-2 flex items-center gap-3">
                    <ProgressBar
                      pct={data.kpis.breakeven_pct}
                      tone={data.kpis.breakeven_atingido ? "bg-green" : "bg-gold"}
                      label="Cobertura do custo fixo"
                    />
                    <span
                      className={`min-w-[3.5rem] text-right text-lg font-extrabold tabular-nums ${
                        data.kpis.breakeven_atingido ? "text-green" : "text-gold"
                      }`}
                    >
                      {data.kpis.breakeven_pct}%
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] text-muted">
                    {data.kpis.breakeven_atingido
                      ? "Custo fixo coberto ✓"
                      : "Margem cobrindo custo fixo (pessoal + comissões)"}{" "}
                    · meta {brl(data.kpis.fixed_cost)}
                  </p>
                </Card>

                {/* Alerta fiscal — Fator R */}
                <Card
                  className={`p-4 ${
                    data.kpis.fator_r_protegido ? "border-green/40 bg-green-soft/40" : "border-gold/40 bg-gold-soft"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-muted">
                      Alerta Fiscal — Fator R
                    </p>
                    <span
                      className={`shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
                        data.kpis.fator_r_protegido
                          ? "bg-green-soft text-green"
                          : "bg-red-soft text-red"
                      }`}
                    >
                      {data.kpis.fator_r_protegido ? "🛡️ Protegido" : "⚠️ Em risco"}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <ProgressBar
                      pct={
                        data.kpis.fator_r_threshold > 0
                          ? (data.kpis.fator_r_pct / data.kpis.fator_r_threshold) * 100
                          : 0
                      }
                      tone={data.kpis.fator_r_protegido ? "bg-green" : "bg-gold"}
                      label="Folha sobre faturamento acumulado"
                    />
                    <span
                      className={`min-w-[3.5rem] text-right text-lg font-extrabold tabular-nums ${
                        data.kpis.fator_r_protegido ? "text-green" : "text-red"
                      }`}
                    >
                      {data.kpis.fator_r_pct}%
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] text-muted">
                    {data.kpis.fator_r_protegido
                      ? `Imposto protegido (~${data.kpis.fator_r_rate_low}%) — folha ≥ ${data.kpis.fator_r_threshold}% do faturamento`
                      : `Risco de alíquota (~${data.kpis.fator_r_rate_high}%) — folha abaixo de ${data.kpis.fator_r_threshold}%`}
                  </p>
                </Card>
              </div>

              <Card>
                <CardHeader className="flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base">📊 DRE Gerencial</CardTitle>
                  <span className="text-[11px] text-muted">Realizado · Projetado · Total</span>
                </CardHeader>
                <CardContent className="p-0">
                  <DreTable dre={data.dre} taxRate={data.kpis.tax_rate} />
                  <p className="px-4 py-3 text-[11px] leading-relaxed text-muted">
                    Projetado = contribuição operacional dos {data.dre.projetado.n_eventos} evento(s)
                    futuro(s), sem custo fixo. Custos fixos (pessoal, gastos extras e recorrentes) são
                    atribuídos ao Realizado.
                  </p>
                </CardContent>
              </Card>

              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard
                  label="A Receber — Clientes"
                  value={brl(data.paineis.a_receber_clientes)}
                  sub="venda − comprovantes"
                  tone={data.paineis.a_receber_clientes > 0 ? "text-red" : "text-green"}
                />
                <KpiCard
                  label="A Pagar — Talentos"
                  value={brl(data.paineis.pagamentos_pendentes)}
                  sub="cachês não pagos no período"
                  tone={data.paineis.pagamentos_pendentes > 0 ? "text-red" : "text-green"}
                />
                <KpiCard
                  label="Pago — Talentos"
                  value={brl(data.paineis.pagamentos_realizados)}
                  sub="cachês pagos/no banco"
                  tone="text-green"
                />
              </div>
            </div>

            {/* ══ COLUNA ANALÍTICA (1/3) ══ */}
            <div className="space-y-4">
              <Card className="p-4">
                <SectionTitle>🎭 Receita por Tipo de Evento</SectionTitle>
                <div className="mt-3 space-y-2.5">
                  {Object.keys(data.paineis.receita_por_tipo).length === 0 ? (
                    <p className="text-sm text-muted">Sem receita no período.</p>
                  ) : (
                    Object.entries(data.paineis.receita_por_tipo).map(([tipo, valor]) => (
                      <div key={tipo} className="flex items-center gap-2 text-xs">
                        <span className="w-16 shrink-0 truncate text-right text-[11px] text-muted">
                          {tipo}
                        </span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                          <div
                            className="h-full rounded-full bg-accent"
                            style={{
                              width: `${
                                data.paineis.receita_tipo_max
                                  ? (valor / data.paineis.receita_tipo_max) * 100
                                  : 0
                              }%`,
                            }}
                          />
                        </div>
                        <span className="w-24 shrink-0 text-right tabular-nums text-ink">
                          {brl(valor)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </Card>

              {data.paineis.loja_virtual.vendas > 0 && (
                <Card className="p-4">
                  <SectionTitle>🎥 Loja de Interações Virtuais</SectionTitle>
                  <p className="mt-1 text-[11px] leading-snug text-muted">
                    Canal self-service, sem vendedor. A receita já está somada no resultado
                    acima; os indicadores de evento (ticket médio, a receber) contam só evento
                    presencial.
                  </p>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-lg font-semibold tabular-nums text-ink">
                        {data.paineis.loja_virtual.vendas}
                      </p>
                      <p className="text-[11px] text-muted">vendas</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold tabular-nums text-ink">
                        {brl(data.paineis.loja_virtual.receita)}
                      </p>
                      <p className="text-[11px] text-muted">receita</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold tabular-nums text-ink">
                        {brl(data.paineis.loja_virtual.ticket_medio)}
                      </p>
                      <p className="text-[11px] text-muted">ticket do canal</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant={incluirLojaVirtual ? "default" : "outline"}
                    className="mt-3 w-full"
                    onClick={() => setIncluirLojaVirtual((v) => !v)}
                    aria-pressed={incluirLojaVirtual}
                  >
                    {incluirLojaVirtual
                      ? "Voltar aos indicadores só de evento"
                      : "Incluir a loja nos indicadores de evento"}
                  </Button>
                </Card>
              )}

              <Card className="p-4">
                <SectionTitle>🏆 Top Vendedores</SectionTitle>
                <div className="mt-3">
                  {data.paineis.top_sellers.length === 0 ? (
                    <p className="text-sm text-muted">Sem vendedor no período.</p>
                  ) : (
                    data.paineis.top_sellers.map((s, idx) => (
                      <div
                        key={s.user_id}
                        className="flex items-center gap-2.5 border-b border-line py-2 text-[13px] last:border-0"
                      >
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-[11px] font-bold text-muted">
                          {idx + 1}
                        </span>
                        <span className="flex-1 truncate font-semibold text-ink">
                          {s.user_name.split(" ")[0]}
                        </span>
                        <span className="flex flex-col items-end">
                          <span className="font-bold tabular-nums text-green">{brl(s.receita)}</span>
                          <span className="text-[11px] tabular-nums text-muted">
                            lucro {brl(s.lucro)}
                          </span>
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </Card>

              <Card className={`p-4 ${data.paineis.auditoria.length > 0 ? "border-red/40" : ""}`}>
                <SectionTitle>🔍 Auditoria de Input</SectionTitle>
                <div className="mt-3 space-y-1.5">
                  {data.paineis.auditoria.length === 0 ? (
                    <p className="text-sm text-muted">
                      Tudo certo ✓ Nenhum evento com receita zerada sem justificativa.
                    </p>
                  ) : (
                    <>
                      <p className="text-xs leading-relaxed text-red">
                        {data.paineis.auditoria.length} evento(s) com receita zerada{" "}
                        <strong>sem</strong> marcação de cortesia/permuta. Provável falta de
                        preenchimento:
                      </p>
                      {data.paineis.auditoria.map((a) => (
                        <Link
                          key={a.event_id}
                          to={`/events/${a.event_id}`}
                          className="flex items-center justify-between gap-2 rounded-md bg-red-soft px-2.5 py-2 text-xs text-ink hover:bg-red-soft/70"
                        >
                          <span className="truncate font-semibold">{a.title}</span>
                          <span className="shrink-0 text-muted">{formatDate(a.start_at)}</span>
                        </Link>
                      ))}
                    </>
                  )}
                </div>
              </Card>

              <Card className="p-4">
                <SectionTitle>
                  🧾 Notas a Emitir ({data.pendencias.nf_a_emitir.length} ·{" "}
                  {brl(data.pendencias.nf_a_emitir_total)})
                </SectionTitle>
                <div className="mt-3 space-y-1.5">
                  {data.pendencias.nf_a_emitir.length === 0 ? (
                    <p className="text-sm text-muted">Nenhuma nota pendente de emissão ✓</p>
                  ) : (
                    data.pendencias.nf_a_emitir.map((nf) => (
                      <div
                        key={nf.id}
                        className="flex items-center justify-between gap-2 border-b border-line pb-1.5 text-xs last:border-0"
                      >
                        <Link
                          to={`/events/${nf.event_id}`}
                          className="truncate font-semibold text-blue hover:underline"
                        >
                          {nf.event_title}
                        </Link>
                        <span className="shrink-0 tabular-nums text-ink">
                          {nf.date ? `${formatDate(nf.date)} · ` : ""}
                          {brl(nf.amount)}
                        </span>
                      </div>
                    ))
                  )}
                  <p className="pt-1 text-[11px] text-muted">
                    Custo de notas emitidas no período: {brl(data.pendencias.custo_nota_total)}
                  </p>
                </div>
              </Card>

              <Card className="p-4">
                <SectionTitle>📅 Tendência — Últimos 6 Meses</SectionTitle>
                <div className="-mx-4 mt-3 overflow-x-auto">
                  <table className="w-full min-w-[380px] border-collapse text-xs">
                    <thead>
                      <tr className="border-b-2 border-line text-left text-[10px] font-bold uppercase tracking-wide text-muted">
                        <th className="px-3 py-1.5">Mês</th>
                        <th className="px-3 py-1.5 text-right">Receita</th>
                        <th className="px-3 py-1.5 text-right">Talentos</th>
                        <th className="px-3 py-1.5 text-right">Lucro</th>
                        <th className="px-3 py-1.5 text-right">Margem</th>
                        <th className="px-3 py-1.5 text-right">Ev.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.paineis.monthly_trend.map((m) => (
                        <tr key={m.label} className="border-b border-line last:border-0">
                          <td className="px-3 py-1.5 font-semibold text-ink">{m.label}</td>
                          <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-ink">
                            {brl(m.receita)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-red">
                            {brl(m.custo)}
                          </td>
                          <td
                            className={`whitespace-nowrap px-3 py-1.5 text-right tabular-nums ${
                              m.lucro >= 0 ? "text-green" : "text-red"
                            }`}
                          >
                            {brl(m.lucro)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-1.5 text-right">
                            <span
                              className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
                                m.margem >= 40
                                  ? "bg-green-soft text-green"
                                  : m.margem >= 20
                                    ? "bg-gold-soft text-gold"
                                    : "bg-red-soft text-red"
                              }`}
                            >
                              {m.margem}%
                            </span>
                          </td>
                          <td className="px-3 py-1.5 text-right tabular-nums text-muted">
                            {m.n_eventos}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card className="p-4">
                <SectionTitle>
                  📥 Recebimentos Previstos ({brl(data.pendencias.recebimentos_previstos_total)})
                </SectionTitle>
                <div className="mt-3 space-y-1.5">
                  {data.pendencias.recebimentos_previstos.length === 0 ? (
                    <p className="text-sm text-muted">Nenhuma parcela prevista no período.</p>
                  ) : (
                    data.pendencias.recebimentos_previstos.map((r, idx) => (
                      <div
                        key={`${r.event_id}-${idx}`}
                        className="flex items-center justify-between gap-2 border-b border-line pb-1.5 text-xs last:border-0"
                      >
                        <Link
                          to={`/events/${r.event_id}`}
                          className="truncate font-semibold text-blue hover:underline"
                        >
                          {r.event_title}
                        </Link>
                        <span className="shrink-0 tabular-nums text-ink">
                          {formatDate(r.date)} · {brl(r.amount)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          </div>

          {/* ══ EVENTOS DO PERÍODO (largura total) ══ */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">📋 Eventos no Período</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data.eventos.length === 0 ? (
                <p className="p-6 text-center text-sm text-muted">
                  Nenhum evento no período selecionado.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[860px] border-collapse text-[13px]">
                    <thead>
                      <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
                        <th className="px-3 py-2">Data</th>
                        <th className="px-3 py-2">Evento</th>
                        <th className="px-3 py-2">Tipo</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2 text-right">Receita</th>
                        <th className="px-3 py-2 text-right">Custo</th>
                        <th className="px-3 py-2 text-right">Lucro</th>
                        <th className="px-3 py-2 text-right">Comissão</th>
                        <th className="px-3 py-2 text-right">Taxa</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.eventos.map((e) => (
                        <tr key={e.event_id} className="border-b border-line last:border-0">
                          <td className="whitespace-nowrap px-3 py-2 text-muted">
                            {formatDate(e.start_at)}
                            {e.is_projetado && (
                              <span className="ml-1 rounded-md bg-blue-soft px-1.5 py-0.5 text-[10px] font-bold text-blue">
                                Projetado
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <Link
                              to={`/events/${e.event_id}`}
                              className="text-blue hover:underline"
                            >
                              {e.group_label ?? e.title}
                            </Link>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2">
                            <span className="rounded-md bg-accent-soft px-1.5 py-0.5 text-[11px] font-semibold text-accent">
                              {e.event_type ?? "—"}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2">
                            <span
                              className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${STATUS_CLASS[e.status]}`}
                            >
                              {STATUS_LABEL[e.status]}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink">
                            {e.status === "permuta" || e.receita <= 0 ? (
                              <span className="text-muted">—</span>
                            ) : (
                              brl(e.receita)
                            )}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-red">
                            {brl(e.custo)}
                          </td>
                          <td
                            className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
                              e.lucro >= 0 ? "text-green" : "text-red"
                            }`}
                          >
                            {brl(e.lucro)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted">
                            {brl(e.comissao)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted">
                            {e.rate}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
