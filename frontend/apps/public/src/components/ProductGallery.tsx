import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import type { CatalogItemImage } from "../lib/catalogo";

interface ProductGalleryProps {
  images: CatalogItemImage[];
  name: string;
}

const MAX_HEIGHT_RATIO = 0.7; // 70vh, mesmo limite do detail.html atual

/**
 * Galeria animada do detalhe do produto — recria a transição da feature 143 (cross-fade +
 * altura animada por foto + swipe) com Framer Motion (research.md §3, Princípio IX).
 */
export function ProductGallery({ images, name }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [height, setHeight] = useState<number | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  const sorted = [...images].sort((a, b) => a.position - b.position);
  const current = sorted[index];

  function applyHeight(img: HTMLImageElement) {
    const wrapWidth = wrapRef.current?.clientWidth ?? img.naturalWidth;
    const maxHeight = window.innerHeight * MAX_HEIGHT_RATIO;
    const natural = wrapWidth * (img.naturalHeight / img.naturalWidth);
    setHeight(Math.min(natural, maxHeight));
  }

  function goTo(nextIndex: number) {
    const clamped = Math.max(0, Math.min(nextIndex, sorted.length - 1));
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
            <motion.img
              key={current.url}
              src={assetUrl(current.url)}
              alt={`${name} — foto ${index + 1}`}
              className="h-full w-full object-contain"
              initial={shouldReduceMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={shouldReduceMotion ? undefined : { opacity: 0 }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
              drag={sorted.length > 1 ? "x" : false}
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.5}
              onLoad={(event) => applyHeight(event.currentTarget)}
              onDragEnd={(_event, info) => {
                const crossedThreshold = Math.abs(info.offset.x) > 40;
                if (crossedThreshold) {
                  goTo(index + (info.offset.x < 0 ? 1 : -1));
                }
              }}
            />
          </AnimatePresence>
        </motion.div>
      </div>

      {sorted.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {sorted.map((img, i) => (
            <button
              key={img.url}
              type="button"
              onClick={() => goTo(i)}
              className={`h-16 w-16 flex-none overflow-hidden rounded-md border-2 ${
                i === index ? "border-accent" : "border-transparent"
              }`}
            >
              <img
                src={assetUrl(img.url)}
                alt={`${name} — miniatura ${i + 1}`}
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
