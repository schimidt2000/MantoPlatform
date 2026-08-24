import { useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import { useNfcResolution } from "../lib/nfc";

/**
 * Página pública da tag NFC da luminária (feature 255) — `app.mantoproducoes.com.br/nfc/<code>`.
 *
 * A cliente encosta o celular na peça e cai aqui, sem login. A URL gravada na tag é imutável;
 * TODO o conteúdo vem do servidor (`useNfcResolution`), então esta página evolui sem regravar
 * tag nenhuma. Código inexistente/desativado chega como `product: null` e a página mostra o
 * mesmo palco — não existe caminho de erro visível (SC-006: nunca revelar se um código existe).
 *
 * A entrada é o RETRATO da luminária física (2ª rodada, com foto da peça em mãos): céu noturno
 * com estrelinhas piscando, nuvens na base, e a estrela "Magia de Sonhar" que **acende** como a
 * lâmpada de verdade acende — primeiro o contorno apagado, depois o brilho quente revelando o
 * escrito. Coreografia em fases de ≤350ms (Princípio XI); com `useReducedMotion`, a estrela já
 * aparece acesa e nada pisca.
 */

/** `@handle` legível a partir da URL do Instagram que o servidor mandou. */
function instagramHandle(url: string): string {
  const match = /instagram\.com\/([^/?#]+)/i.exec(url);
  return match ? `@${match[1]}` : "@mantoproducoes";
}

/** Estrela de 5 pontas centrada em (110,116) — raio externo 92, interno 38. */
const STAR_POINTS = Array.from({ length: 10 }, (_, i) => {
  const radius = i % 2 === 0 ? 92 : 38;
  const angle = (Math.PI / 5) * i - Math.PI / 2;
  return `${(110 + radius * Math.cos(angle)).toFixed(1)},${(116 + radius * Math.sin(angle)).toFixed(1)}`;
}).join(" ");

/** Estrelinhas do céu — posições fixas (nada de aleatório: render estável, sem hidratar duas vezes). */
const SKY_STARS = [
  { top: "8%", left: "12%", size: 3, delay: 0 },
  { top: "14%", left: "78%", size: 2, delay: 0.6 },
  { top: "22%", left: "38%", size: 2, delay: 1.4 },
  { top: "28%", left: "88%", size: 3, delay: 0.9 },
  { top: "34%", left: "8%", size: 2, delay: 1.8 },
  { top: "6%", left: "55%", size: 2, delay: 2.2 },
  { top: "44%", left: "92%", size: 2, delay: 0.3 },
  { top: "52%", left: "6%", size: 3, delay: 1.1 },
  { top: "18%", left: "24%", size: 2, delay: 2.6 },
  { top: "40%", left: "72%", size: 2, delay: 1.6 },
  { top: "60%", left: "86%", size: 2, delay: 0.7 },
  { top: "64%", left: "14%", size: 2, delay: 2.0 },
];

export function NfcPage() {
  const { code = "" } = useParams<{ code: string }>();
  const resolution = useNfcResolution(code);
  const reducedMotion = useReducedMotion();

  const instagramUrl = resolution.data?.instagram_url;
  // Feature 261: por ora no máximo uma entrega de vídeo por tag.
  const videoDelivery = resolution.data?.deliveries.find((d) => d.kind === "video");

  // Conteúdo textual sobe em fases, depois que a estrela acendeu (~0.8s).
  const enter = (delay: number) =>
    reducedMotion
      ? {}
      : {
          initial: { opacity: 0, y: 14 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.3, delay, ease: "easeOut" as const },
        };

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-accent-dark to-ink px-6 py-10 text-center">
      {/* Céu: estrelinhas piscando (estáticas com movimento reduzido). */}
      {SKY_STARS.map((star, i) => (
        <motion.span
          key={i}
          aria-hidden="true"
          className="absolute rounded-full bg-on-color"
          style={{ top: star.top, left: star.left, width: star.size, height: star.size }}
          initial={{ opacity: reducedMotion ? 0.5 : 0.15 }}
          animate={
            reducedMotion
              ? { opacity: 0.5 }
              : { opacity: [0.15, 0.9, 0.15], scale: [1, 1.4, 1] }
          }
          transition={
            reducedMotion
              ? undefined
              : { duration: 2.8, delay: star.delay, repeat: Infinity, ease: "easeInOut" }
          }
        />
      ))}

      {/* Nuvens da base — como a nuvem que segura a estrela na peça física. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-16 left-1/2 h-48 w-[130%] -translate-x-1/2 rounded-[100%] bg-lamp-cloud/10 blur-2xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-24 left-1/4 h-40 w-96 -translate-x-1/2 rounded-[100%] bg-lamp-cloud/[0.07] blur-3xl"
      />

      <main className="relative flex w-full max-w-md flex-col items-center gap-5">
        {/* A luminária: o contorno chega apagado; o miolo ACENDE revelando o "Magia de Sonhar". */}
        <motion.div
          initial={reducedMotion ? undefined : { scale: 0.4, opacity: 0, rotate: -8 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1.2, 0.36, 1] }}
          className="relative"
          aria-hidden="true"
        >
          <svg viewBox="0 0 220 232" className="h-56 w-56">
            {/* Corpo apagado: só o contorno e um miolo quase escuro. */}
            <polygon
              points={STAR_POINTS}
              className="fill-lamp-glow/10 stroke-lamp-border"
              strokeWidth="9"
              strokeLinejoin="round"
            />
          </svg>

          {/* A luz: camada acesa que surge por cima, com o halo vazando no escuro. */}
          <motion.div
            className="absolute inset-0 drop-shadow-lamp"
            initial={reducedMotion ? { opacity: 1 } : { opacity: 0 }}
            animate={
              reducedMotion
                ? { opacity: 1 }
                : { opacity: [0, 0.35, 1, 0.85, 1] }
            }
            transition={
              reducedMotion
                ? undefined
                : { duration: 0.5, delay: 0.4, times: [0, 0.35, 0.6, 0.8, 1] }
            }
          >
            <svg viewBox="0 0 220 232" className="h-56 w-56">
              <defs>
                <radialGradient id="nfc-star-glow" cx="50%" cy="48%" r="62%">
                  <stop offset="0%" className="[stop-color:theme(colors.lamp.glow)]" />
                  <stop offset="100%" className="[stop-color:theme(colors.lamp.glow-deep)]" />
                </radialGradient>
              </defs>
              <polygon
                points={STAR_POINTS}
                fill="url(#nfc-star-glow)"
                className="stroke-lamp-border"
                strokeWidth="9"
                strokeLinejoin="round"
              />
              {/* O escrito da peça, que só aparece com a luz acesa — igual à luminária. */}
              <text
                x="110"
                y="112"
                textAnchor="middle"
                className="fill-lamp-script font-display italic"
                fontSize="30"
              >
                Magia
              </text>
              <text
                x="110"
                y="140"
                textAnchor="middle"
                className="fill-lamp-script font-display italic"
                fontSize="17"
              >
                de Sonhar
              </text>
            </svg>
          </motion.div>

          {/* Respiração da luz — só para quem aceita movimento. */}
          {!reducedMotion && (
            <motion.div
              className="absolute inset-0 drop-shadow-lamp"
              animate={{ opacity: [0, 0.35, 0] }}
              transition={{ duration: 3.6, delay: 1.2, repeat: Infinity, ease: "easeInOut" }}
            >
              <svg viewBox="0 0 220 232" className="h-56 w-56">
                <polygon points={STAR_POINTS} className="fill-lamp-glow/40" strokeLinejoin="round" />
              </svg>
            </motion.div>
          )}
        </motion.div>

        <motion.p
          {...enter(0.8)}
          className="text-xs font-bold uppercase tracking-[0.3em] text-gold"
        >
          Manto Produções
        </motion.p>

        <motion.h1
          {...enter(0.9)}
          className="font-display text-3xl leading-tight text-on-color"
        >
          A magia da Manto também na sua casa
        </motion.h1>

        {videoDelivery ? (
          // Entrega de vídeo (feature 261): substitui o placeholder pelo conteúdo real. O card
          // entra na mesma coreografia de fases das linhas acima — só troca o conteúdo.
          <motion.div
            {...enter(1.0)}
            className="w-full overflow-hidden rounded-xl border border-lamp-cloud/20 bg-lamp-cloud/[0.06] shadow-lg"
          >
            <p className="px-5 pt-4 text-sm font-semibold text-on-color">
              {videoDelivery.title || "Um vídeo especial para você"}
            </p>
            <video
              controls
              playsInline
              preload="metadata"
              className="mt-3 block w-full bg-ink"
              src={assetUrl(videoDelivery.media_url)}
            />
          </motion.div>
        ) : (
          <motion.p {...enter(1.0)} className="text-base leading-relaxed text-on-color/70">
            Este é o portal da sua luminária. Em breve, ele se abrirá bem aqui — com novidades e
            surpresas feitas para você.
          </motion.p>
        )}

        {/* CTA só quando o servidor respondeu: botão sem destino é botão morto (Princípio V). */}
        {instagramUrl && (
          <motion.a
            {...enter(1.1)}
            href={instagramUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-full bg-gold px-8 text-base font-bold text-ink shadow-lg transition-colors hover:bg-gold/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
              <path d="M12 2.2c3.2 0 3.6 0 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.26.07 1.64.07 4.85s0 3.6-.07 4.85c-.05 1.17-.25 1.8-.41 2.23a3.7 3.7 0 0 1-.9 1.38c-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.26.06-1.64.07-4.85.07s-3.6 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.6 2.2 15.2 2.2 12s0-3.6.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.4 2.2 8.8 2.2 12 2.2Zm0 1.8c-3.15 0-3.52 0-4.76.07-1.08.05-1.66.23-2.05.38-.51.2-.88.44-1.26.82-.38.38-.62.75-.82 1.26-.15.39-.33.97-.38 2.05C2.66 9.83 2.65 10.2 2.65 12s0 2.17.07 3.42c.05 1.08.23 1.66.38 2.05.2.51.44.88.82 1.26.38.38.75.62 1.26.82.39.15.97.33 2.05.38 1.24.06 1.61.07 4.76.07s3.52 0 4.76-.07c1.08-.05 1.66-.23 2.05-.38.51-.2.88-.44 1.26-.82.38-.38.62-.75.82-1.26.15-.39.33-.97.38-2.05.06-1.25.07-1.62.07-3.42s0-2.17-.07-3.42c-.05-1.08-.23-1.66-.38-2.05a2.9 2.9 0 0 0-.82-1.26 2.9 2.9 0 0 0-1.26-.82c-.39-.15-.97-.33-2.05-.38C15.52 4 15.15 4 12 4Zm0 3.1a4.9 4.9 0 1 1 0 9.8 4.9 4.9 0 0 1 0-9.8Zm0 1.8a3.1 3.1 0 1 0 0 6.2 3.1 3.1 0 0 0 0-6.2Zm5.1-2.98a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3Z" />
            </svg>
            Seguir {instagramHandle(instagramUrl)}
          </motion.a>
        )}
      </main>

      <motion.footer {...enter(1.25)} className="relative mt-10 text-xs text-on-color/40">
        mantoproducoes.com.br
      </motion.footer>
    </div>
  );
}
