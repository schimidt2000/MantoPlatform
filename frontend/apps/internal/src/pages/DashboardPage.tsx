import { useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { apiFetch } from "@manto/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricBadge,
  PageHeader,
  Skeleton,
  formatShortDate,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import { PORTAL_PUBLICO } from "../lib/eventDetail";
import { useCurrentUser } from "../lib/useAuth";
import type {
  ComercialSummary,
  DashboardSummary,
  DashboardTaskRef,
  EnsaioEventRef,
  EnsaioSummary,
  FormulariosSummary,
  LinhaFormulario,
  MinhaPecaRef,
  PendingPayment,
  SemValorSummary,
  UnconfirmedInviteRef,
} from "../lib/types";
import { SEVERIDADE_TOM, diaMes, distanciaDaData } from "../lib/homeListas";
import { BotaoMostrarTodas, GrupoDeLinhas, LIMITE_LINHAS_PAINEL, PanelGroup } from "../components/home/GrupoDeLinhas";
import { LinhaDaHome } from "../components/home/LinhaDaHome";
import { PainelCobrancas } from "../components/home/PainelCobrancas";
import { PainelSemValor } from "../components/home/PainelSemValor";
import { SectorPanel, getUrgency } from "../components/SectorPanel";
import { EncerrarFormularioDialog } from "../components/formularios/EncerrarFormularioDialog";
import { SugestaoDeEventoFaixa } from "../components/formularios/SugestaoDeEventoFaixa";
import {
  mensagemDaApi,
  useManterEntreRepetidos,
  useUsarClienteDoEvento,
  type DivergenciaCliente,
  type ResultadoVinculo,
} from "../lib/formulariosAdmin";
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
function UnconfirmedRow({ item }: { item: UnconfirmedInviteRef }) {
  const urgency = getUrgency(item.start_at);
  const nuncaEnviado = item.invite_status !== "pending";
  // Endereço FIXO do portal (feature 269), não o `portal_url` da API: esta mensagem é copiada e
  // enviada por WhatsApp a um talento de fora. Vindo da env, quem rodasse o ambiente local
  // mandava `http://localhost:5000/` para uma pessoa real, e sem a env a mensagem saía sem link.
  const zap = item.whatsapp
    ? `https://wa.me/${item.whatsapp.replace(/\D/g, "")}?text=${encodeURIComponent(
        `Oi, ${item.talent_name}! Falta você confirmar no portal a sua presença em "${item.event_title}". Consegue responder por lá? ${PORTAL_PUBLICO}`,
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
      <BotaoMostrarTodas
        expandida={expandida}
        total={children.length}
        onClick={() => setExpandida((v) => !v)}
      />
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

// ── Formulários sem evento na agenda (feature 298) ─────────────────────────────
// A escala de cor, o `diaMes` e a distância em palavras moram em `lib/homeListas.ts` desde a
// 299: as três listas comerciais (Formulários, Cobranças e Sem valor) usam as mesmas peças.

function chegouHa(dias: number | undefined): string {
  if (dias == null) return "";
  if (dias <= 0) return "chegou hoje";
  return `chegou há ${dias} dia${dias !== 1 ? "s" : ""}`;
}

/**
 * Uma linha da lista: quem, quando e uma ação (feature 298).
 *
 * Mesma estrutura das outras linhas da Home. Em tela estreita o conteúdo quebra em duas linhas e o
 * botão desce, sem rolagem horizontal — a ação principal fica sempre à mostra.
 */
function FormularioSemDestinoRow({
  linha,
  podeCriarEvento,
  onEncerrar,
  onLigado,
}: {
  linha: LinhaFormulario;
  podeCriarEvento: boolean;
  /** Ausente quando o servidor não mandou os motivos (versão antiga no meio do deploy). */
  onEncerrar?: () => void;
  onLigado?: (resultado: ResultadoVinculo, formularioId: number) => void;
}) {
  const severidade = linha.severidade ?? "cinza";
  const nome = linha.cliente?.nome ?? linha.nome_no_formulario ?? "Sem nome";
  // Data suspeita (ex.: 2049) não ganha distância: "em 8241 dias" é ruído — a marca já diz tudo.
  const distancia = linha.data_suspeita ? null : distanciaDaData(linha.dias_ate_a_data);
  const vezes = linha.formularios?.length ?? 1;
  const id = linha.representante_id;
  const [repetidosAbertos, setRepetidosAbertos] = useState(false);
  const reduceMotion = useReducedMotion();
  const detalhe = [linha.tipo_rotulo ?? "Formulário", chegouHa(linha.dias_desde_chegada)]
    .filter(Boolean)
    .join(" · ");

  return (
    <LinhaDaHome
      severidade={severidade}
      cabecalho={
        <>
          <span className="min-w-0 break-words">{nome}</span>
          {linha.data_informada ? (
            <span className="tabular-nums">{formatShortDate(linha.data_informada)}</span>
          ) : (
            <span className="font-normal text-muted">sem data informada</span>
          )}
          {distancia && (
            <MetricBadge tone={SEVERIDADE_TOM[severidade]} size="xs">
              {distancia}
            </MetricBadge>
          )}
          {/* Marcas numa ordem fixa, para o olho achar sempre no mesmo lugar. */}
          {linha.data_suspeita && (
            <MetricBadge tone="neutral" size="xs">
              data suspeita
            </MetricBadge>
          )}
          {linha.repetido && (
            <button
              type="button"
              onClick={() => setRepetidosAbertos((v) => !v)}
              aria-expanded={repetidosAbertos}
              className="cursor-pointer rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <MetricBadge tone="gold" size="xs">
                preencheu {vezes} vezes {repetidosAbertos ? "▴" : "▾"}
              </MetricBadge>
            </button>
          )}
          {linha.outro_com_evento && (
            <MetricBadge tone="neutral" size="xs">
              já tem outro formulário com evento
            </MetricBadge>
          )}
        </>
      }
      detalhe={detalhe}
      acoes={
        <>
          {onEncerrar && (
            <Button type="button" variant="ghost" size="sm" onClick={onEncerrar}>
              Encerrar…
            </Button>
          )}
          <Button asChild variant={podeCriarEvento ? "default" : "outline"} size="sm">
            <Link to={podeCriarEvento ? `/events/new?form_response_id=${id}` : `/formularios?resposta=${id}`}>
              {podeCriarEvento ? "Criar evento" : "Abrir"}
            </Link>
          </Button>
        </>
      }
    >
      <AnimatePresence initial={false}>
        {linha.sugestao && (
          <SugestaoDeEventoFaixa
            key={linha.sugestao.event_id}
            formularioId={id}
            sugestao={linha.sugestao}
            onLigado={(resultado) => onLigado?.(resultado, id)}
          />
        )}
      </AnimatePresence>
      <AnimatePresence initial={false}>
        {linha.repetido && repetidosAbertos && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="basis-full overflow-hidden"
          >
            <RepetidosDaLinha linha={linha} />
          </motion.div>
        )}
      </AnimatePresence>
    </LinhaDaHome>
  );
}

/**
 * Os formulários da mesma cliente, cada um com "Este é o que vale" (feature 298). Escolher um
 * encerra os outros como "Repetido" — continuam guardados e dá para reabrir pela tela Formulários.
 */
function RepetidosDaLinha({ linha }: { linha: LinhaFormulario }) {
  const manter = useManterEntreRepetidos();
  return (
    <div className="pt-2">
      <ul className="space-y-1.5 border-l-2 border-line pl-3">
        {(linha.formularios ?? []).map((f) => {
          const escolhendoEste = manter.isPending && manter.variables === f.id;
          return (
            <li key={f.id} className="flex flex-wrap items-center justify-between gap-2">
              <span className="min-w-0 text-ink">
                {f.tipo_rotulo ?? "Formulário"} ·{" "}
                {f.data_informada ? formatShortDate(f.data_informada) : "sem data"}
                <span className="text-muted"> · {chegouHa(f.dias_desde_chegada)}</span>
              </span>
              <div className="flex shrink-0 items-center gap-1.5">
                <Button asChild variant="ghost" size="sm">
                  <Link to={`/formularios?resposta=${f.id}`}>Ver</Link>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  loading={escolhendoEste}
                  onClick={() => manter.mutate(f.id)}
                >
                  Este é o que vale
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      {manter.isError ? (
        <p role="alert" className="mt-1.5 text-xs text-red">
          {mensagemDaApi(manter.error, "Não foi possível encerrar os repetidos. Tente novamente.")}
        </p>
      ) : (
        <p className="mt-1.5 text-xs text-muted">
          Os outros são encerrados como “Repetido” e continuam guardados.
        </p>
      )}
    </div>
  );
}

/**
 * Um grupo do painel ("ainda vai chegar" / "já passou"). O corte em 6 linhas, o "Mostrar todas" e
 * a saída animada da linha resolvida são do `GrupoDeLinhas`, que a 299 extraiu daqui para as listas
 * de Cobranças e Sem valor usarem o mesmo.
 */
function GrupoFormularios({
  titulo,
  linhas,
  podeCriarEvento,
  onEncerrar,
  onLigado,
}: {
  titulo: string;
  linhas: LinhaFormulario[];
  podeCriarEvento: boolean;
  onEncerrar?: (linha: LinhaFormulario) => void;
  onLigado?: (resultado: ResultadoVinculo, formularioId: number) => void;
}) {
  return (
    <GrupoDeLinhas titulo={titulo} itens={linhas} chave={(linha) => linha.representante_id}>
      {(linha) => (
        <FormularioSemDestinoRow
          linha={linha}
          podeCriarEvento={podeCriarEvento}
          onEncerrar={onEncerrar ? () => onEncerrar(linha) : undefined}
          onLigado={onLigado}
        />
      )}
    </GrupoDeLinhas>
  );
}

/**
 * "📝 Formulários sem evento na agenda" (feature 298): os formulários que chegaram desde o corte e
 * ainda não viraram evento nem foram encerrados. Substitui os quatro números da 266, que contavam
 * o histórico importado.
 */
function FormulariosPanel({
  summary,
  urgentCount,
  open,
  onOpenChange,
}: {
  summary: FormulariosSummary;
  urgentCount: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const aChegar = summary.a_chegar ?? [];
  const jaPassou = summary.ja_passou ?? [];
  const podeCriarEvento = summary.pode_criar_evento ?? false;
  const desde = diaMes(summary.contagens?.corte);
  const motivos = summary.motivos_encerramento ?? [];
  const [encerrando, setEncerrando] = useState<LinhaFormulario | null>(null);
  // Sem motivos (servidor antigo no meio do deploy) a ação não aparece em vez de abrir vazia.
  const aoEncerrar = motivos.length > 0 ? setEncerrando : undefined;
  // A linha ligada sai da lista; a divergência de cliente precisa sobreviver a ela, então mora
  // aqui no painel e não na linha.
  const [divergente, setDivergente] = useState<{
    formularioId: number;
    divergencia: DivergenciaCliente;
  } | null>(null);
  const usarCliente = useUsarClienteDoEvento();
  const aoLigar = (resultado: ResultadoVinculo, formularioId: number) => {
    if (resultado.divergencia_cliente) {
      setDivergente({ formularioId, divergencia: resultado.divergencia_cliente });
    }
  };

  return (
    <SectorPanel
      title="📝 Formulários sem evento na agenda"
      count={summary.contagens?.sem_destino ?? 0}
      urgentCount={urgentCount}
      open={open}
      onOpenChange={onOpenChange}
    >
      {divergente && (
        <div role="status" className="mb-3 space-y-2 rounded-md bg-gold-50 px-3 py-2 text-sm text-ink">
          <p>
            Formulário ligado. A cliente do formulário (
            <strong>{divergente.divergencia.formulario.nome ?? "sem nome"}</strong>) não é a cliente
            do evento (<strong>{divergente.divergencia.evento.nome ?? "sem nome"}</strong>) — o evento
            não foi alterado.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              loading={usarCliente.isPending}
              onClick={() =>
                usarCliente.mutate(divergente.formularioId, { onSuccess: () => setDivergente(null) })
              }
            >
              Usar a cliente do evento neste formulário
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                usarCliente.reset();
                setDivergente(null);
              }}
            >
              Manter assim
            </Button>
          </div>
          {usarCliente.isError && (
            <p role="alert" className="text-xs text-red">
              {mensagemDaApi(usarCliente.error, "Não foi possível trocar a cliente. Tente novamente.")}
            </p>
          )}
        </div>
      )}
      {aChegar.length === 0 && jaPassou.length === 0 ? (
        <p className="py-2 text-sm text-muted">Nenhum formulário esperando evento ✓</p>
      ) : (
        <div className="space-y-3">
          {aChegar.length > 0 && (
            <GrupoFormularios
              titulo="A data informada ainda vai chegar"
              linhas={aChegar}
              podeCriarEvento={podeCriarEvento}
              onEncerrar={aoEncerrar}
              onLigado={aoLigar}
            />
          )}
          {jaPassou.length > 0 && (
            <GrupoFormularios
              titulo="A data informada já passou"
              linhas={jaPassou}
              podeCriarEvento={podeCriarEvento}
              onEncerrar={aoEncerrar}
              onLigado={aoLigar}
            />
          )}
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        {desde && <p className="text-xs text-muted">Formulários que chegaram desde {desde}.</p>}
        <Button asChild variant="outline" size="sm">
          <Link to="/formularios">Abrir formulários</Link>
        </Button>
      </div>
      <EncerrarFormularioDialog
        formularioId={encerrando?.representante_id ?? null}
        nome={encerrando?.cliente?.nome ?? encerrando?.nome_no_formulario}
        motivos={motivos}
        open={encerrando !== null}
        onClose={() => setEncerrando(null)}
      />
    </SectorPanel>
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
  | "sem_valor"
  | "formularios"
  | "recorrentes";

interface SectionStat extends HomeOverviewItem {
  key: SectionKey;
  /**
   * Quanto esta seção soma em "N pendências no total" (feature 299). Nas listas comerciais é o
   * `para_agir` (vermelho + amarelo), o mesmo número do card; nos painéis de operação, `count`.
   */
  noTotal?: number;
  /** A lista não carregou: card sem ✓ e o topo avisa, em vez de dizer "Tudo em dia". */
  falhou?: boolean;
}

/** Linha vermelha de Cobranças — com o servidor antigo (sem `severidade`), pela `severity`. */
function cobrancaVermelha(p: PendingPayment): boolean {
  if (p.severidade) return p.severidade === "vermelho";
  return p.severity === "atrasado" || p.severity === "vencido" || p.severity === "urgent";
}

/** Card de lista comercial que não carregou (FR-032): 0, sem ✓ e fora do total. */
function cardEmFalha(key: SectionKey, emoji: string, label: string): SectionStat {
  return { key, emoji, label, count: 0, urgent: 0, noTotal: 0, emDia: false, falhou: true, detail: "Não carregou" };
}

/** Linhas do painel "Sem valor" (os dois grupos); 0 quando a lista falhou. */
function totalSemValor(resumo: SemValorSummary | null | undefined): number {
  return resumo ? resumo.a_acontecer.length + resumo.ja_aconteceu.length : 0;
}

/**
 * Cards "Cobranças" e "Sem valor" (feature 299). O número é o de linhas para agir (vermelho +
 * amarelo), o mesmo que soma no total; o painel aberto mostra todas. Com o servidor antigo (sem
 * `cobrancas_resumo`), a conta de antes; sem `sem_valor`, não há card.
 */
function statsComerciais(c: ComercialSummary): SectionStat[] {
  const stats: SectionStat[] = [];
  const pagamentos = c.pending_payments;
  const resumo = c.cobrancas_resumo;
  if (resumo === null) {
    stats.push(cardEmFalha("comercial", "💼", "Cobranças"));
  } else {
    const count = resumo?.para_agir ?? pagamentos.length;
    const emAberto = resumo?.total_em_aberto ?? pagamentos.reduce((soma, p) => soma + p.saldo, 0);
    stats.push({
      key: "comercial",
      emoji: "💼",
      label: "Cobranças",
      count,
      noTotal: count,
      urgent: pagamentos.filter(cobrancaVermelha).length,
      emDia: resumo ? pagamentos.length === 0 : undefined,
      detail: pagamentos.length > 0 ? `R$ ${formatBRL(emAberto)} em aberto` : null,
    });
  }
  if (c.sem_valor === null) {
    stats.push(cardEmFalha("sem_valor", "🏷️", "Sem valor"));
  } else if (c.sem_valor) {
    const total = totalSemValor(c.sem_valor);
    const desde = diaMes(c.corte);
    const vermelhas = [...c.sem_valor.a_acontecer, ...c.sem_valor.ja_aconteceu].filter(
      (l) => l.severidade === "vermelho",
    );
    stats.push({
      key: "sem_valor",
      emoji: "🏷️",
      label: "Sem valor",
      count: c.sem_valor.para_agir,
      noTotal: c.sem_valor.para_agir,
      urgent: vermelhas.length,
      emDia: total === 0,
      detail:
        total > 0
          ? `${total} evento${total !== 1 ? "s" : ""} sem valor${desde ? ` desde ${desde}` : ""}`
          : null,
    });
  }
  return stats;
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
    stats.push(...statsComerciais(data.comercial));
  }

  if (data.formularios) {
    const f = data.formularios;
    const semDestino = f.contagens?.sem_destino ?? 0;
    const desde = diaMes(f.contagens?.corte);
    // Urgente = os formulários das linhas vermelhas (data informada a até 7 dias). Conta
    // formulários, não linhas, para bater com o número do painel.
    const urgentes = [...(f.a_chegar ?? []), ...(f.ja_passou ?? [])]
      .filter((l) => l.severidade === "vermelho")
      .reduce((soma, l) => soma + (l.formularios?.length ?? 1), 0);
    // Feature 299: o card (e a parte do total) conta as LINHAS para agir, vermelhas e amarelas —
    // as cinza são informação. Servidor antigo (sem `para_agir`): os formulários sem destino.
    const paraAgir = f.para_agir ?? semDestino;
    stats.push({
      key: "formularios",
      emoji: "📝",
      label: "Formulários",
      count: paraAgir,
      noTotal: paraAgir,
      emDia: f.para_agir !== undefined ? semDestino === 0 : undefined,
      urgent: urgentes,
      detail:
        semDestino > 0 && desde
          ? `${semDestino} formulário${semDestino !== 1 ? "s" : ""} sem evento desde ${desde}`
          : null,
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
  // "N pendências no total" (feature 299): das listas comerciais, só o que é para agir; dos painéis
  // de operação, tudo, como antes. É a soma dos números dos cards.
  const totalPendencias = stats.reduce((soma, s) => soma + (s.noTotal ?? s.count), 0);
  const totalUrgentes = stats.reduce((soma, s) => soma + s.urgent, 0);
  const algumaFalhou = stats.some((s) => s.falhou);
  const tentarDeNovo = () => {
    void dashboard.refetch();
  };

  // Abertura dos painéis: escolha explícita da pessoa vence; sem escolha, nasce aberto só quem
  // tem item urgente — é a triagem que devolve a Home legível no celular.
  const [abertos, setAbertos] = useState<Partial<Record<SectionKey, boolean>>>({});
  // A lista que não carregou também nasce aberta (feature 299, FR-032): o aviso com "Tentar de
  // novo" não pode ficar escondido atrás de um painel fechado.
  const painelAberto = (key: SectionKey) => {
    const stat = statPorSecao.get(key);
    return abertos[key] ?? ((stat?.urgent ?? 0) > 0 || Boolean(stat?.falhou));
  };
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
                {totalPendencias > 0 || algumaFalhou ? (
                  <>
                    <span>
                      {totalPendencias} pendência{totalPendencias !== 1 ? "s" : ""} no total
                    </span>
                    {totalUrgentes > 0 && (
                      <span className="rounded-full bg-red-soft px-2 py-0.5 font-medium text-red">
                        {totalUrgentes} urgente{totalUrgentes !== 1 ? "s" : ""}
                      </span>
                    )}
                    {/* Uma lista que não carregou não pode virar "Tudo em dia ✓" (FR-032). */}
                    {algumaFalhou && (
                      <span className="rounded-full bg-red-soft px-2 py-0.5 font-medium text-red">
                        uma lista não carregou
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

            {/* Feature 299: o painel "Comercial" virou dois, "Cobranças" e "Sem valor", cada um
                com o nome do seu card. O contador do painel aberto mostra todas as linhas. */}
            {data.comercial && (
              <div {...propsSecao("comercial")}>
                <SectorPanel
                  title="💼 Cobranças"
                  count={data.comercial.pending_payments.length}
                  falhou={statPorSecao.get("comercial")?.falhou}
                  urgentCount={statPorSecao.get("comercial")?.urgent ?? 0}
                  open={painelAberto("comercial")}
                  onOpenChange={aoAlternar("comercial")}
                >
                  <PainelCobrancas
                    linhas={data.comercial.pending_payments}
                    resumo={data.comercial.cobrancas_resumo}
                    onTentarDeNovo={tentarDeNovo}
                    tentando={dashboard.isFetching}
                  />
                </SectorPanel>
              </div>
            )}

            {/* `undefined` = servidor antigo (sem painel); `null` = a lista falhou (aviso). */}
            {data.comercial && data.comercial.sem_valor !== undefined && (
              <div {...propsSecao("sem_valor")}>
                <SectorPanel
                  title="🏷️ Sem valor"
                  count={totalSemValor(data.comercial.sem_valor)}
                  falhou={statPorSecao.get("sem_valor")?.falhou}
                  urgentCount={statPorSecao.get("sem_valor")?.urgent ?? 0}
                  open={painelAberto("sem_valor")}
                  onOpenChange={aoAlternar("sem_valor")}
                >
                  <PainelSemValor
                    resumo={data.comercial.sem_valor}
                    corte={data.comercial.corte}
                    podeEditarVenda={data.comercial.pode_editar_venda ?? false}
                    onTentarDeNovo={tentarDeNovo}
                    tentando={dashboard.isFetching}
                  />
                </SectorPanel>
              </div>
            )}

            {data.formularios && (
              <div {...propsSecao("formularios")}>
                <FormulariosPanel
                  summary={data.formularios}
                  urgentCount={statPorSecao.get("formularios")?.urgent ?? 0}
                  open={painelAberto("formularios")}
                  onOpenChange={aoAlternar("formularios")}
                />
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
