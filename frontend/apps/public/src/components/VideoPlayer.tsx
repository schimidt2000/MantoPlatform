import { useRef, useState } from "react";
import type { VideoKind } from "../lib/catalogo";

interface VideoPlayerProps {
  videoUrl: string;
  videoKind: VideoKind;
  /** Rótulo acessível (nome do Tema/Personagem) — usado nos botões de som/tela cheia. */
  label: string;
  className?: string;
  /** Chamado com as dimensões naturais do vídeo assim que carregam (galeria anima a altura). */
  onDimensions?: (width: number, height: number) => void;
  /** Chamado quando o vídeo falha ao carregar — quem usa decide se remove da galeria (silencioso). */
  onError?: () => void;
}

/**
 * Player de vídeo do catálogo (feature 185): MP4/Drive tocam num `<video>` nativo com controles
 * customizados (mute/fullscreen); Vimeo usa o embed oficial via `<iframe>`, que já suporta
 * autoplay/mute/loop/playsinline nativamente por query params — ver research.md §1.
 */
export function VideoPlayer({
  videoUrl,
  videoKind,
  label,
  className = "",
  onDimensions,
  onError,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [muted, setMuted] = useState(true);

  function toggleMute() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setMuted(video.muted);
  }

  async function toggleFullscreen() {
    const wrap = wrapRef.current;
    if (!wrap) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await wrap.requestFullscreen().catch(() => {
        // Fullscreen indisponível (ex.: iOS Safari fora de gesto direto) — degrada sem quebrar
      });
    }
  }

  if (videoKind === "vimeo") {
    const src = `${videoUrl}${videoUrl.includes("?") ? "&" : "?"}autoplay=1&muted=1&loop=1&background=1&playsinline=1`;
    return (
      <div ref={wrapRef} className={`relative h-full w-full ${className}`}>
        <iframe
          src={src}
          title={label}
          className="h-full w-full"
          allow="autoplay; fullscreen; picture-in-picture"
          allowFullScreen
          onError={() => onError?.()}
        />
      </div>
    );
  }

  return (
    <div ref={wrapRef} className={`relative h-full w-full ${className}`}>
      <video
        ref={videoRef}
        src={videoUrl}
        className="h-full w-full object-contain"
        autoPlay
        muted
        loop
        playsInline
        onLoadedMetadata={(event) => {
          const video = event.currentTarget;
          onDimensions?.(video.videoWidth, video.videoHeight);
        }}
        onError={() => onError?.()}
      />
      <div className="absolute bottom-3 right-3 flex gap-2">
        <button
          type="button"
          onClick={toggleMute}
          aria-label={muted ? `Ativar som de ${label}` : `Silenciar ${label}`}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-ink/60 text-white backdrop-blur-sm transition-transform hover:scale-105"
        >
          {muted ? "🔇" : "🔊"}
        </button>
        <button
          type="button"
          onClick={toggleFullscreen}
          aria-label={`Tela cheia — ${label}`}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-ink/60 text-white backdrop-blur-sm transition-transform hover:scale-105"
        >
          ⛶
        </button>
      </div>
    </div>
  );
}
