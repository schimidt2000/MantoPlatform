import { useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, MetricBadge, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useCurrentUser } from "../lib/useAuth";
import type {
  DashboardSummary,
  DashboardTaskRef,
  EnsaioEventRef,
  EnsaioSummary,
  MinhaPecaRef,
  PendingPayment,
  UnconfirmedInviteRef,
} from "../lib/types";
import { SectorPanel, getUrgency } from "../components/SectorPanel";
import { HomeOverview, type HomeOverviewItem } from "../components/HomeOverview";
import { HomePerformance, type PerformancePeriod } from "../components/HomePerformance";

/** Urgência "vermelha" (evento em ≤2 dias) — mesmo corte visual das linhas. */
function isUrgente(startAt: string | null): boolean {
  return getUrgency(startAt)?.tone === "red";
}

/** Peça crítica: não pode ir para evento, prazo estourado ou a ≤2 dias (feature 225). */
function isPecaCritica(item: MinhaPecaRef): boolean {
  return (
    item.impede_uso || item.is_late || (item.dias_para_prazo != null && item.dias_para_prazo <= 2)
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    </div>
  );
}

function TaskRow({ task, badge }: { task: DashboardTaskRef; badge?: ReactNode }) {
  const urgency = getUrgency(task.start_at);
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {task.character_name}
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
          {badge}
        </div>
        <Link to={`/events/${task.event_id}`} className="text-muted hover:underline">
          {task.event_title}
          {task.start_at && ` — ${new Date(task.start_at).toLocaleDateString("pt-BR")}`}
        </Link>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${task.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/**
 * Linha de "quem ainda não confirmou" (feature 231).
 *
 * Mostra a ação certa para cada caso, que é o que a lista existe para responder: convite enviado
 * e sem resposta vira cobrança no WhatsApp; convite nunca enviado é o casting que precisa mandar,
 * e aí o caminho é abrir o evento. Também diz quantos lembretes automáticos já saíram, para
 * ninguém cobrar de novo quem o robô acabou de cobrar.
 */
function UnconfirmedRow({ item, portalUrl }: { item: UnconfirmedInviteRef; portalUrl: string | null }) {
  const urgency = getUrgency(item.start_at);
  const nuncaEnviado = item.invite_status !== "pending";
  // Barra final é o mesmo padrão que os e-mails automáticos já usam (`f"{portal_url}/"`); se a
  // env var não estiver setada, `portalUrl` vem `null` e o link é omitido em vez de quebrado.
  const linkPortal = portalUrl ? ` ${portalUrl}/` : "";
  const zap = item.whatsapp
    ? `https://wa.me/${item.whatsapp.replace(/\D/g, "")}?text=${encodeURIComponent(
        `Oi, ${item.talent_name}! Falta você confirmar no portal a sua presença em "${item.event_title}". Consegue responder por lá?${linkPortal}`,
      )}`
    : null;

  return (
    <div
      className="-mx-4 flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {item.talent_name}
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
          <MetricBadge tone={nuncaEnviado ? "red" : "neutral"} size="xs">
            {nuncaEnviado ? "convite não enviado" : "sem resposta"}
          </MetricBadge>
          {item.reminder_count > 0 && (
            <span className="text-[11px] text-muted">
              {item.reminder_count} lembrete{item.reminder_count > 1 ? "s" : ""} enviado
              {item.reminder_count > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <Link to={`/events/${item.event_id}`} className="text-muted hover:underline">
          {item.character_name} · {item.event_title}
          {item.start_at && ` — ${new Date(item.start_at).toLocaleDateString("pt-BR")}`}
        </Link>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {zap && !nuncaEnviado && (
          <Button asChild variant="outline" size="sm">
            <a href={zap} target="_blank" rel="noopener">
              Cobrar no WhatsApp
            </a>
          </Button>
        )}
        <Button asChild variant={nuncaEnviado ? "default" : "outline"} size="sm">
          <Link to={`/events/${item.event_id}`}>{nuncaEnviado ? "Enviar convite" : "Abrir"}</Link>
        </Button>
      </div>
    </div>
  );
}

/** Linha de evento do painel de Ensaio (sem cargo — o link é o próprio evento). */
function EnsaioEventRow({ item, extra }: { item: EnsaioEventRef; extra?: string }) {
  const urgency = getUrgency(item.start_at);
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={urgency ? { background: urgency.rowBackground } : undefined}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 font-medium text-ink">
          <Link to={`/events/${item.event_id}`} className="min-w-0 truncate hover:underline">
            {item.event_title}
          </Link>
          {urgency && (
            <MetricBadge tone={urgency.tone} size="xs">
              {urgency.label}
            </MetricBadge>
          )}
        </div>
        <div className="text-muted">
          {item.start_at && new Date(item.start_at).toLocaleDateString("pt-BR")}
          {extra && ` — ${extra}`}
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${item.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/** Sub-lista com título dentro de um painel (Ensaio, Casting). */
function PanelGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-1 pt-2 first:pt-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {children}
    </div>
  );
}

const LIMITE_LINHAS_PAINEL = 6;

/**
 * Lista com as primeiras linhas à mostra e o resto atrás de "Mostrar todas" — as consultas já
 * vêm ordenadas por data, então o topo é sempre o mais próximo de acontecer. É o que devolve a
 * legibilidade no celular sem esconder nada: a fila inteira continua a um toque.
 */
function ListaTruncada({ children }: { children: ReactNode[] }) {
  const [expandida, setExpandida] = useState(false);
  const reduceMotion = useReducedMotion();

  if (children.length <= LIMITE_LINHAS_PAINEL) return <>{children}</>;

  return (
    <>
      {children.slice(0, LIMITE_LINHAS_PAINEL)}
      <AnimatePresence initial={false}>
        {expandida && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            {children.slice(LIMITE_LINHAS_PAINEL)}
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        onClick={() => setExpandida((v) => !v)}
        className="-mx-4 block w-[calc(100%+2rem)] cursor-pointer px-4 py-2 text-center text-xs font-medium text-accent hover:bg-surface-2"
      >
        {expandida ? "Mostrar menos" : `Mostrar todas as ${children.length}`}
      </button>
    </>
  );
}

/**
 * Painel do papel ENSAIO — as quatro listas restauradas da home Jinja (206): shows a
 * agendar, agendados, ensaios órfãos e a vaga de Técnico de Som (Presença) sem talento.
 */
function EnsaioPanel({
  summary,
  urgentCount,
  open,
  onOpenChange,
}: {
  summary: EnsaioSummary;
  urgentCount: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const pendencias =
    summary.pending.length + summary.orphans.length + summary.pending_presence.length;
  return (
    <SectorPanel
      title="🎭 Ensaio"
      count={pendencias}
      urgentCount={urgentCount}
      open={open}
      onOpenChange={onOpenChange}
    >
      <div className="space-y-3">
        <PanelGroup title={`A agendar (${summary.pending.length})`}>
          {summary.pending.length === 0 ? (
            <p className="py-1 text-sm text-muted">Nenhum show esperando ensaio.</p>
          ) : (
            <ListaTruncada>
              {summary.pending.map((item) => (
                <EnsaioEventRow key={item.event_id} item={item} />
              ))}
            </ListaTruncada>
          )}
        </PanelGroup>

        <PanelGroup title={`Presença pendente (${summary.pending_presence.length})`}>
          {summary.pending_presence.length === 0 ? (
            <p className="py-1 text-sm text-muted">Técnico definido em todos os shows.</p>
          ) : (
            <ListaTruncada>
              {summary.pending_presence.map((t) => (
                <TaskRow key={t.role_id ?? `${t.event_id}-presenca`} task={t} />
              ))}
            </ListaTruncada>
          )}
        </PanelGroup>

        {summary.orphans.length > 0 && (
          <PanelGroup title={`Ensaios órfãos (${summary.orphans.length})`}>
            <ListaTruncada>
              {summary.orphans.map((item) => (
                <EnsaioEventRow key={item.event_id} item={item} extra="show original removido" />
              ))}
            </ListaTruncada>
          </PanelGroup>
        )}

        {summary.scheduled.length > 0 && (
          <PanelGroup title={`Agendados (${summary.scheduled.length})`}>
            <ListaTruncada>
              {summary.scheduled.map((item) => (
                <EnsaioEventRow
                  key={item.event_id}
                  item={item}
                  extra={`ensaio: ${item.ensaios
                    .filter(Boolean)
                    .map((iso) =>
                      new Date(iso as string).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                      }),
                    )
                    .join(", ")}`}
                />
              ))}
            </ListaTruncada>
          </PanelGroup>
        )}
      </div>
    </SectorPanel>
  );
}

const SEVERITY_TONE: Record<PendingPayment["severity"], "red" | "gold" | "neutral"> = {
  atrasado: "red",
  vencido: "red",
  urgent: "red",
  warn: "gold",
  info: "neutral",
};

const SEVERITY_ROW_BG: Partial<Record<PendingPayment["severity"], string>> = {
  atrasado: "rgba(228,88,88,0.06)",
  vencido: "rgba(228,88,88,0.06)",
  urgent: "rgba(228,88,88,0.06)",
  warn: "rgba(245,200,66,0.06)",
};

/** Severidades do comercial que pedem ação imediata (viram o recorte "urgente"). */
const SEVERIDADES_URGENTES: PendingPayment["severity"][] = ["atrasado", "vencido", "urgent"];

function PendingPaymentRow({ item }: { item: PendingPayment }) {
  const rowBg = SEVERITY_ROW_BG[item.severity];
  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={rowBg ? { background: rowBg } : undefined}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 font-medium text-ink">
          <Link to={`/events/${item.event_id}`} className="hover:underline">
            {item.event_title}
          </Link>
          <MetricBadge tone={SEVERITY_TONE[item.severity]} size="xs">
            {item.severity.toUpperCase()}
          </MetricBadge>
        </div>
        <div className="text-muted">
          Recebido R$ {formatBRL(item.received)} de R$ {formatBRL(item.sale)} — falta R${" "}
          {formatBRL(item.saldo)}
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/events/${item.event_id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/**
 * Uma peça de figurino sob responsabilidade de quem está logado (feature 225).
 *
 * Não reusa `TaskRow` porque a urgência aqui não vem de `start_at` do evento e sim do prazo do
 * pedido — que pode ser bem antes do show, e é justamente o que se perde de vista hoje.
 */
function MinhaPecaRow({ item }: { item: MinhaPecaRef }) {
  const dias = item.dias_para_prazo;
  // "Não pode ir para evento" é crítico mesmo sem prazo apertado: o boneco está fora de uso.
  const critico = isPecaCritica(item);
  const rotulo = item.is_late
    ? `ATRASADO ${Math.abs(dias ?? 0)}d`
    : dias == null
      ? null
      : dias === 0
        ? "HOJE"
        : `${dias}d`;
  const contexto = item.figurino_sheet_name ?? item.event_title;

  return (
    <div
      className="-mx-4 flex items-center justify-between gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0"
      style={critico ? { background: "rgba(228,88,88,0.06)" } : undefined}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {item.title}
          {item.impede_uso && (
            <MetricBadge tone="red" size="xs">
              NÃO PODE IR
            </MetricBadge>
          )}
          {rotulo && (
            <MetricBadge tone={critico ? "red" : "neutral"} size="xs">
              {rotulo}
            </MetricBadge>
          )}
        </div>
        <span className="text-muted">
          {item.kind_label} · {item.status_label}
          {contexto && ` — ${contexto}`}
        </span>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={`/figurinos/producao/${item.id}`}>Abrir</Link>
      </Button>
    </div>
  );
}

/** Uma linha "rótulo → número" do painel de formulários (feature 266). */
function LinhaFormularios({
  rotulo,
  valor,
  urgente = false,
}: {
  rotulo: string;
  valor: number;
  urgente?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line py-2 last:border-b-0">
      <dt className={urgente && valor > 0 ? "text-red" : "text-ink"}>{rotulo}</dt>
      <dd
        className={`tabular-nums ${urgente && valor > 0 ? "font-semibold text-red" : "text-ink"}`}
      >
        {valor}
      </dd>
    </div>
  );
}

/** Ordem fixa das seções — a mesma na visão geral e na pilha de painéis (previsibilidade). */
type SectionKey =
  | "minhas_pecas"
  | "oficina"
  | "casting"
  | "confirmacoes"
  | "figurino"
  | "ensaio"
  | "comercial"
  | "formularios"
  | "recorrentes";

interface SectionStat extends HomeOverviewItem {
  key: SectionKey;
}

/**
 * Contagens por seção a partir do resumo da API — alimentam a visão geral, os selos de urgência
 * dos painéis e o padrão de abertura (painel nasce aberto só quando tem item urgente).
 */
function computeSectionStats(data: DashboardSummary): SectionStat[] {
  const stats: SectionStat[] = [];

  if (data.figurino_producao) {
    stats.push({
      key: "minhas_pecas",
      emoji: "🧵",
      label: "Minhas peças",
      count: data.figurino_producao.pending,
      urgent: data.figurino_producao.items.filter(isPecaCritica).length,
    });
  }

  if (data.figurino_oficina) {
    stats.push({
      key: "oficina",
      emoji: "🪡",
      label: "Oficina",
      count: data.figurino_oficina.pending,
      urgent: data.figurino_oficina.impedem_uso,
    });
  }

  if (data.casting) {
    const recusados = recusadosSemDuplicata(data.casting.pending, data.casting.rejected_invites);
    const aEscalar = data.casting.pending;
    stats.push({
      key: "casting",
      emoji: "👥",
      label: "Escalar",
      count: aEscalar.length + recusados.length,
      urgent: [...aEscalar, ...recusados].filter((t) => isUrgente(t.start_at)).length,
      detail: recusados.length > 0 ? `${recusados.length} recusa${recusados.length !== 1 ? "s" : ""} de convite` : null,
    });

    const semConvite = data.casting.unconfirmed.filter((i) => i.invite_status !== "pending");
    stats.push({
      key: "confirmacoes",
      emoji: "🙋",
      label: "Confirmações",
      count: data.casting.unconfirmed.length,
      urgent: data.casting.unconfirmed.filter((i) => isUrgente(i.start_at)).length,
      detail: semConvite.length > 0 ? `${semConvite.length} sem convite enviado` : null,
    });
  }

  if (data.figurino) {
    stats.push({
      key: "figurino",
      emoji: "👗",
      label: "Figurino",
      count: data.figurino.pending.length,
      urgent: data.figurino.pending.filter((t) => isUrgente(t.start_at)).length,
    });
  }

  if (data.ensaio) {
    const e = data.ensaio;
    stats.push({
      key: "ensaio",
      emoji: "🎭",
      label: "Ensaio",
      count: e.pending.length + e.orphans.length + e.pending_presence.length,
      urgent:
        e.pending.filter((ev) => isUrgente(ev.start_at)).length +
        e.pending_presence.filter((t) => isUrgente(t.start_at)).length,
    });
  }

  if (data.comercial) {
    const pagamentos = data.comercial.pending_payments;
    const saldoTotal = pagamentos.reduce((soma, p) => soma + p.saldo, 0);
    stats.push({
      key: "comercial",
      emoji: "💼",
      label: "Cobranças",
      count: pagamentos.length,
      urgent: pagamentos.filter((p) => SEVERIDADES_URGENTES.includes(p.severity)).length,
      detail: pagamentos.length > 0 ? `R$ ${formatBRL(saldoTotal)} em aberto` : null,
    });
  }

  if (data.formularios) {
    const f = data.formularios;
    stats.push({
      key: "formularios",
      emoji: "📝",
      label: "Formulários",
      // A contagem é "ainda não virou evento"; a urgência é a festa marcada chegando sem
      // evento na agenda — a única das quatro que tem data batendo na porta.
      count: f.sem_evento,
      urgent: f.futuros_sem_evento,
      detail: f.total > 0 ? `${f.total} resposta(s) recebidas` : null,
    });
  }

  if (data.financeiro) {
    const alertas = data.financeiro.recurring_expense_alerts;
    const valores = alertas.map((a) => a.amount);
    const somaConhecida = valores.every((v) => v != null)
      ? (valores as number[]).reduce((s, v) => s + v, 0)
      : null;
    stats.push({
      key: "recorrentes",
      emoji: "🔁",
      label: "Contas do mês",
      count: alertas.length,
      urgent: 0,
      detail: somaConhecida != null && alertas.length > 0 ? `R$ ${formatBRL(somaConhecida)} a pagar` : null,
    });
  }

  return stats;
}

/**
 * Convites recusados que ainda não viraram vaga aberta (feature 231 mandava e a tela jogava
 * fora). Quando o casting limpa o talento da vaga, o cargo já entra em `pending` — aí a recusa
 * sai daqui para não contar duas vezes.
 */
function recusadosSemDuplicata(
  pending: DashboardTaskRef[],
  rejected: DashboardTaskRef[],
): DashboardTaskRef[] {
  const idsPendentes = new Set(pending.map((t) => t.role_id).filter((id) => id != null));
  return rejected.filter((t) => t.role_id == null || !idsPendentes.has(t.role_id));
}

export function DashboardPage() {
  const reduceMotion = useReducedMotion();
  const { data: user } = useCurrentUser();

  // Período do painel Performance (só superadmin). Entra na chave da query porque a API calcula
  // tudo numa resposta só; `keepPreviousData` segura os números antigos enquanto o novo período
  // carrega, para a visão geral e os painéis não piscarem a cada troca.
  const [periodo, setPeriodo] = useState<PerformancePeriod>({ range: "7" });
  const dashboard = useQuery<DashboardSummary>({
    queryKey: ["dashboard", periodo],
    queryFn: () => {
      const params = new URLSearchParams({ perf_range: periodo.range });
      if (periodo.range === "custom" && periodo.start && periodo.end) {
        params.set("perf_start", periodo.start);
        params.set("perf_end", periodo.end);
      }
      return apiFetch<DashboardSummary>(`/api/dashboard?${params}`);
    },
    placeholderData: keepPreviousData,
  });

  const stats = useMemo(
    () => (dashboard.data ? computeSectionStats(dashboard.data) : []),
    [dashboard.data],
  );
  const statPorSecao = useMemo(
    () => new Map(stats.map((s) => [s.key, s])),
    [stats],
  );
  const totalPendencias = stats.reduce((soma, s) => soma + s.count, 0);
  const totalUrgentes = stats.reduce((soma, s) => soma + s.urgent, 0);

  // Abertura dos painéis: escolha explícita da pessoa vence; sem escolha, nasce aberto só quem
  // tem item urgente — é a triagem que devolve a Home legível no celular.
  const [abertos, setAbertos] = useState<Partial<Record<SectionKey, boolean>>>({});
  const painelAberto = (key: SectionKey) => abertos[key] ?? (statPorSecao.get(key)?.urgent ?? 0) > 0;
  const aoAlternar = (key: SectionKey) => (open: boolean) =>
    setAbertos((prev) => ({ ...prev, [key]: open }));

  const refsSecoes = useRef<Partial<Record<SectionKey, HTMLDivElement | null>>>({});
  const irParaSecao = (key: string) => {
    setAbertos((prev) => ({ ...prev, [key]: true }));
    // Espera o painel abrir para rolar até a posição final dele. `setTimeout` (e não rAF):
    // rAF congela em aba oculta e o scroll ficaria retido até a aba voltar ao foco.
    setTimeout(() => {
      refsSecoes.current[key as SectionKey]?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "start",
      });
    }, 0);
  };

  // Props do wrapper de cada seção: alvo do scroll da visão geral, com `scroll-mt` compensando
  // o topbar sticky do mobile. É função (e não componente local) de propósito — componente
  // definido dentro do render seria um tipo novo a cada passada e remontaria os painéis.
  const propsSecao = (chave: SectionKey) => ({
    ref: (el: HTMLDivElement | null) => {
      refsSecoes.current[chave] = el;
    },
    className: "scroll-mt-16 lg:scroll-mt-4",
  });

  const data = dashboard.data;
  const recusados = data?.casting
    ? recusadosSemDuplicata(data.casting.pending, data.casting.rejected_invites)
    : [];

  return (
    <div className="w-full px-6 py-6 sm:px-8">
      <PageHeader title="Início" subtitle={user ? `Olá, ${user.name}` : undefined} />

      {dashboard.isLoading && <DashboardSkeleton />}

      {dashboard.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o resumo. Tente novamente em instantes.
        </div>
      )}

      {data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          {stats.length > 0 && (
            <section aria-label="Visão geral das pendências" className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                {totalPendencias > 0 ? (
                  <>
                    <span>
                      {totalPendencias} pendência{totalPendencias !== 1 ? "s" : ""} no total
                    </span>
                    {totalUrgentes > 0 && (
                      <span className="rounded-full bg-red-soft px-2 py-0.5 font-medium text-red">
                        {totalUrgentes} urgente{totalUrgentes !== 1 ? "s" : ""}
                      </span>
                    )}
                  </>
                ) : (
                  <span className="rounded-full bg-green-soft px-2 py-0.5 font-medium text-green">
                    Tudo em dia ✓
                  </span>
                )}
              </div>
              <HomeOverview items={stats} onSelect={irParaSecao} />
            </section>
          )}

          {/* Performance (somente leitura, só superadmin real): a API devolve `null` para quem
              não é superadmin e durante o "Ver como" — e também quando o período personalizado
              ainda não foi preenchido, caso em que o painel precisa continuar na tela. */}
          {(data.performance || (user?.is_superadmin && periodo.range === "custom")) && (
            <HomePerformance
              summary={data.performance}
              period={periodo}
              onPeriodChange={setPeriodo}
              atualizando={dashboard.isPlaceholderData}
            />
          )}

          {/* `grid-cols-1` explícito: sem template, a coluna implícita dimensiona por
              max-content e um título de evento comprido estoura a página no celular. */}
          <div className="grid grid-cols-1 items-start gap-3 lg:grid-cols-2">
            {/* Primeiro painel da home de propósito (feature 225): é o único pessoal — o que está
                nas mãos de quem está lendo. Só aparece para quem tem peça sob sua responsabilidade. */}
            {data.figurino_producao && (
              <div {...propsSecao("minhas_pecas")}>
                <SectorPanel
                  title="🧵 Minhas peças e compras"
                  count={data.figurino_producao.pending}
                  urgentCount={statPorSecao.get("minhas_pecas")?.urgent ?? 0}
                  open={painelAberto("minhas_pecas")}
                  onOpenChange={aoAlternar("minhas_pecas")}
                >
                  <ListaTruncada>
                    {data.figurino_producao.items.map((item) => (
                      <MinhaPecaRow key={item.id} item={item} />
                    ))}
                  </ListaTruncada>
                </SectorPanel>
              </div>
            )}

            {/* Caixa de entrada do setor (225b): manutenção quase sempre nasce sem dono, porque
                quem relata o defeito recebeu o feedback do evento e não é quem vai consertar. */}
            {data.figurino_oficina && (
              <div {...propsSecao("oficina")}>
                <SectorPanel
                  title="🪡 Oficina — sem responsável"
                  count={data.figurino_oficina.pending}
                  urgentCount={statPorSecao.get("oficina")?.urgent ?? 0}
                  open={painelAberto("oficina")}
                  onOpenChange={aoAlternar("oficina")}
                >
                  <ListaTruncada>
                    {data.figurino_oficina.items.map((item) => (
                      <MinhaPecaRow key={item.id} item={item} />
                    ))}
                  </ListaTruncada>
                </SectorPanel>
              </div>
            )}

            {data.casting && (
              <div {...propsSecao("casting")}>
                <SectorPanel
                  title="👥 Casting"
                  count={data.casting.pending.length + recusados.length}
                  urgentCount={statPorSecao.get("casting")?.urgent ?? 0}
                  open={painelAberto("casting")}
                  onOpenChange={aoAlternar("casting")}
                >
                  {data.casting.pending.length === 0 && recusados.length === 0 ? (
                    <p className="py-2 text-sm text-muted">Nenhuma pendência.</p>
                  ) : (
                    <div className="space-y-3">
                      <PanelGroup title={`A escalar (${data.casting.pending.length})`}>
                        {data.casting.pending.length === 0 ? (
                          <p className="py-1 text-sm text-muted">Nenhuma vaga aberta.</p>
                        ) : (
                          <ListaTruncada>
                            {data.casting.pending.map((t) => (
                              <TaskRow key={t.role_id ?? `${t.event_id}-${t.character_name}`} task={t} />
                            ))}
                          </ListaTruncada>
                        )}
                      </PanelGroup>

                      {recusados.length > 0 && (
                        <PanelGroup title={`Convites recusados (${recusados.length})`}>
                          <ListaTruncada>
                            {recusados.map((t) => (
                              <TaskRow
                                key={t.role_id ?? `${t.event_id}-${t.character_name}`}
                                task={t}
                                badge={
                                  <MetricBadge tone="red" size="xs">
                                    recusou
                                  </MetricBadge>
                                }
                              />
                            ))}
                          </ListaTruncada>
                        </PanelGroup>
                      )}
                    </div>
                  )}
                </SectorPanel>
              </div>
            )}

            {data.casting && (
              <div {...propsSecao("confirmacoes")}>
                <SectorPanel
                  title="🙋 Confirmações pendentes"
                  count={data.casting.unconfirmed.length}
                  urgentCount={statPorSecao.get("confirmacoes")?.urgent ?? 0}
                  open={painelAberto("confirmacoes")}
                  onOpenChange={aoAlternar("confirmacoes")}
                >
                  {data.casting.unconfirmed.length === 0 ? (
                    <p className="py-2 text-sm text-muted">Todo mundo confirmado. ✓</p>
                  ) : (
                    <>
                      {/* O robô só cobra quem JÁ recebeu convite, e só na semana do evento — quem
                          está com "convite não enviado" depende de alguém aqui. Dizer isso na tela
                          evita a suposição de que o automático resolve tudo. */}
                      <p className="py-2 text-xs text-muted">
                        A cobrança automática por e-mail alcança só quem já recebeu o convite, na
                        semana do evento, no máximo 2 vezes. Quem está como{" "}
                        <strong className="text-ink">convite não enviado</strong> depende de você.
                      </p>
                      <ListaTruncada>
                        {data.casting.unconfirmed.map((item) => (
                          <UnconfirmedRow
                            key={item.role_id ?? `${item.event_id}-${item.talent_id}`}
                            item={item}
                            portalUrl={data.portal_url}
                          />
                        ))}
                      </ListaTruncada>
                    </>
                  )}
                </SectorPanel>
              </div>
            )}

            {data.figurino && (
              <div {...propsSecao("figurino")}>
                <SectorPanel
                  title="👗 Figurino"
                  count={data.figurino.pending.length}
                  urgentCount={statPorSecao.get("figurino")?.urgent ?? 0}
                  open={painelAberto("figurino")}
                  onOpenChange={aoAlternar("figurino")}
                >
                  {data.figurino.pending.length === 0 ? (
                    <p className="py-2 text-sm text-muted">Nenhuma pendência.</p>
                  ) : (
                    <ListaTruncada>
                      {data.figurino.pending.map((t) => (
                        <TaskRow key={t.role_id ?? `${t.event_id}-${t.character_name}`} task={t} />
                      ))}
                    </ListaTruncada>
                  )}
                </SectorPanel>
              </div>
            )}

            {data.ensaio && (
              <div {...propsSecao("ensaio")}>
                <EnsaioPanel
                  summary={data.ensaio}
                  urgentCount={statPorSecao.get("ensaio")?.urgent ?? 0}
                  open={painelAberto("ensaio")}
                  onOpenChange={aoAlternar("ensaio")}
                />
              </div>
            )}

            {data.comercial && (
              <div {...propsSecao("comercial")}>
                <SectorPanel
                  title="💼 Comercial"
                  count={data.comercial.pending_payments.length}
                  urgentCount={statPorSecao.get("comercial")?.urgent ?? 0}
                  open={painelAberto("comercial")}
                  onOpenChange={aoAlternar("comercial")}
                >
                  {data.comercial.pending_payments.length === 0 ? (
                    <p className="py-2 text-sm text-muted">Nenhuma pendência comercial.</p>
                  ) : (
                    <ListaTruncada>
                      {data.comercial.pending_payments.map((p) => (
                        <PendingPaymentRow key={p.event_id} item={p} />
                      ))}
                    </ListaTruncada>
                  )}
                </SectorPanel>
              </div>
            )}

            {data.formularios && (
              <div {...propsSecao("formularios")}>
                <SectorPanel
                  title="📝 Respostas de formulário"
                  count={data.formularios.sem_evento}
                  urgentCount={data.formularios.futuros_sem_evento}
                  open={painelAberto("formularios")}
                  onOpenChange={aoAlternar("formularios")}
                >
                  {data.formularios.total === 0 ? (
                    <p className="py-2 text-sm text-muted">Nenhuma resposta recebida.</p>
                  ) : (
                    <>
                      <dl className="text-sm">
                        <LinhaFormularios
                          rotulo="Festa futura sem evento"
                          valor={data.formularios.futuros_sem_evento}
                          urgente
                        />
                        <LinhaFormularios
                          rotulo="Sem evento na agenda"
                          valor={data.formularios.sem_evento}
                        />
                        <LinhaFormularios
                          rotulo="Sem cliente associada"
                          valor={data.formularios.sem_cliente}
                        />
                        <LinhaFormularios
                          rotulo="Vínculo ambíguo"
                          valor={data.formularios.ambiguos}
                        />
                      </dl>
                      <Button asChild variant="outline" size="sm" className="mt-3">
                        <Link to="/formularios">Abrir formulários</Link>
                      </Button>
                    </>
                  )}
                </SectorPanel>
              </div>
            )}

            {data.financeiro && (
              <div {...propsSecao("recorrentes")}>
                <SectorPanel
                  title="🔁 Contas recorrentes"
                  count={data.financeiro.recurring_expense_alerts.length}
                  urgentCount={0}
                  open={painelAberto("recorrentes")}
                  onOpenChange={aoAlternar("recorrentes")}
                >
                  {data.financeiro.recurring_expense_alerts.length === 0 ? (
                    <p className="py-2 text-sm text-muted">Nenhuma conta pendente.</p>
                  ) : (
                    <ListaTruncada>
                      {data.financeiro.recurring_expense_alerts.map((alert) => (
                        <div
                          key={alert.name}
                          className="flex items-center justify-between gap-3 border-b border-line py-2 text-sm last:border-b-0"
                        >
                          <span className="text-ink">
                            {alert.name} (dia {alert.due_day})
                          </span>
                          <div className="flex items-center gap-3">
                            {alert.amount != null && (
                              <span className="tabular-nums text-ink">R$ {formatBRL(alert.amount)}</span>
                            )}
                            <Button asChild variant="outline" size="sm" className="shrink-0">
                              <a href="/gastos/recorrentes" target="_blank" rel="noopener">
                                Abrir
                              </a>
                            </Button>
                          </div>
                        </div>
                      ))}
                    </ListaTruncada>
                  )}
                </SectorPanel>
              </div>
            )}
          </div>

          {!data.casting &&
            !data.figurino &&
            !data.figurino_producao &&
            !data.figurino_oficina &&
            !data.ensaio &&
            !data.comercial &&
            !data.formularios &&
            !data.financeiro && (
              <Card>
                <CardContent className="p-5">
                  <p className="text-sm text-muted">Tudo em dia! ✓</p>
                </CardContent>
              </Card>
            )}

          {user?.is_superadmin && data.dismissed_casting.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Cargos dispensados</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted">
                  {data.dismissed_casting.length} cargo(s) marcados como dispensados.
                </p>
              </CardContent>
            </Card>
          )}
        </motion.div>
      )}
    </div>
  );
}
