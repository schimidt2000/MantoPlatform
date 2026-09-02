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

// Faixa de altura do palco da galeria. A foto continua aparecendo inteira (`object-contain`),
// mas o quadro onde ela vive tem tamanho previsível: sem o teto, um retrato alto tomava a tela
// toda; sem o piso, uma foto larga virava uma tira baixa. Com os dois, produtos diferentes ficam
// no mesmo padrão e a página para de "pular" de um item para outro.
const MAX_HEIGHT_PX = 620;
const MIN_HEIGHT_PX = 380;

/**
 * Teto e piso ficam em **CSS**, não em contas de JavaScript, por dois motivos:
 *
 * 1. Valem sempre — inclusive antes de a foto carregar, quando ela falha, e depois de o usuário
 *    redimensionar a janela (a altura calculada no `onLoad` é um pixel fixo que envelhece).
 * 2. `62vh` acompanha a altura real da tela sem precisar de listener de resize.
 *
 * O `min()` resolve sozinho o caso da janela baixa: em telas curtas manda o `62vh`, em telas
 * altas manda o limite em pixels, e o piso nunca ultrapassa o teto porque o navegador aplica
 * `max-height` depois de `min-height`.
 */
const FAIXA_DO_PALCO = {
  minHeight: `${MIN_HEIGHT_PX}px`,
  maxHeight: `min(62vh, ${MAX_HEIGHT_PX}px)`,
} as const;

/**
 * Mesma faixa, em número, para já pedir a altura certa quando a foto carrega — o CSS acima é a
 * garantia, este cálculo é o que evita o quadro nascer no piso e "crescer" na frente do cliente.
 */
function alturaNaFaixa(larguraDoQuadro: number, naturalWidth: number, naturalHeight: number) {
  const teto = Math.min(window.innerHeight * 0.62, MAX_HEIGHT_PX);
  const piso = Math.min(MIN_HEIGHT_PX, teto);
  const natural = larguraDoQuadro * (naturalHeight / naturalWidth);
  return Math.round(Math.min(Math.max(natural, piso), teto));
}

/**
 * Galeria animada do detalhe do produto — recria a transição da feature 143 (cross-fade +
 * altura animada por foto + swipe) com Framer Motion (research.md §3, Princípio IX). Estendida
 * na feature 185 para incluir um item de vídeo, cuja altura também anima ao entrar em foco
 * (dimensões via `onLoadedMetadata`, não `onLoad` de imagem).
 */
export function ProductGallery({ images, name, videoUrl, videoKind }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  // Começa no piso da faixa: o quadro já nasce com o tamanho certo, sem depender de a foto
  // carregar (uma imagem quebrada deixava o palco com 24px de altura).
  const [height, setHeight] = useState(MIN_HEIGHT_PX);
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
    setHeight(alturaNaFaixa(wrapWidth, naturalWidth, naturalHeight));
  }

  function goTo(nextIndex: number) {
    const clamped = Math.max(0, Math.min(nextIndex, media.length - 1));
    setIndex(clamped);
  }

  if (!current) {
    return <div className="rounded-lg bg-bg-alt" style={FAIXA_DO_PALCO} />;
  }

  return (
    // `min-w-0` é obrigatório: como filho de grid, o padrão é `min-width: auto`, ou seja, a
    // coluna não encolhe abaixo da largura NATURAL da foto. Uma imagem de arquivo grande
    // engolia a coluna do texto — título quebrando em duas linhas, tags empilhadas e botões
    // virando bolinhas —, enquanto uma foto menor no mesmo layout ficava certa.
    <div className="min-w-0">
      {/* A altura do palco é um `style` de verdade, não um alvo de animação: ela precisa valer
          desde o primeiro quadro, inclusive quando a foto falha ao carregar. A transição fica
          por conta do CSS (e some com `prefers-reduced-motion`), o que mantém o movimento sem
          entregar o tamanho do quadro para a biblioteca de animação. */}
      <div
        ref={wrapRef}
        style={{ height, ...FAIXA_DO_PALCO }}
        className="relative mb-3 touch-pan-y select-none overflow-hidden rounded-lg bg-bg-alt shadow-md transition-[height] duration-300 ease-out motion-reduce:transition-none"
      >
        <div className="relative h-full w-full">
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
        </div>
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
                  // 64px na tela → variante de 128 (2× para retina). Antes baixava o original
                  // inteiro (~380× mais bytes do que o quadradinho precisa) — feature 270.
                  src={assetUrl(item.url, { largura: 128 })}
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
