import { useState } from "react";
import { Button, cn } from "@manto/ui";
import type { RevisaoComment } from "../../lib/revisao";
import { formatTimecode } from "./format";

export interface CommentFeedProps {
  comments: RevisaoComment[];
  onSeek: (time: number) => void;
  onToggleResolve: (commentId: number) => void;
  onDelete: (commentId: number) => void;
  togglePending: boolean;
  deletePending: boolean;
}

type FeedFilter = "all" | "pending";

/**
 * Feed de comentários (feature 182, FR-007–FR-009): a ordenação cronológica pelo timestamp
 * já vem do backend (`review_ops.list_comments_for_version`) — aqui só filtra e apresenta.
 */
export function CommentFeed({
  comments,
  onSeek,
  onToggleResolve,
  onDelete,
  togglePending,
  deletePending,
}: CommentFeedProps) {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const visible = filter === "pending" ? comments.filter((c) => !c.resolved) : comments;

  return (
    <div className="space-y-3">
      <div className="flex gap-1 rounded-md bg-surface-2 p-1 text-xs">
        {(["all", "pending"] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setFilter(value)}
            className={cn(
              "flex-1 rounded px-2 py-1 font-medium transition-colors",
              filter === value ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink",
            )}
          >
            {value === "all" ? "Todos" : "Apenas pendentes"}
          </button>
        ))}
      </div>

      {visible.length === 0 && (
        <p className="text-sm text-muted">
          {filter === "pending" ? "Nenhum comentário pendente." : "Nenhum comentário nesta versão."}
        </p>
      )}

      {visible.length > 0 && (
        <ul className="divide-y divide-line">
          {visible.map((c) => (
            <li key={c.id} className="space-y-1 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-ink">{c.author}</span>
                {c.timecode != null && (
                  <button
                    type="button"
                    onClick={() => onSeek(c.timecode as number)}
                    className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-dark hover:bg-accent/20"
                  >
                    @ {formatTimecode(c.timecode)}
                  </button>
                )}
              </div>
              <p className={cn("text-sm", c.resolved ? "text-muted line-through" : "text-ink")}>{c.body}</p>
              {c.resolved && c.resolved_by_name && (
                <p className="text-xs text-green">
                  Concluído por {c.resolved_by_name} em {c.resolved_at}
                </p>
              )}
              <div className="flex gap-2">
                {c.can_resolve && (
                  <Button variant="ghost" size="sm" loading={togglePending} onClick={() => onToggleResolve(c.id)}>
                    {c.resolved ? "Reabrir" : "Concluir"}
                  </Button>
                )}
                {c.can_delete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={deletePending}
                    onClick={() => {
                      if (window.confirm("Excluir este comentário?")) onDelete(c.id);
                    }}
                  >
                    Excluir
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
