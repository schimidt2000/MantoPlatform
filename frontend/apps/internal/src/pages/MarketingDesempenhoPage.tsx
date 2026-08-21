import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import { Badge, Button, Card, Input, PageHeader, Skeleton, Table, TableCell, TableRow } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useMarketingDesempenho,
  type DesempenhoCampaign,
  type DesempenhoParams,
  type DesempenhoPost,
  type DesempenhoResponse,
  type DesempenhoRun,
  type DesempenhoWeeks,
} from "../lib/marketing";
import { LineSeriesChart } from "../components/charts/LineSeriesChart";
import { BarListChart } from "../components/charts/BarListChart";
import { FunnelChart } from "../components/charts/FunnelChart";

const WEEK_OPTIONS: { value: DesempenhoWeeks; label: string }[] = [
  { value: 4, label: "4 semanas" },
  { value: 12, label: "12 semanas" },
  { value: 26, label: "26 semanas" },
];

const brl = (valor: string | number | null | undefined) =>
  valor == null ? "—" : `R$ ${formatBRL(Number(valor))}`;
const num = (valor: number | null | undefined) => (valor == null ? "—" : valor.toLocaleString("pt-BR"));
const dataCurta = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano.slice(2)}`;
};
const pct = (parte: number, todo: number) => (todo > 0 ? `${((parte / todo) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} %` : "—");

const LINK_LABEL: Record<DesempenhoPost["link_method"], { texto: string; tone: "green" | "gold" | "neutral" }> = {
  permalink: { texto: "pelo link", tone: "green" },
  date: { texto: "pela data", tone: "gold" },
  none: { texto: "sem card", tone: "neutral" },
};

function KpiTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold leading-tight tabular-nums text-ink">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-muted">{hint}</p>}
    </Card>
  );
}

function Bloco({ title, children, hint }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Card className="divide-y divide-line">
      <div className="px-4 py-2.5">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {hint && <p className="text-[11px] text-muted">{hint}</p>}
      </div>
      <div className="px-4 py-3">{children}</div>
    </Card>
  );
}

function EstadoVazio() {
  return (
    <Card className="p-5">
      <h3 className="text-base font-semibold text-ink">Nenhuma rodada do auditor de marketing ainda</h3>
      <p className="mt-2 text-sm text-muted">
        Toda segunda-feira às 06:30 o auditor lê os exports salvos em{" "}
        <code className="rounded bg-surface-2 px-1 text-xs text-ink">scripts/marketing/inbox/</code> no computador da
        rotina, grava o histórico aqui e manda o relatório por e-mail. Para a primeira rodada, exporte:
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink">
        <li>Meta Business Suite → Insights → <strong>Conteúdo</strong> → Exportar (CSV, últimos 90 dias)</li>
        <li>Meta Business Suite → Insights → <strong>Público/Conta</strong> → Exportar (CSV)</li>
        <li>Gerenciador de Anúncios → Relatórios → <strong>Detalhamento: Dia</strong> → Exportar CSV</li>
        <li>Google Ads → Campanhas → Segmento <strong>Dia</strong> → Baixar CSV</li>
      </ul>
      <p className="mt-3 text-sm text-muted">Salve tudo na pasta até domingo à noite. Se um arquivo não for reconhecido, ele aparece aqui e no e-mail com o motivo.</p>
    </Card>
  );
}

function TabelaCampanhas({ campanhas }: { campanhas: DesempenhoCampaign[] }) {
  if (campanhas.length === 0) return <p className="text-sm text-muted">Nenhuma campanha com gasto no período.</p>;
  return (
    <div className="-mx-4 overflow-x-auto px-4">
      <Table className="min-w-[760px]">
        <thead>
          <TableRow head>
            <TableCell as="th">Plataforma</TableCell>
            <TableCell as="th">Campanha</TableCell>
            <TableCell as="th" align="right">Gasto</TableCell>
            <TableCell as="th" align="right">Cliques</TableCell>
            <TableCell as="th" align="right">CPC</TableCell>
            <TableCell as="th" align="right">Leads</TableCell>
            <TableCell as="th" align="right">Custo/lead</TableCell>
            <TableCell as="th" align="right">Eventos</TableCell>
            <TableCell as="th" align="right">Custo/evento</TableCell>
          </TableRow>
        </thead>
        <tbody>
          {campanhas.map((c) => (
            <TableRow key={`${c.platform}-${c.campaign_name}`}>
              <TableCell className="whitespace-nowrap">{c.platform}</TableCell>
              <TableCell className="font-medium text-ink">{c.campaign_name}</TableCell>
              <TableCell align="right" className="tabular-nums">{brl(c.spend)}</TableCell>
              <TableCell align="right" className="tabular-nums">{num(c.clicks)}</TableCell>
              <TableCell align="right" className="tabular-nums">{brl(c.cpc)}</TableCell>
              <TableCell align="right" className="tabular-nums">{num(c.leads)}</TableCell>
              <TableCell align="right" className="tabular-nums">{brl(c.cost_per_lead)}</TableCell>
              <TableCell align="right" className="tabular-nums">{num(c.events)}</TableCell>
              <TableCell align="right" className="tabular-nums">{brl(c.cost_per_event)}</TableCell>
            </TableRow>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function TabelaPosts({ posts }: { posts: DesempenhoPost[] }) {
  if (posts.length === 0) return <p className="text-sm text-muted">Nenhum post medido no período.</p>;
  return (
    <div className="-mx-4 overflow-x-auto px-4">
      <Table className="min-w-[860px]">
        <thead>
          <TableRow head>
            <TableCell as="th">Publicado</TableCell>
            <TableCell as="th">Post</TableCell>
            <TableCell as="th">Vínculo</TableCell>
            <TableCell as="th" align="right">Alcance</TableCell>
            <TableCell as="th" align="right">Curtidas</TableCell>
            <TableCell as="th" align="right">Coment.</TableCell>
            <TableCell as="th" align="right">Salvos</TableCell>
            <TableCell as="th" align="right">Compart.</TableCell>
            <TableCell as="th">Medido em</TableCell>
            <TableCell as="th" align="right">Link</TableCell>
          </TableRow>
        </thead>
        <tbody>
          {posts.map((p) => {
            const vinculo = LINK_LABEL[p.link_method];
            return (
              <TableRow key={`${p.platform}-${p.platform_post_id}`}>
                <TableCell className="whitespace-nowrap">{dataCurta(p.published_at)}</TableCell>
                <TableCell>
                  <span className="block max-w-[320px] truncate font-medium text-ink" title={p.marketing_post?.title ?? p.caption ?? ""}>
                    {p.marketing_post?.title ?? p.caption ?? p.platform_post_id}
                  </span>
                  <span className="text-[11px] text-muted">{p.post_type ?? p.platform}</span>
                </TableCell>
                <TableCell>
                  <Badge tone={vinculo.tone}>{vinculo.texto.toUpperCase()}</Badge>
                </TableCell>
                <TableCell align="right" className="tabular-nums">{num(p.reach)}</TableCell>
                <TableCell align="right" className="tabular-nums">{num(p.likes)}</TableCell>
                <TableCell align="right" className="tabular-nums">{num(p.comments)}</TableCell>
                <TableCell align="right" className="tabular-nums">{num(p.saves)}</TableCell>
                <TableCell align="right" className="tabular-nums">{num(p.shares)}</TableCell>
                <TableCell className="whitespace-nowrap">{dataCurta(p.snapshot_date)}</TableCell>
                <TableCell align="right">
                  {p.permalink ? (
                    <a href={p.permalink} target="_blank" rel="noopener" className="inline-flex items-center gap-1 text-accent hover:underline" aria-label="Abrir post">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </tbody>
      </Table>
    </div>
  );
}

function ListaRodadas({ runs }: { runs: DesempenhoRun[] }) {
  if (runs.length === 0) return <p className="text-sm text-muted">Nenhuma rodada registrada.</p>;
  return (
    <ul className="divide-y divide-line">
      {runs.map((r) => (
        <li key={r.run_id} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-2 text-sm">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
              {dataCurta(r.executed_at)} · rodada {r.run_id}
              {r.mode === "local" && <Badge tone="neutral">TESTE</Badge>}
              <Badge tone={r.report_sent ? "green" : "gold"}>{r.report_sent ? "E-MAIL ENVIADO" : "SEM E-MAIL"}</Badge>
            </div>
            <div className="text-muted">
              janela {dataCurta(r.window[0])} – {dataCurta(r.window[1])} · {r.files_accepted} arquivo(s) aceito(s), {r.files_rejected} rejeitado(s)
            </div>
            {r.rejected_files.length > 0 && (
              <ul className="mt-1 space-y-0.5 text-[12px] text-red">
                {r.rejected_files.map((f) => (
                  <li key={f.filename}>
                    {f.filename}: {f.reason ?? "não reconhecido"}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Conteudo({ data }: { data: DesempenhoResponse }) {
  const semanas = data.weekly;
  const gastoPeriodo = data.campaigns.reduce((s, c) => s + Number(c.spend), 0);
  const cliques = data.campaigns.reduce((s, c) => s + c.clicks, 0);
  const leads = data.campaigns.reduce((s, c) => s + c.leads, 0);
  const eventos = data.campaigns.reduce((s, c) => s + c.events, 0);
  const postsPublicados = semanas.reduce((s, w) => s + w.posts_published, 0);
  const metasAtrasadas = data.goals.filter((g) => g.status === "delayed");
  const manchete =
    data.headline.kind === "leads"
      ? { label: "Leads no período", value: num(data.headline.value), hint: data.headline.cost_per_lead ? `custo por lead ${brl(data.headline.cost_per_lead)}` : "sem gasto atribuído" }
      : { label: "Alcance dos posts", value: num(data.headline.value), hint: `leads indisponíveis — ${data.headline.fallback_reason ?? "sem atribuição"}` };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiTile label={manchete.label} value={manchete.value} hint={manchete.hint} />
        <KpiTile
          label={`CAC de ${data.cac.month.slice(5)}/${data.cac.month.slice(0, 4)}`}
          value={brl(data.cac.value)}
          hint={`${brl(data.cac.spend)} em anúncios ÷ ${data.cac.new_clients} cliente(s) novo(s)`}
        />
        <KpiTile label="Gasto no período" value={brl(gastoPeriodo)} hint={`${num(cliques)} cliques`} />
        <KpiTile
          label="Posts publicados"
          value={num(postsPublicados)}
          hint={metasAtrasadas.length ? `${metasAtrasadas.length} meta(s) de frequência atrasada(s)` : "metas de frequência em dia"}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Bloco title="Alcance por semana" hint="soma do alcance dos posts publicados em cada semana">
          <LineSeriesChart title="Alcance por semana" points={semanas.map((w) => ({ label: dataCurta(w.week_start), value: w.reach }))} tone="accent" />
        </Bloco>
        <Bloco title="Seguidores" hint="último valor medido em cada semana">
          <LineSeriesChart title="Seguidores" points={semanas.map((w) => ({ label: dataCurta(w.week_start), value: w.followers }))} tone="green" />
        </Bloco>
        <Bloco title="Gasto por campanha">
          <BarListChart
            items={data.campaigns.map((c) => ({ label: c.campaign_name, sublabel: c.platform, value: Number(c.spend), display: brl(c.spend) }))}
            tone="gold"
          />
        </Bloco>
        <Bloco title="Funil do período" hint="gasto → cliques → leads (utm) → eventos fechados">
          <FunnelChart
            stages={[
              { label: "Gasto", value: gastoPeriodo, display: brl(gastoPeriodo) },
              { label: "Cliques", value: cliques, display: num(cliques) },
              { label: "Leads", value: leads, display: num(leads) },
              { label: "Eventos", value: eventos, display: num(eventos) },
            ]}
            ratios={[
              cliques ? `CPC ${brl(gastoPeriodo / cliques)}` : null,
              leads ? `${pct(leads, cliques)} viram lead · ${brl(gastoPeriodo / leads)}/lead` : "sem lead atribuído",
              eventos ? `${pct(eventos, leads)} fecham · ${brl(gastoPeriodo / eventos)}/evento` : "sem evento atribuído",
            ]}
          />
        </Bloco>
      </div>

      <details className="rounded-lg border border-line bg-panel px-4 py-2 text-sm">
        <summary className="cursor-pointer font-medium text-ink">Ver tabela semanal</summary>
        <div className="-mx-4 mt-2 overflow-x-auto px-4">
          <Table className="min-w-[640px]">
            <thead>
              <TableRow head>
                <TableCell as="th">Semana</TableCell>
                <TableCell as="th" align="right">Posts</TableCell>
                <TableCell as="th" align="right">Alcance</TableCell>
                <TableCell as="th" align="right">Seguidores</TableCell>
                <TableCell as="th" align="right">Gasto</TableCell>
                <TableCell as="th" align="right">Cliques</TableCell>
                <TableCell as="th" align="right">Leads</TableCell>
                <TableCell as="th" align="right">Eventos</TableCell>
              </TableRow>
            </thead>
            <tbody>
              {semanas.map((w) => (
                <TableRow key={w.week_start}>
                  <TableCell>{dataCurta(w.week_start)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.posts_published)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.reach)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.followers)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{brl(w.spend)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.clicks)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.leads)}</TableCell>
                  <TableCell align="right" className="tabular-nums">{num(w.events)}</TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
        </div>
      </details>

      <Bloco title="Campanhas" hint="leads e eventos vêm do utm_campaign dos leads importados do CRM">
        <TabelaCampanhas campanhas={data.campaigns} />
      </Bloco>

      <Bloco title="Posts medidos" hint='"sem card" = o post existe no Instagram mas não foi reconhecido no painel — informe o link no card'>
        <TabelaPosts posts={data.posts} />
      </Bloco>

      {metasAtrasadas.length > 0 && (
        <Bloco title="Metas de frequência atrasadas">
          <ul className="space-y-1 text-sm">
            {metasAtrasadas.map((g) => (
              <li key={g.id} className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{g.name}</span>
                <span className="text-muted">
                  {g.never_posted ? "nunca postado" : `${g.days_late ?? 0} dia(s) além do intervalo de ${g.target_interval_days}`}
                </span>
              </li>
            ))}
          </ul>
          <Button asChild variant="outline" size="sm" className="mt-3">
            <Link to="/marketing/metas">Abrir metas</Link>
          </Button>
        </Bloco>
      )}

      <Bloco title="Rodadas do auditor" hint="uma por segunda-feira; arquivos rejeitados aparecem com o motivo">
        <ListaRodadas runs={data.runs} />
      </Bloco>
    </div>
  );
}

export function MarketingDesempenhoPage() {
  const reduceMotion = useReducedMotion();
  const [params, setParams] = useState<DesempenhoParams>({ weeks: 12 });
  const [personalizado, setPersonalizado] = useState(false);
  const [rascunho, setRascunho] = useState({ start: "", end: "" });
  const query = useMarketingDesempenho(params);
  const intervaloInvalido = !rascunho.start || !rascunho.end || rascunho.start > rascunho.end;

  const seletor = (
    <div className="flex flex-wrap items-center gap-2">
      <div className="inline-flex rounded-md border border-line bg-surface p-0.5" role="radiogroup" aria-label="Período">
        {WEEK_OPTIONS.map((opt) => {
          const ativo = !personalizado && "weeks" in params && params.weeks === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => {
                setPersonalizado(false);
                setParams({ weeks: opt.value });
              }}
              className={`cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors ${ativo ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink"}`}
            >
              {opt.label}
            </button>
          );
        })}
        <button
          type="button"
          role="radio"
          aria-checked={personalizado}
          onClick={() => setPersonalizado(true)}
          className={`cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors ${personalizado ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink"}`}
        >
          Personalizado
        </button>
      </div>
      {personalizado && (
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!intervaloInvalido) setParams({ start: rascunho.start, end: rascunho.end });
          }}
        >
          <Input type="date" value={rascunho.start} onChange={(e) => setRascunho((r) => ({ ...r, start: e.target.value }))} className="h-9 w-40" aria-label="Data inicial" />
          <span className="text-sm text-muted">até</span>
          <Input type="date" value={rascunho.end} onChange={(e) => setRascunho((r) => ({ ...r, end: e.target.value }))} className="h-9 w-40" aria-label="Data final" />
          <Button type="submit" size="sm" variant="outline" disabled={intervaloInvalido}>
            Aplicar
          </Button>
        </form>
      )}
    </div>
  );

  return (
    <div className="w-full px-6 py-6 sm:px-8">
      <PageHeader
        title="Desempenho de marketing"
        subtitle={
          query.data
            ? `${dataCurta(query.data.period.start)} – ${dataCurta(query.data.period.end)} · o que os exports da Meta e do Google dizem, semana a semana`
            : "o que os exports da Meta e do Google dizem, semana a semana"
        }
        filters={seletor}
      />

      {query.isLoading && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-56 w-full" />
            ))}
          </div>
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o desempenho. Tente novamente em instantes.
        </div>
      )}

      {query.data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className={`transition-opacity duration-200 ${query.isPlaceholderData ? "opacity-60" : ""}`}
          aria-busy={query.isPlaceholderData || undefined}
        >
          {query.data.empty ? <EstadoVazio /> : <Conteudo data={query.data} />}
        </motion.div>
      )}
    </div>
  );
}
