import { useState } from "react";
import { useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import { useNfcResolution } from "../lib/nfc";

/**
 * Página pública da tag NFC da luminária (feature 255) — `app.mantoproducoes.com.br/nfc/<code>`.
 *
 * A cliente encosta o celular na peça e cai aqui, sem login. A URL gravada na tag é imutável;
 * TODO o conteúdo vem do servidor (`useNfcResolution`), então esta página evolui sem regravar
 * tag nenhuma. Código inexistente/desativado chega como `product: null` e a página simplesmente
 * mostra o modo genérico — não existe caminho de erro visível (SC-006: nunca revelar se um
 * código existe).
 *
 * Mobile-first de verdade (Princípio X): o acesso nasce de um toque de NFC num iPhone/Android,
 * quase sempre à noite, ao lado da luminária acesa — daí a superfície escura (roxo profundo da
 * paleta) com o portal dourado se abrindo (Princípio XI, com `useReducedMotion`).
 */

/** `@handle` legível a partir da URL do Instagram que o servidor mandou. */
function instagramHandle(url: string): string {
  const match = /instagram\.com\/([^/?#]+)/i.exec(url);
  return match ? `@${match[1]}` : "@mantoproducoes";
}

export function NfcPage() {
  const { code = "" } = useParams<{ code: string }>();
  const resolution = useNfcResolution(code);
  const reducedMotion = useReducedMotion();
  // Foto que não carregou vira o brilho genérico — nunca o ícone de imagem quebrada no portal.
  const [photoBroken, setPhotoBroken] = useState(false);

  const product = resolution.data?.product ?? null;
  const instagramUrl = resolution.data?.instagram_url;
  const showPhoto = product !== null && !photoBroken;

  // Entrada encadeada: portal abre → conteúdo sobe. Com movimento reduzido, tudo já visível.
  const enter = (delay: number) =>
    reducedMotion
      ? {}
      : {
          initial: { opacity: 0, y: 14 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.3, delay, ease: "easeOut" as const },
        };

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-accent-dark to-ink px-6 py-10 text-center">
      <main className="flex w-full max-w-md flex-col items-center gap-6">
        {/* O portal: anel dourado que se abre revelando a peça (ou o brilho genérico). */}
        <motion.div
          initial={reducedMotion ? undefined : { scale: 0.25, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.35, ease: [0.22, 1.2, 0.36, 1] }}
          className="relative flex h-44 w-44 items-center justify-center rounded-full border-2 border-gold/80 shadow-[0_0_60px_rgba(177,121,58,0.35)]"
          aria-hidden="true"
        >
          {/* Halo respirando — só para quem aceita movimento. */}
          {!reducedMotion && (
            <motion.div
              className="absolute inset-0 rounded-full border border-gold/30"
              animate={{ scale: [1, 1.12, 1], opacity: [0.6, 0.15, 0.6] }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
          {showPhoto ? (
            <img
              src={assetUrl(product.photo_url)}
              alt={product.name}
              onError={() => setPhotoBroken(true)}
              className="h-40 w-40 rounded-full object-cover"
            />
          ) : (
            <span className="text-6xl">✨</span>
          )}
        </motion.div>

        <motion.p
          {...enter(0.2)}
          className="text-xs font-bold uppercase tracking-[0.3em] text-gold"
        >
          Manto Produções
        </motion.p>

        <motion.h1
          {...enter(0.3)}
          className="font-display text-3xl leading-tight text-on-color"
        >
          A magia da Manto também na sua casa
        </motion.h1>

        <motion.p {...enter(0.4)} className="text-base leading-relaxed text-on-color/70">
          Este é o portal da sua luminária. Em breve, ele se abrirá bem aqui — com novidades e
          surpresas feitas para você.
        </motion.p>

        {/* CTA só quando o servidor respondeu: botão sem destino é botão morto (Princípio V). */}
        {instagramUrl && (
          <motion.a
            {...enter(0.5)}
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

      <motion.footer {...enter(0.65)} className="mt-10 text-xs text-on-color/40">
        mantoproducoes.com.br
      </motion.footer>
    </div>
  );
}
