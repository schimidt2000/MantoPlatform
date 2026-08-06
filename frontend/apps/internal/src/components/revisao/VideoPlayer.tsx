import { forwardRef, useImperativeHandle, useRef } from "react";
import { Pause, Play } from "lucide-react";
import { cn } from "@manto/ui";
import { PLAYBACK_SPEEDS, useVideoPlayer, type PlaybackSpeed } from "./useVideoPlayer";
import { VideoScrubber } from "./VideoScrubber";
import { formatTimecode } from "./format";

export interface VideoPlayerHandle {
  pause: () => void;
  getCurrentTime: () => number;
  seekTo: (time: number) => void;
}

export interface VideoPlayerProps {
  url: string;
  /** Timestamps (segundos) dos comentários da versão atual, para os marcadores da timeline. */
  markers?: number[];
}

/**
 * Player de vídeo custom estilo Vimeo (feature 182): `<video>` nativo sem controles do
 * browser, scrubber com marcadores de comentário, velocidade e atalhos de teclado (via
 * `useVideoPlayer`). Expõe `pause`/`getCurrentTime`/`seekTo` ao pai via `ref` para integrar
 * com o campo de novo comentário e o feed de comentários sem re-renderizar a cada frame.
 */
export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer(
  { url, markers = [] },
  ref,
) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, controls] = useVideoPlayer(videoRef);

  useImperativeHandle(
    ref,
    () => ({
      pause: controls.pause,
      getCurrentTime: controls.getCurrentTime,
      seekTo: controls.seekTo,
    }),
    [controls],
  );

  return (
    // `bg-media` e não `bg-ink`: `ink` é o token de TEXTO e inverte com o tema — no escuro ele
    // vira #f0eef5, então a moldura do player virava uma caixa quase branca com todos os
    // controles brancos por cima, ilegíveis. `media` é escura nos dois temas, que é a convenção
    // de player (o vídeo tem que ser a coisa mais clara da caixa); por isso os `text-white`
    // daqui para baixo estão CERTOS e não devem virar `on-color`.
    <div className="flex flex-col gap-2 rounded-md bg-media p-2">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        ref={videoRef}
        src={url}
        className="aspect-video w-full rounded-sm bg-black"
        onClick={controls.togglePlay}
      />
      <div className="flex min-w-0 items-center gap-3 px-1">
        <button
          type="button"
          aria-label={state.paused ? "Reproduzir" : "Pausar"}
          onClick={controls.togglePlay}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
        >
          {state.paused ? <Play className="h-4 w-4" aria-hidden="true" /> : <Pause className="h-4 w-4" aria-hidden="true" />}
        </button>

        <VideoScrubber
          currentTime={state.currentTime}
          duration={state.duration}
          markers={markers}
          onSeekTo={controls.seekTo}
        />

        <span className="w-28 shrink-0 text-right text-xs tabular-nums text-white/80">
          {formatTimecode(state.currentTime)} / {formatTimecode(state.duration)}
        </span>

        <div className="flex shrink-0 items-center gap-1">
          {PLAYBACK_SPEEDS.map((speed) => (
            <button
              key={speed}
              type="button"
              onClick={() => controls.setSpeed(speed as PlaybackSpeed)}
              className={cn(
                "rounded px-1.5 py-0.5 text-xs font-medium transition-colors",
                state.playbackRate === speed
                  ? // `text-media` e não `text-ink`: a pastilha de velocidade ativa é branca
                    // fixa, e `ink` inverte — no tema escuro daria texto quase branco sobre
                    // branco. `media` é escura nos dois temas, igual à moldura do player.
                    "bg-white text-media"
                  : "text-white/70 hover:bg-white/10 hover:text-white",
              )}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});
