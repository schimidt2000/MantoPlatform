import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { KanbanSquare, Table2 } from "lucide-react";
import {
  AvatarThumb,
  Badge,
  Button,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
  cn,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  formatMarketingDate,
  MARKETING_STATUS_ICONS,
  MARKETING_STATUS_LABELS,
  MARKETING_STATUS_TONES,
  REVIEW_SPACE_STATUS_LABELS,
  REVIEW_SPACE_STATUS_TONES,
  useMarketingPosts,
  type MarketingPost,
  type MarketingStatus,
} from "../lib/marketing";
import { MarketingKanban } from "../components/MarketingKanban";
import { MarketingPostDialog } from "../components/MarketingPostDialog";

type ViewMode = "kanban" | "tabela";

/** Mesma chave/estratégia de persistência da tela `/admin/catalogo` (feature 169). */
const VIEW_MODE_KEY = "manto_marketing_painel_view";

function loadViewMode(): ViewMode {
  const saved = window.localStorage.getItem(VIEW_MODE_KEY);
  return saved === "tabela" ? "tabela" : "kanban";
}

const VIEW_OPTIONS: { value: ViewMode; label: string; icon: typeof Table2 }[] = [
  { value: "kanban", label: "Kanban", icon: KanbanSquare },
  { value: "tabela", label: "Tabela", icon: Table2 },
];

/** Linha da visão em lista — densa de propósito: serve para varrer datas de publicação. */
function PostRow({ post, onOpen }: { post: MarketingPost; onOpen: () => void }) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          {post.catalog_item && (
            <AvatarThumb
              src={assetUrl(post.catalog_item.cover_url)}
              name={post.catalog_item.name}
              shape="square"
              size="md"
              fallbackIcon="🎭"
            />
          )}
          <div className="min-w-0">
            <div className="font-medium text-ink">{post.title}</div>
            {post.catalog_item && (
              <div className="text-[11px] text-muted">{post.catalog_item.name}</div>
            )}
          </div>
        </div>
      </TableCell>
      <TableCell>
        {post.assignee ? (
          <div className="flex items-center gap-1.5">
            <AvatarThumb
              src={assetUrl(post.assignee.photo_url)}
              name={post.assignee.name}
              shape="circle"
              size="sm"
            />
            <span className="text-ink">{post.assignee.name}</span>
          </div>
        ) : (
          <span className="text-muted">Sem responsável</span>
        )}
      </TableCell>
      <TableCell>{post.platform ?? <span className="text-muted">—</span>}</TableCell>
      <TableCell className="whitespace-nowrap">
        <Badge tone={MARKETING_STATUS_TONES[post.status]}>
          {MARKETING_STATUS_LABELS[post.status].toUpperCase()}
        </Badge>
      </TableCell>
      <TableCell className="whitespace-nowrap">{formatMarketingDate(post.deadline_date)}</TableCell>
      <TableCell className="whitespace-nowrap">{formatMarketingDate(post.publish_date)}</TableCell>
      <TableCell className="whitespace-nowrap">
        {post.review_space ? (
          <Link to={`/revisao/${post.review_space.id}`} className="hover:underline">
            <Badge tone={REVIEW_SPACE_STATUS_TONES[post.review_space.status]}>
              {REVIEW_SPACE_STATUS_LABELS[post.review_space.status].toUpperCase()}
            </Badge>
          </Link>
        ) : (
          <span className="text-muted">Sem revisão</span>
        )}
      </TableCell>
      <TableCell align="right">
        <Button variant="outline" size="sm" onClick={onOpen}>
          Abrir
        </Button>
      </TableCell>
    </TableRow>
  );
}

function PostsTable({
  posts,
  onOpenPost,
}: {
  posts: MarketingPost[];
  onOpenPost: (post: MarketingPost) => void;
}) {
  return (
    <div className="rounded-lg border border-line bg-panel">
      <Table className="min-w-[900px]">
        <thead>
          <TableRow head>
            <TableCell as="th">Postagem</TableCell>
            <TableCell as="th">Responsável</TableCell>
            <TableCell as="th">Plataforma</TableCell>
            <TableCell as="th">Status</TableCell>
            <TableCell as="th">Prazo</TableCell>
            <TableCell as="th">Publicação</TableCell>
            <TableCell as="th">Revisão</TableCell>
            <TableCell as="th" align="right">
              Ações
            </TableCell>
          </TableRow>
        </thead>
        <tbody>
          {posts.map((post) => (
            <PostRow key={post.id} post={post} onOpen={() => onOpenPost(post)} />
          ))}
        </tbody>
      </Table>
    </div>
  );
}

/**
 * Painel de Marketing (`/marketing/painel`, feature 204).
 *
 * Duas visões da mesma lista, alternadas por um seletor que **persiste em `localStorage`** (mesmo
 * padrão de `/admin/catalogo`): o **Kanban** para conduzir a produção (o card muda de coluna com
 * animação de `layoutId`) e a **tabela densa** para varrer datas de publicação. A troca de visão
 * é uma transição do Framer Motion que respeita `useReducedMotion()` (Princípio IX).
 */
export function MarketingPainelPage() {
  const reduceMotion = useReducedMotion();
  const [viewMode, setViewModeState] = useState<ViewMode>(loadViewMode);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [initialStatus, setInitialStatus] = useState<MarketingStatus | undefined>(undefined);
  const query = useMarketingPosts();

  function setViewMode(mode: ViewMode) {
    setViewModeState(mode);
    window.localStorage.setItem(VIEW_MODE_KEY, mode);
  }

  function openPost(post: MarketingPost) {
    setEditingId(post.id);
    setInitialStatus(undefined);
    setDialogOpen(true);
  }

  function openCreate(status?: MarketingStatus) {
    setEditingId(null);
    setInitialStatus(status);
    setDialogOpen(true);
  }

  const posts = query.data?.items ?? [];
  // O Dialog recebe o post **do cache**, não uma cópia guardada em estado: criar o espaço de
  // revisão altera o post pela API, e uma cópia congelada seguiria oferecendo "Criar Espaço de
  // Revisão" mesmo depois de o espaço existir.
  const editing = posts.find((post) => post.id === editingId) ?? null;
  const publicados = posts.filter((post) => post.status === "publicado").length;

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Painel de Marketing"
        subtitle="Planejamento das postagens — do brainstorm ao ar."
        className="mb-0"
        actions={
          <Button size="sm" onClick={() => openCreate()}>
            + Nova postagem
          </Button>
        }
      />

      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Alternador de visualização — o item ativo é o "trilho" animado por trás do rótulo. */}
        <div
          className="flex items-center gap-1 rounded-md border border-line bg-surface-2 p-1 text-sm"
          role="group"
          aria-label="Modo de visualização"
        >
          {VIEW_OPTIONS.map((option) => {
            const Icon = option.icon;
            const active = viewMode === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => setViewMode(option.value)}
                aria-pressed={active}
                className={cn(
                  "relative flex items-center gap-1.5 rounded px-3 py-1.5 font-medium transition-colors",
                  active ? "text-ink" : "text-muted hover:text-ink",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="marketing-view-pill"
                    className="absolute inset-0 rounded bg-panel shadow-sm"
                    transition={reduceMotion ? { duration: 0 } : { duration: 0.2, ease: "easeOut" }}
                  />
                )}
                <Icon className="relative h-4 w-4" aria-hidden="true" />
                <span className="relative">{option.label}</span>
              </button>
            );
          })}
        </div>
        {query.data && (
          <span className="text-xs text-muted">
            {posts.length} postagem(ns) · {publicados} publicada(s)
          </span>
        )}
      </div>

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-40 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o painel de marketing.
        </div>
      )}
      {query.data && posts.length === 0 && (
        <p className="text-sm text-muted">
          Nenhuma postagem no planejamento ainda. Comece criando uma ideia — o card nasce na
          primeira coluna. {MARKETING_STATUS_ICONS.ideia}
        </p>
      )}

      {query.data && posts.length > 0 && (
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={viewMode}
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            {viewMode === "kanban" ? (
              <MarketingKanban
                posts={posts}
                onOpenPost={openPost}
                onCreateInColumn={(status) => openCreate(status)}
              />
            ) : (
              <PostsTable posts={posts} onOpenPost={openPost} />
            )}
          </motion.div>
        </AnimatePresence>
      )}

      <MarketingPostDialog
        post={editing}
        open={dialogOpen}
        initialStatus={initialStatus}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  );
}
