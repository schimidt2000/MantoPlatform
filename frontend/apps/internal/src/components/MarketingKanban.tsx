import { useRef, useState, type RefObject } from "react";
import {
  AnimatePresence,
  LayoutGroup,
  motion,
  useReducedMotion,
  type PanInfo,
} from "framer-motion";
import { ChevronLeft, ChevronRight, FolderOpen, GripVertical, Plus } from "lucide-react";
import { AvatarThumb, Badge, Button, cn } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  daysUntil,
  formatMarketingDate,
  MARKETING_STATUS_ICONS,
  MARKETING_STATUS_LABELS,
  MARKETING_STATUSES,
  MARKETING_STATUS_TONES,
  REVIEW_SPACE_STATUS_LABELS,
  REVIEW_SPACE_STATUS_TONES,
  useMoveMarketingPost,
  type MarketingPost,
  type MarketingStatus,
} from "../lib/marketing";
import { attributeAtPoint, viewportPoint } from "../lib/pointerDrag";

/** Duração das transições do quadro — dentro da faixa de 150–350ms do Princípio IX. */
const MOVE_TRANSITION = { duration: 0.28, ease: "easeOut" } as const;

/** Atributo que marca a área de soltura de cada coluna (lido no hit-test do drop). */
const STATUS_ATTR = "data-kanban-status";

/** Coluna sob o ponteiro, pelo empilhamento real de elementos (ver `lib/pointerDrag`). */
function statusAtPoint(x: number, y: number): MarketingStatus | null {
  const status = attributeAtPoint(STATUS_ATTR, x, y);
  return status && (MARKETING_STATUSES as string[]).includes(status)
    ? (status as MarketingStatus)
    : null;
}

/** Selo de urgência do prazo — mesma leitura de relance da Fila de Impressão 3D. */
function DeadlineBadge({ deadline }: { deadline: string | null }) {
  const days = daysUntil(deadline);
  if (days === null) return null;
  if (days < 0) return <Badge tone="red">Atrasado {Math.abs(days)}d</Badge>;
  if (days === 0) return <Badge tone="red">Hoje</Badge>;
  if (days <= 3) return <Badge tone="gold">Em {days}d</Badge>;
  return <Badge tone="neutral">Em {days}d</Badge>;
}

interface KanbanCardProps {
  post: MarketingPost;
  onOpen: () => void;
  /** Limite do arraste: o card não escapa do quadro (que tem `overflow-x-auto` e recortaria). */
  boardRef: RefObject<HTMLDivElement>;
  /** Coluna sob o ponteiro durante o arraste — só para o realce; `null` encerra o arraste. */
  onDragOver: (status: MarketingStatus | null) => void;
  onDraggingChange: (postId: number | null) => void;
}

/**
 * Card de uma postagem no quadro — arrastável entre as colunas.
 *
 * Duas formas de mover, de propósito: **arrastar** (mouse/toque) e as **setas ◀ ▶** (teclado e
 * telas estreitas, onde arrastar disputa com a rolagem). Nenhuma delas espera a API: a mutação é
 * otimista, então o card já aparece na coluna nova (Princípio V).
 *
 * O `layoutId` é o coração da animação (Princípio IX): quando o status muda, o card **desmonta**
 * de uma coluna e **monta** na outra, e o Framer Motion interpola a posição entre as duas — no
 * drop, isso faz o card sair de onde a mão o deixou e assentar no lugar novo. Com
 * `useReducedMotion()` ativo, a animação de layout é desligada e a troca é instantânea.
 */
function KanbanCard({
  post,
  onOpen,
  boardRef,
  onDragOver,
  onDraggingChange,
}: KanbanCardProps) {
  const reduceMotion = useReducedMotion();
  const move = useMoveMarketingPost();
  // Distingue "clique no card" (abre o Dialog) de "arrastei o card" (move) — sem isso, todo
  // arraste terminaria abrindo o Dialog no `click` que vem depois do `pointerup`.
  const dragged = useRef(false);
  const index = MARKETING_STATUSES.indexOf(post.status);
  const previous = index > 0 ? MARKETING_STATUSES[index - 1] : null;
  const next = index < MARKETING_STATUSES.length - 1 ? MARKETING_STATUSES[index + 1] : null;

  function moveTo(status: MarketingStatus, event: React.MouseEvent) {
    event.stopPropagation();
    move.mutate({ id: post.id, status });
  }

  function handleDragEnd(event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) {
    onDragOver(null);
    onDraggingChange(null);
    const point = viewportPoint(event, info);
    const target = statusAtPoint(point.x, point.y);
    // Soltar fora de uma coluna, ou na mesma, não é uma mudança — o card volta sozinho
    // (`dragSnapToOrigin`) e nenhuma requisição é disparada.
    if (target && target !== post.status) {
      move.mutate({ id: post.id, status: target });
    }
  }

  return (
    <motion.li
      layoutId={`marketing-post-${post.id}`}
      layout={!reduceMotion}
      initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96 }}
      transition={MOVE_TRANSITION}
      drag
      dragSnapToOrigin
      dragElastic={0.12}
      dragMomentum={false}
      dragConstraints={boardRef}
      whileDrag={{ scale: 1.04, zIndex: 30, boxShadow: "0 12px 28px rgb(0 0 0 / 0.28)" }}
      onPointerDown={() => {
        dragged.current = false;
      }}
      onDragStart={() => {
        dragged.current = true;
        onDraggingChange(post.id);
      }}
      onDrag={(event, info) => {
        const point = viewportPoint(event, info);
        onDragOver(statusAtPoint(point.x, point.y));
      }}
      onDragEnd={handleDragEnd}
      className={cn(
        "cursor-grab rounded-lg border border-line bg-panel p-2.5 shadow-sm active:cursor-grabbing",
        move.isPending && "opacity-70",
      )}
    >
      {/* O card inteiro abre o Dialog e também é a alça de arraste; as setas param a propagação. */}
      <button
        type="button"
        onClick={() => {
          if (dragged.current) return;
          onOpen();
        }}
        aria-label={`Abrir postagem ${post.title}`}
        className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex items-start gap-2">
          {post.catalog_items[0] && (
            <AvatarThumb
              src={assetUrl(post.catalog_items[0].cover_url)}
              name={post.catalog_items[0].name}
              shape="square"
              size="md"
              fallbackIcon="🎭"
            />
          )}
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold leading-snug text-ink">{post.title}</span>
            {post.catalog_items.length > 0 && (
              <span className="block truncate text-xs text-muted">
                {post.catalog_items.map((item) => item.name).join(", ")}
              </span>
            )}
          </span>
          <GripVertical className="h-4 w-4 flex-none text-muted/60" aria-hidden="true" />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {post.platform && <Badge tone="accent">{post.platform.toUpperCase()}</Badge>}
          <DeadlineBadge deadline={post.deadline_date} />
          {post.review_space && (
            <Badge tone={REVIEW_SPACE_STATUS_TONES[post.review_space.status]}>
              {REVIEW_SPACE_STATUS_LABELS[post.review_space.status].toUpperCase()}
            </Badge>
          )}
          {post.drive_folder_url && (
            <FolderOpen className="h-3.5 w-3.5 text-gold" aria-label="Tem acervo no Drive" />
          )}
        </div>

        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-1.5">
            {post.assignee ? (
              <>
                <AvatarThumb
                  src={assetUrl(post.assignee.photo_url)}
                  name={post.assignee.name}
                  shape="circle"
                  size="sm"
                />
                <span className="truncate text-xs text-muted">{post.assignee.name}</span>
              </>
            ) : (
              <span className="text-xs text-muted">Sem responsável</span>
            )}
          </span>
          {post.publish_date && (
            <span className="shrink-0 text-xs text-muted">
              {post.status === "publicado" ? "Publicado" : "Publica"}{" "}
              {formatMarketingDate(post.publish_date)}
            </span>
          )}
        </div>
      </button>

      <div className="mt-2 flex items-center justify-between border-t border-line pt-1.5">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-1.5"
          disabled={!previous || move.isPending}
          aria-label={
            previous ? `Mover para ${MARKETING_STATUS_LABELS[previous]}` : "Já está na primeira etapa"
          }
          onClick={(event) => previous && moveTo(previous, event)}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        {move.isError && <span className="text-[11px] text-red">Erro ao mover</span>}
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-1.5"
          disabled={!next || move.isPending}
          aria-label={next ? `Mover para ${MARKETING_STATUS_LABELS[next]}` : "Já está na última etapa"}
          onClick={(event) => next && moveTo(next, event)}
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </motion.li>
  );
}

export interface MarketingKanbanProps {
  posts: MarketingPost[];
  onOpenPost: (post: MarketingPost) => void;
  /** Abre o Dialog de criação já com a coluna clicada pré-selecionada. */
  onCreateInColumn: (status: MarketingStatus) => void;
}

/**
 * Quadro Kanban do planejamento de marketing (feature 204).
 *
 * Uma coluna por status. O card muda de coluna **arrastando** ou pelas setas, sempre com
 * atualização otimista (`useMoveMarketingPost`), então o movimento começa no gesto e não espera a
 * API. O `LayoutGroup` mantém as animações de `layoutId` coordenadas entre as colunas.
 *
 * A rolagem horizontal fica **dentro** do quadro (`overflow-x-auto`), nunca na página — por isso o
 * arraste é limitado ao próprio quadro (`dragConstraints`): fora dele o card seria recortado.
 */
export function MarketingKanban({ posts, onOpenPost, onCreateInColumn }: MarketingKanbanProps) {
  const boardRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState<MarketingStatus | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const draggingPost = posts.find((post) => post.id === draggingId) ?? null;

  return (
    <LayoutGroup>
      <div
        ref={boardRef}
        className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-2"
        // Enquanto o card está no ar, o quadro deixa de rolar por toque: a rolagem competiria
        // com o gesto de arrastar e o card "escaparia" da mão.
        style={draggingId !== null ? { touchAction: "none" } : undefined}
      >
        {MARKETING_STATUSES.map((status) => {
          const columnPosts = posts.filter((post) => post.status === status);
          // Realce só quando soltar ali de fato muda algo — a coluna de origem não pisca.
          const isDropTarget =
            draggingPost !== null && dragOver === status && draggingPost.status !== status;
          return (
            <section
              key={status}
              {...{ [STATUS_ATTR]: status }}
              className={cn(
                "flex w-[264px] shrink-0 flex-col rounded-lg border p-2 transition-colors",
                isDropTarget
                  ? "border-accent bg-accent-soft/60 ring-2 ring-accent/40"
                  : "border-line bg-surface-2/50",
              )}
              aria-label={`Coluna ${MARKETING_STATUS_LABELS[status]}`}
            >
              <header className="mb-2 flex items-center justify-between gap-2 px-0.5">
                <h3 className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
                  <span aria-hidden="true">{MARKETING_STATUS_ICONS[status]}</span>
                  {MARKETING_STATUS_LABELS[status]}
                  <Badge tone={MARKETING_STATUS_TONES[status]}>{columnPosts.length}</Badge>
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  aria-label={`Nova postagem em ${MARKETING_STATUS_LABELS[status]}`}
                  onClick={() => onCreateInColumn(status)}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                </Button>
              </header>

              <ul className="flex min-h-[120px] flex-1 flex-col gap-2">
                {/* `mode` fica no padrão ("sync"): `popLayout` exigiria que `KanbanCard`
                    encaminhasse a `ref` (o wrapper `PopChild` do Framer a injeta no filho
                    direto), e o card é um componente de função. */}
                <AnimatePresence initial={false}>
                  {columnPosts.map((post) => (
                    <KanbanCard
                      key={post.id}
                      post={post}
                      onOpen={() => onOpenPost(post)}
                      boardRef={boardRef}
                      onDragOver={setDragOver}
                      onDraggingChange={setDraggingId}
                    />
                  ))}
                </AnimatePresence>
                {columnPosts.length === 0 && (
                  <li
                    className={cn(
                      "rounded-md border border-dashed px-2 py-4 text-center text-xs transition-colors",
                      isDropTarget ? "border-accent text-accent" : "border-line text-muted",
                    )}
                  >
                    {isDropTarget ? "Solte aqui" : "Nada aqui ainda"}
                  </li>
                )}
              </ul>
            </section>
          );
        })}
      </div>
      <p className="mt-1 px-1 text-[11px] text-muted">
        Arraste um card para outra coluna, ou use as setas ◀ ▶ do próprio card.
      </p>
    </LayoutGroup>
  );
}
