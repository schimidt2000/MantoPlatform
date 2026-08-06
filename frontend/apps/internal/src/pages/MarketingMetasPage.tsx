import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AlarmClock, CheckCircle2, Pencil, Target, Trash2 } from "lucide-react";
import { AvatarThumb, Badge, Button, Card, PageHeader, Skeleton, cn } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  formatMarketingDate,
  useDeleteMarketingGoal,
  useMarketingGoals,
  type MarketingGoal,
} from "../lib/marketing";
import { MarketingGoalDialog } from "../components/MarketingGoalDialog";

/** Percentual do intervalo já consumido — passa de 100% quando a meta estourou o prazo. */
function usedPercent(goal: MarketingGoal): number {
  if (goal.days_since_last_post === null) return 100;
  const ratio = (goal.days_since_last_post / goal.target_interval_days) * 100;
  return Math.min(100, Math.max(0, Math.round(ratio)));
}

/** Frase de urgência do card — é o que a tela precisa dizer em uma linha. */
function urgencyText(goal: MarketingGoal): string {
  if (goal.never_posted) return "Nenhum post publicado ainda — precisa de conteúdo urgente.";
  if (goal.status === "delayed") {
    return `Atrasado ${goal.days_late} dia(s) além do intervalo combinado.`;
  }
  const restam = goal.target_interval_days - (goal.days_since_last_post ?? 0);
  if (restam <= 0) return "Vence hoje — vale adiantar o próximo post.";
  return `Em dia — próximo post em ${restam} dia(s).`;
}

interface GoalCardProps {
  goal: MarketingGoal;
  onEdit: () => void;
}

/**
 * Card de saúde de uma meta.
 *
 * O estado aparece três vezes de propósito (cor da borda, selo e barra de consumo): quem abre a
 * tela precisa achar o que está atrasado sem ler nada — e nada depende **só** da cor (há ícone e
 * texto), para não excluir quem não distingue vermelho de verde.
 */
function GoalCard({ goal, onEdit }: GoalCardProps) {
  const deleteGoal = useDeleteMarketingGoal();
  const [confirming, setConfirming] = useState(false);
  const delayed = goal.status === "delayed";
  const percent = usedPercent(goal);

  return (
    <Card
      className={cn(
        "space-y-3 p-4",
        delayed ? "border-red/50 bg-red-soft/30" : "border-green/40 bg-green-soft/20",
      )}
    >
      <div className="flex items-start gap-3">
        {goal.catalog_item ? (
          <AvatarThumb
            src={assetUrl(goal.catalog_item.cover_url)}
            name={goal.catalog_item.name}
            shape="square"
            size="lg"
            fallbackIcon="🎭"
          />
        ) : (
          <span className="flex h-12 w-12 flex-none items-center justify-center rounded-md bg-surface-2 text-muted">
            <Target className="h-5 w-5" aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-ink">{goal.name}</h3>
          <p className="text-xs text-muted">
            Meta: postar a cada <strong className="text-ink">{goal.target_interval_days}</strong>{" "}
            dias
            {goal.catalog_item ? ` · Tema ${goal.catalog_item.name}` : " · sem Tema vinculado"}
          </p>
        </div>
        <Badge tone={delayed ? "red" : "green"} className="shrink-0 gap-1 px-2 py-1 text-[11px]">
          {delayed ? (
            <AlarmClock className="h-3 w-3" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
          )}
          {goal.never_posted ? "SEM POSTS" : delayed ? `ATRASADO ${goal.days_late}D` : "EM DIA"}
        </Badge>
      </div>

      <p className={cn("text-sm font-medium", delayed ? "text-red" : "text-green")}>
        {urgencyText(goal)}
      </p>

      {/* Barra de consumo do intervalo: cheia e vermelha = passou do prazo combinado. */}
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={`Intervalo consumido da meta ${goal.name}`}
      >
        <div
          className={cn("h-full rounded-full", delayed ? "bg-red" : "bg-green")}
          style={{ width: `${percent}%` }}
        />
      </div>

      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <div>
          <dt className="text-muted">Último post</dt>
          <dd className="font-medium text-ink">
            {goal.never_posted ? "—" : formatMarketingDate(goal.last_posted_date)}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Próximo previsto</dt>
          <dd className="font-medium text-ink">
            {goal.never_posted ? "Assim que possível" : formatMarketingDate(goal.next_due_date)}
          </dd>
        </div>
      </dl>

      {confirming ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-2">
          <span className="mr-auto text-xs text-ink">Excluir esta meta?</span>
          <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
            Cancelar
          </Button>
          <Button
            size="sm"
            // `on-color`: o vermelho clareia no tema escuro e o branco cai para 2.78:1.
            className="bg-red text-on-color hover:bg-red/90"
            loading={deleteGoal.isPending}
            onClick={() => deleteGoal.mutate(goal.id)}
          >
            Excluir
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2 border-t border-line pt-2">
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Editar
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-red hover:bg-red-soft"
            onClick={() => setConfirming(true)}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            Excluir
          </Button>
          {deleteGoal.isError && (
            <span className="text-xs text-red" role="alert">
              Erro ao excluir
            </span>
          )}
        </div>
      )}
    </Card>
  );
}

/** Ordena o dashboard por urgência: sem posts, depois mais atrasados, depois os em dia. */
function byUrgency(a: MarketingGoal, b: MarketingGoal): number {
  const score = (goal: MarketingGoal) =>
    goal.never_posted ? Number.MAX_SAFE_INTEGER : (goal.days_late ?? 0);
  const diff = score(b) - score(a);
  if (diff !== 0) return diff;
  return a.name.localeCompare(b.name, "pt-BR");
}

/**
 * Metas de Frequência (`/marketing/metas`, feature 204) — o "Health Dashboard".
 *
 * Lista as regras combinadas em reunião ("15 Anos a cada 15 dias") e responde de relance a
 * pergunta que importa: **qual assunto está pedindo post agora**. O status é derivado no servidor
 * a partir dos posts já publicados (`marketing_ops.goal_health`) — mover um card do Kanban para
 * "publicado" conserta a saúde da meta na hora.
 */
export function MarketingMetasPage() {
  const reduceMotion = useReducedMotion();
  const query = useMarketingGoals();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const goals = [...(query.data?.items ?? [])].sort(byUrgency);
  const delayed = query.data?.delayed_count ?? 0;
  const emDia = goals.length - delayed;
  // Mesma razão do painel: a meta vem do cache, para o Dialog nunca editar uma cópia velha.
  const editing = goals.find((goal) => goal.id === editingId) ?? null;

  function openCreate() {
    setEditingId(null);
    setDialogOpen(true);
  }

  function openEdit(goal: MarketingGoal) {
    setEditingId(goal.id);
    setDialogOpen(true);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Metas de Frequência"
        subtitle="A saúde de cada assunto: quem está em dia e quem está pedindo post."
        className="mb-0"
        actions={
          <Button size="sm" onClick={openCreate}>
            + Nova meta
          </Button>
        }
      />

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="h-48 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as metas de frequência.
        </div>
      )}

      {query.data && goals.length > 0 && (
        <motion.div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <div
            className={cn(
              "flex items-center gap-3 rounded-lg border p-4 sm:col-span-2",
              delayed > 0 ? "border-red/50 bg-red-soft/40" : "border-green/40 bg-green-soft/30",
            )}
          >
            <span className="text-3xl" aria-hidden="true">
              {delayed > 0 ? "🚨" : "✅"}
            </span>
            <div>
              <p className="text-lg font-semibold text-ink">
                {delayed > 0
                  ? `${delayed} assunto(s) precisando de post`
                  : "Todos os assuntos em dia"}
              </p>
              <p className="text-xs text-muted">
                {emDia} em dia · {goals.length} meta(s) acompanhada(s)
              </p>
            </div>
          </div>

          <AnimatePresence initial={false} mode="popLayout">
            {goals.map((goal) => (
              <motion.div
                key={goal.id}
                layout={!reduceMotion}
                initial={reduceMotion ? false : { opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.24, ease: "easeOut" }}
              >
                <GoalCard goal={goal} onEdit={() => openEdit(goal)} />
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {query.data && goals.length === 0 && (
        <p className="text-sm text-muted">
          Nenhuma meta cadastrada. Crie a primeira regra (ex.: “Festa de 15 Anos a cada 15 dias”)
          para o painel começar a acompanhar a frequência.
        </p>
      )}

      <MarketingGoalDialog
        goal={editing}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  );
}
