import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { MotionProps } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { apiMoneyToNumber, dataPorExtenso, useVitrineVirtual } from "../../lib/virtuais";

/**
 * Cartão do Papai Noel no menu da luminária (feature 355).
 *
 * Quem encosta o celular na luminária é cliente que já comprou da Manto, quase sempre com criança
 * em casa: o público da chamada com o Papai Noel da loja (`alo.mantoproducoes.com.br`). O cartão
 * vive até o dia das chamadas e some sozinho depois dele — passado o último dia a página nem
 * consulta a loja. Depois de 06/12 este arquivo sai do código (dívida no `docs/05`).
 *
 * Nunca oferece o que não há: lê a vitrine pública e só aparece com a campanha publicada e com
 * horário ao vivo livre ou vídeo gravado em estoque. O texto acompanha o formato que ainda tem
 * vaga. Vitrine fora do ar = nenhum cartão, sem aviso: a luminária não é lugar de mensagem de erro.
 */

const SLUG = "papai-noel";

/** Último dia do cartão — é também o dia das chamadas ao vivo (campanha 341, grade de 06/12). */
const ULTIMO_DIA = "2026-12-06";

/**
 * A campanha na loja. `?origem=luminaria` é a linha "Luminária" no card "Visitas e vendas" (344/355).
 * O prefixo segue o `CATALOGO_BASENAME` do `App.tsx`: `/catalogo` só no build de produção — a tag
 * mora na raiz, e um link relativo sem o prefixo cairia fora do roteador da loja.
 */
const DESTINO = `${import.meta.env.PROD ? "/catalogo" : ""}/v/${SLUG}?origem=luminaria`;

/**
 * Hoje em São Paulo, `AAAA-MM-DD`. O fuso é o da campanha, não o do aparelho: uma família em
 * Manaus não pode perder o cartão uma hora antes, nem alguém em Lisboa ganhar três a mais.
 */
function hojeEmSaoPaulo(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

interface AnuncioPapaiNoelProps {
  /** Entrada escalonada da cena do menu — a mesma de quem está acima do cartão. */
  entrada: MotionProps;
}

export function AnuncioPapaiNoel({ entrada }: AnuncioPapaiNoelProps) {
  const reducedMotion = useReducedMotion();
  const noAr = hojeEmSaoPaulo() <= ULTIMO_DIA;
  const vitrine = useVitrineVirtual(noAr);
  const [capaFalhou, setCapaFalhou] = useState(false);

  const campanha = vitrine.data?.campanhas.find((c) => c.slug === SLUG);
  if (!noAr || !campanha || (!campanha.tem_horario && !campanha.tem_gravado)) return null;

  const dia = dataPorExtenso(ULTIMO_DIA);
  let frase: string;
  if (campanha.tem_horario && campanha.tem_gravado) {
    frase = `No dia ${dia}, ele liga por vídeo e chama pelo nome quem você quiser surpreender. Prefere sem hora marcada? Ele também grava um vídeo especial.`;
  } else if (campanha.tem_horario) {
    frase = `No dia ${dia}, ele liga por vídeo e chama pelo nome quem você quiser surpreender.`;
  } else {
    frase =
      "Os horários ao vivo acabaram, mas ele ainda grava um vídeo especial para quem você quiser surpreender.";
  }

  // "A partir de" só entre os formatos com vaga: oferecer o preço de um formato esgotado engana.
  const precos = [
    campanha.tem_horario ? campanha.price_live : null,
    campanha.tem_gravado ? campanha.price_recorded : null,
  ]
    .map(apiMoneyToNumber)
    .filter((valor) => valor > 0);
  const aPartirDe = precos.length ? Math.min(...precos) : null;

  return (
    <motion.a
      {...entrada}
      href={DESTINO}
      whileTap={reducedMotion ? undefined : { scale: 0.98 }}
      className="block w-full overflow-hidden rounded-2xl border border-gold/40 bg-lamp-cloud/10 text-left shadow-lg transition-colors hover:border-gold/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold"
    >
      {campanha.cover_url && !capaFalhou && (
        <img
          src={assetUrl(campanha.cover_url)}
          alt=""
          loading="lazy"
          onError={() => setCapaFalhou(true)}
          className="h-40 w-full object-cover object-[50%_35%]"
        />
      )}
      <div className="space-y-2 p-4">
        <p className="text-xs font-bold uppercase tracking-[0.25em] text-gold">
          Novidade de Natal
        </p>
        <p className="font-display text-xl leading-tight text-on-color">{campanha.title}</p>
        <p className="text-sm leading-relaxed text-on-color/75">{frase}</p>
        {aPartirDe !== null && (
          <p className="text-sm text-on-color/75">
            A partir de <strong className="text-on-color">R$ {formatBRL(aPartirDe)}</strong>
          </p>
        )}
        <span className="mt-1 inline-flex min-h-[44px] items-center rounded-full bg-gold px-5 text-sm font-bold text-ink">
          Ver como funciona
        </span>
        <p className="text-xs text-on-color/50">alo.mantoproducoes.com.br</p>
      </div>
    </motion.a>
  );
}
