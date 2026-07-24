import { useCallback, useEffect, useState, type RefObject } from "react";

export const PLAYBACK_SPEEDS = [0.5, 1, 1.5, 2] as const;
export type PlaybackSpeed = (typeof PLAYBACK_SPEEDS)[number];

export interface VideoPlayerState {
  currentTime: number;
  duration: number;
  paused: boolean;
  playbackRate: PlaybackSpeed;
}

export interface VideoPlayerControls {
  togglePlay: () => void;
  pause: () => void;
  seek: (deltaSeconds: number) => void;
  seekTo: (time: number) => void;
  setSpeed: (rate: PlaybackSpeed) => void;
  getCurrentTime: () => number;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}

/**
 * Player de vídeo custom (feature 182): estado + controles sobre um `<video>` nativo via
 * `ref`, com atalhos de teclado globais (Espaço, setas) que ignoram campos de texto focados.
 */
export function useVideoPlayer(
  videoRef: RefObject<HTMLVideoElement>,
): [VideoPlayerState, VideoPlayerControls] {
  const [state, setState] = useState<VideoPlayerState>({
    currentTime: 0,
    duration: 0,
    paused: true,
    playbackRate: 1,
  });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTimeUpdate = () => setState((s) => ({ ...s, currentTime: video.currentTime }));
    const onLoadedMetadata = () =>
      setState((s) => ({ ...s, duration: Number.isFinite(video.duration) ? video.duration : 0 }));
    const onPlay = () => setState((s) => ({ ...s, paused: false }));
    const onPause = () => setState((s) => ({ ...s, paused: true }));
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("loadedmetadata", onLoadedMetadata);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("loadedmetadata", onLoadedMetadata);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, [videoRef]);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play();
    else video.pause();
  }, [videoRef]);

  const pause = useCallback(() => {
    videoRef.current?.pause();
  }, [videoRef]);

  const seekTo = useCallback(
    (time: number) => {
      const video = videoRef.current;
      if (!video) return;
      const max = Number.isFinite(video.duration) ? video.duration : time;
      video.currentTime = Math.max(0, Math.min(time, max));
      setState((s) => ({ ...s, currentTime: video.currentTime }));
    },
    [videoRef],
  );

  const seek = useCallback(
    (deltaSeconds: number) => {
      const video = videoRef.current;
      if (!video) return;
      seekTo(video.currentTime + deltaSeconds);
    },
    [videoRef, seekTo],
  );

  const setSpeed = useCallback(
    (rate: PlaybackSpeed) => {
      const video = videoRef.current;
      if (!video) return;
      video.playbackRate = rate;
      setState((s) => ({ ...s, playbackRate: rate }));
    },
    [videoRef],
  );

  const getCurrentTime = useCallback(() => videoRef.current?.currentTime ?? 0, [videoRef]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (isTypingTarget(e.target)) return;
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        seek(5);
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        seek(-5);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [togglePlay, seek]);

  return [state, { togglePlay, pause, seek, seekTo, setSpeed, getCurrentTime }];
}
