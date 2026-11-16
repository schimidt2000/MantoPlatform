import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { useRastreamento } from "../../lib/virtuais";
import {
  carregarPixel,
  eventoPixel,
  gravarConsentimento,
  lerConsentimento,
  type Consentimento,
} from "../../lib/pixel";

/**
 * Aviso de cookies da loja (feature 344). Só aparece quando há Pixel da Meta configurado e a pessoa
 * ainda não escolheu. "Aceitar" carrega o pixel; "Recusar" não carrega nada. A escolha vale para as
 * próximas visitas. Também manda a visita (PageView) a cada página da loja depois do aceite.
 */
export function AvisoCookies() {
  const { data } = useRastreamento();
  const pixelId = data?.meta_pixel_id ?? null;
  const [escolha, setEscolha] = useState<Consentimento>(() => lerConsentimento());
  const reduzirMovimento = useReducedMotion();
  const { pathname } = useLocation();

  // Carrega o pixel quando há ID e aceite (agora ou numa visita anterior).
  useEffect(() => {
    if (pixelId && escolha === "aceito") carregarPixel(pixelId);
  }, [pixelId, escolha]);

  // Uma visita por página da loja, só com o pixel carregado.
  useEffect(() => {
    if (pixelId && escolha === "aceito") eventoPixel("PageView");
  }, [pixelId, escolha, pathname]);

  const escolher = (valor: "aceito" | "recusado") => {
    gravarConsentimento(valor);
    setEscolha(valor);
  };

  // Sem animação de saída de propósito: com a aba em segundo plano o `AnimatePresence` deixava o
  // aviso montado e transparente por cima do botão de reservar, engolindo o toque. Escolheu, sai.
  if (!pixelId || escolha !== null) return null;

  return (
    <motion.div
      role="region"
      aria-label="Aviso de cookies"
      initial={reduzirMovimento ? false : { y: 24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.2 }}
      // A faixa em volta do cartão não pode bloquear toque na página.
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 px-3 pb-[max(12px,env(safe-area-inset-bottom))]"
    >
      <div className="pointer-events-auto mx-auto max-w-lg rounded-2xl border border-alo-gold/60 bg-alo-surface-2 p-4 shadow-[0_-8px_30px_rgba(0,0,0,0.45)]">
        <p className="text-[14px] leading-relaxed text-alo-ink">
          Usamos cookies da Meta para saber quais anúncios trazem você até aqui. Só com o seu
          ok.{" "}
          <Link to="/v/privacidade" className="text-alo-gold underline underline-offset-2">
            Saiba mais
          </Link>
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => escolher("recusado")}
            className="min-h-[44px] rounded-full border border-alo-line-strong px-4 text-[15px] text-alo-ink transition-colors hover:bg-alo-surface"
          >
            Recusar
          </button>
          <button
            type="button"
            onClick={() => escolher("aceito")}
            className="min-h-[44px] rounded-full border border-alo-gold/80 bg-alo-red px-4 text-[15px] font-bold text-alo-on-red transition-colors hover:bg-alo-red-hover"
          >
            Aceitar
          </button>
        </div>
      </div>
    </motion.div>
  );
}
