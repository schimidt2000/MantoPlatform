import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import type { CatalogItemImage, VideoKind } from "../lib/catalogo";
import { VideoPlayer } from "./VideoPlayer";

type MediaItem =
  | { kind: "image"; key: string; url: string }
  | { kind: "video"; key: string; url: string; videoKind: VideoKind };

interface ProductGalleryProps {
  images: CatalogItemImage[];
  name: string;
  /** URL de vídeo do Tema (opcional) — entra na galeria como item adicional (feature 185). */
  videoUrl?: string | null;
  videoKind?: VideoKind;
}

const MAX_HEIGHT_RATIO = 0.7; // 70vh, mesmo limite do detail.html atual

/**
 * Galeria animada do detalhe do produto — recria a transição da feature 143 (cross-fade +
 * altura animada por foto + swipe) com Framer Motion (research.md §3, Princípio IX). Estendida
 * na feature 185 para incluir um item de vídeo, cuja altura também anima ao entrar em foco
 * (dimensões via `onLoadedMetadata`, não `onLoad` de imagem).
 */
export function ProductGallery({ images, name, videoUrl, videoKind }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [height, setHeight] = useState<number | undefined>(undefined);
  const [brokenVideo, setBrokenVideo] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  const sortedImages = [...images].sort((a, b) => a.position - b.position);
  const media: MediaItem[] = [
    ...sortedImages.map((img) => ({ kind: "image" as const, key: img.url, url: img.url })),
    ...(videoUrl && videoKind && !brokenVideo
      ? [{ kind: "video" as const, key: videoUrl, url: videoUrl, videoKind }]
      : []),
  ];
  // Clampado a cada render (não só em goTo): se o vídeo era o item ativo e falha ao carregar,
  // `media` encolhe e `index` pode ficar fora dos limites — sem isso a galeria trava vazia e
  // sem miniaturas para o cliente voltar às fotos (violaria FR-017: falha de mídia não pode
  // quebrar a navegação).
  const safeIndex = Math.max(0, Math.min(index, media.length - 1));
  const current = media[safeIndex];

  function applyHeight(naturalWidth: number, naturalHeight: number) {
    const wrapWidth = wrapRef.current?.clientWidth ?? naturalWidth;
    const maxHeight = window.innerHeight * MAX_HEIGHT_RATIO;
    const natural = wrapWidth * (naturalHeight / naturalWidth);
    setHeight(Math.min(natural, maxHeight));
  }

  function goTo(nextIndex: number) {
    const clamped = Math.max(0, Math.min(nextIndex, media.length - 1));
    setIndex(clamped);
  }

  if (!current) {
    return <div className="aspect-[4/5] rounded-lg bg-bg-alt" />;
  }

  return (
    <div>
      <div
        ref={wrapRef}
        className="mb-3 touch-pan-y select-none overflow-hidden rounded-lg bg-bg-alt shadow-md"
      >
        <motion.div
          animate={{ height: height ?? "auto" }}
          transition={{ duration: shouldReduceMotion ? 0 : 0.32, ease: "easeOut" }}
          className="relative"
          style={{ aspectRatio: height ? undefined : "4 / 5" }}
        >
          <AnimatePresence mode="wait" initial={false}>
            {current.kind === "image" ? (
              <motion.img
                key={current.key}
                src={assetUrl(current.url)}
                alt={`${name} — foto ${safeIndex + 1}`}
                className="h-full w-full object-contain"
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
                drag={media.length > 1 ? "x" : false}
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.5}
                onLoad={(event) =>
                  applyHeight(event.currentTarget.naturalWidth, event.currentTarget.naturalHeight)
                }
                onDragEnd={(_event, info) => {
                  const crossedThreshold = Math.abs(info.offset.x) > 40;
                  if (crossedThreshold) {
                    goTo(safeIndex + (info.offset.x < 0 ? 1 : -1));
                  }
                }}
              />
            ) : (
              <motion.div
                key={current.key}
                className="h-full w-full"
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
              >
                <VideoPlayer
                  videoUrl={current.url}
                  videoKind={current.videoKind}
                  label={name}
                  onDimensions={applyHeight}
                  onError={() => setBrokenVideo(true)}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {media.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {media.map((item, i) => (
            <button
              key={item.key}
              type="button"
              onClick={() => goTo(i)}
              className={`relative h-16 w-16 flex-none overflow-hidden rounded-md border-2 ${
                i === safeIndex ? "border-accent" : "border-transparent"
              }`}
            >
              {item.kind === "image" ? (
                <img
                  src={assetUrl(item.url)}
                  alt={`${name} — miniatura ${i + 1}`}
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center bg-ink/80 text-lg text-white">
                  ▶
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
