import { useState, type RefObject } from "react";
import { Button } from "@manto/ui";
import type { VideoPlayerHandle } from "./VideoPlayer";
import { formatTimecode } from "./format";

export interface NewCommentFormProps {
  playerRef: RefObject<VideoPlayerHandle | null>;
  onSubmit: (body: string, timecode: number) => void;
  isPending: boolean;
}

/**
 * Campo de novo comentário ancorado no vídeo (feature 182, FR-005/FR-006): ao focar,
 * pausa o player e captura o timestamp atual, exibido como "@ MM:SS" até o envio.
 */
export function NewCommentForm({ playerRef, onSubmit, isPending }: NewCommentFormProps) {
  const [body, setBody] = useState("");
  const [capturedTime, setCapturedTime] = useState<number | null>(null);

  const handleFocus = () => {
    playerRef.current?.pause();
    setCapturedTime(playerRef.current?.getCurrentTime() ?? 0);
  };

  const handleSubmit = () => {
    if (!body.trim()) return;
    onSubmit(body, capturedTime ?? playerRef.current?.getCurrentTime() ?? 0);
    setBody("");
    setCapturedTime(null);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted">
          {capturedTime != null
            ? `Comentário será marcado em @ ${formatTimecode(capturedTime)}`
            : "Clique no campo para marcar o ponto atual do vídeo."}
        </p>
        {capturedTime != null && (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-dark">
            @ {formatTimecode(capturedTime)}
          </span>
        )}
      </div>
      <textarea
        className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
        placeholder="Escreva um comentário…"
        value={body}
        onFocus={handleFocus}
        onChange={(e) => setBody(e.target.value)}
      />
      <Button size="sm" loading={isPending} onClick={handleSubmit} disabled={!body.trim()}>
        Comentar
      </Button>
    </div>
  );
}
