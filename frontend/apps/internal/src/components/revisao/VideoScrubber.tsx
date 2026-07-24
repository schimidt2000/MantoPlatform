import { useCallback, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { cn } from "@manto/ui";
import { formatTimecode } from "./format";

export interface VideoScrubberProps {
  currentTime: number;
  duration: number;
  /** Timestamps (segundos) dos comentários da versão atual — vira marcador visual na barra. */
  markers?: number[];
  onSeekTo: (time: number) => void;
}

/** Barra de progresso clicável/arrastável com marcadores de comentário (feature 182). */
export function VideoScrubber({ currentTime, duration, markers = [], onSeekTo }: VideoScrubberProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

  const timeFromClientX = useCallback(
    (clientX: number) => {
      const track = trackRef.current;
      if (!track || duration <= 0) return 0;
      const rect = track.getBoundingClientRect();
      const fraction = rect.width > 0 ? Math.min(1, Math.max(0, (clientX - rect.left) / rect.width)) : 0;
      return fraction * duration;
    },
    [duration],
  );

  const handlePointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    onSeekTo(timeFromClientX(e.clientX));
  };
  const handlePointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    onSeekTo(timeFromClientX(e.clientX));
  };
  const handlePointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    setDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
  };

  const progressPct = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;

  return (
    <div
      ref={trackRef}
      role="slider"
      aria-label="Progresso do vídeo"
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
      aria-valuenow={Math.round(currentTime)}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className="group relative h-2 min-w-0 flex-1 touch-none select-none rounded-full bg-surface-2"
    >
      <div
        className="pointer-events-none absolute inset-y-0 left-0 rounded-full bg-accent"
        style={{ width: `${progressPct}%` }}
      />
      <div
        className={cn(
          "pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent shadow-sm transition-transform",
          dragging && "scale-125",
        )}
        style={{ left: `${progressPct}%` }}
      />
      {duration > 0 &&
        markers.map((t, i) => (
          <div
            key={`${t}-${i}`}
            title={`Comentário em ${formatTimecode(t)}`}
            className="pointer-events-none absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-panel bg-gold"
            style={{ left: `${Math.min(100, Math.max(0, (t / duration) * 100))}%` }}
          />
        ))}
    </div>
  );
}
