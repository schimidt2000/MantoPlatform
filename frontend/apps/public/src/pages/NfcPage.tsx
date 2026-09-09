import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { assetUrl } from "@manto/api-client";
import {
  aberturaJaVista,
  marcarAberturaVista,
  useEnviarRecado,
  useNfcResolution,
} from "../lib/nfc";

/**
 * Página pública da tag NFC da luminária (features 255, 261 e 297) —
 * `app.mantoproducoes.com.br/nfc/<code>`.
 *
 * A cliente encosta o celular na peça, à noite, ao lado da luminária acesa, e cai aqui sem login.
 * A URL gravada na tag é imutável; TODO o conteúdo vem do servidor (`useNfcResolution`), então
 * esta página evolui sem regravar tag nenhuma. Código inexistente/desativado chega como
 * `product: null` com `deliveries: []` e a página mostra o MESMO menu, só sem a mensagem especial
 * — não existe caminho de erro visível (SC-006: nunca revelar se um código existe).
 *
 * O palco é permanente: céu noturno com estrelinhas piscando, nuvens na base, e a estrela "Magia
 * de Sonhar" que **acende** como a lâmpada de verdade acende. Ele nunca desmonta — quem troca é
 * só a cena por cima dele.
 *
 * ```
 *   capa ──toque──▶ abertura ──fim/pular──▶ menu ──▶ mensagem ──envio──▶ agradecimento
 *     │                                      ▲          │                     │
 *     └── sem vídeo de abertura, ou aparelho ┘          └─────voltar──────────┘
 *         que já viu: entra direto no menu
 * ```
 *
 * A capa existe por uma razão técnica que virou vantagem: navegador de celular não deixa vídeo
 * começar sozinho **com áudio**. O toque da cliente é o que libera o som — e é o mesmo gesto que
 * abre o portal. Nada toca antes dele.
 */

/** As cenas da página. `null` enquanto a resolução não chegou: só o palco na tela. */
type Cena = "capa" | "abertura" | "menu" | "mensagem";

/** O agradecimento é derivado do envio do recado, não um estado à parte que precise ser sincronizado. */
type CenaVisivel = Cena | "agradecimento";

/** Tetos do servidor (`contracts/nfc-api.md` §4) espelhados aqui só para o contador e o `maxLength`. */
const LIMITE_RECADO = 1000;
const LIMITE_NOME = 120;

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

/* ------------------------------------------------------------------ *
 * Classes repetidas — um lugar só para o alvo de toque e o foco
 * ------------------------------------------------------------------ */

/**
 * Base de todo botão/link da página. `min-h-[48px]` é o alvo de toque de dedo à noite (a spec
 * exige 44px; sobra folga), e o foco visível é obrigatório para quem navega por teclado.
 */
const BOTAO_BASE =
  "inline-flex min-h-[48px] items-center justify-center gap-2 rounded-full px-6 text-base font-bold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold disabled:cursor-not-allowed disabled:opacity-60";

/** Vidro claro da nuvem: legível no escuro sem competir com o dourado. */
const VIDRO = "border border-lamp-cloud/30 bg-lamp-cloud/10 text-on-color hover:bg-lamp-cloud/20";

/** Destino principal da cena: o dourado da marca sobre o céu escuro. */
const BOTAO_PRIMARIO = `${BOTAO_BASE} w-full bg-gold text-ink shadow-lg hover:bg-gold/90`;

/** Destinos secundários do menu. */
const BOTAO_SECUNDARIO = `${BOTAO_BASE} w-full ${VIDRO}`;

/** Volta ao menu no alto da cena: mesmo alvo de toque, largura do próprio texto. */
const BOTAO_VOLTAR = `${BOTAO_BASE} px-5 text-sm ${VIDRO}`;

/** Volta ao menu no fim da cena: presente sem disputar atenção com o formulário. */
const BOTAO_VOLTAR_DISCRETO = `${BOTAO_BASE} w-full text-sm font-semibold text-on-color/70 hover:bg-lamp-cloud/10`;

/** Campo de texto do recado sobre o palco noturno. */
const CAMPO_BASE =
  "w-full rounded-lg border bg-lamp-cloud/[0.08] px-3 text-left text-base text-on-color placeholder:text-on-color/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold";

/* ------------------------------------------------------------------ *
 * A luminária — o palco permanente
 * ------------------------------------------------------------------ */

interface LuminariaProps {
  /**
   * Nas cenas de vídeo a peça recua para dar a tela ao filme, sem nunca sumir: ela é a
   * identidade da luminária física e continua ali, menor, como assinatura.
   */
  compacta: boolean;
}

/**
 * A luminária "Magia de Sonhar": o contorno chega apagado e o miolo ACENDE revelando o escrito,
 * como a lâmpada de verdade acende. Vive FORA do `AnimatePresence` de propósito — trocar de cena
 * não pode reacender a estrela na cara da cliente.
 *
 * A mudança de tamanho é transição de CSS (some sozinha com `prefers-reduced-motion`), não alvo
 * de animação: assim o palco tem o tamanho certo já no primeiro quadro de cada cena.
 */
function Luminaria({ compacta }: LuminariaProps) {
  const reducedMotion = useReducedMotion();
  const tamanho = `${compacta ? "h-24 w-24" : "h-56 w-56"} transition-[height,width] duration-300 ease-out motion-reduce:transition-none`;

  return (
    <motion.div
      initial={reducedMotion ? undefined : { scale: 0.4, opacity: 0, rotate: -8 }}
      animate={{ scale: 1, opacity: 1, rotate: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1.2, 0.36, 1] }}
      className="relative"
      aria-hidden="true"
    >
      <svg viewBox="0 0 220 232" className={tamanho}>
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
        animate={reducedMotion ? { opacity: 1 } : { opacity: [0, 0.35, 1, 0.85, 1] }}
        transition={
          reducedMotion ? undefined : { duration: 0.5, delay: 0.4, times: [0, 0.35, 0.6, 0.8, 1] }
        }
      >
        <svg viewBox="0 0 220 232" className={tamanho}>
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
          <svg viewBox="0 0 220 232" className={tamanho}>
            <polygon points={STAR_POINTS} className="fill-lamp-glow/40" strokeLinejoin="round" />
          </svg>
        </motion.div>
      )}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ *
 * Ícones dos destinos
 * ------------------------------------------------------------------ */

function IconePlay() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M8 5.14v13.72c0 .8.87 1.29 1.55.87l10.8-6.86a1.03 1.03 0 0 0 0-1.74L9.55 4.27A1.03 1.03 0 0 0 8 5.14Z" />
    </svg>
  );
}

function IconeSpotify() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm4.59 14.42a.75.75 0 0 1-1.03.25c-2.82-1.72-6.37-2.11-10.55-1.15a.75.75 0 1 1-.33-1.46c4.55-1.04 8.48-.59 11.66 1.34.35.21.46.67.25 1.02Zm1.22-2.72a.94.94 0 0 1-1.29.31c-3.23-1.98-8.15-2.56-11.97-1.4a.94.94 0 1 1-.54-1.8c4.36-1.31 9.78-.67 13.49 1.61.44.27.58.85.31 1.28Zm.11-2.84C14.05 8.56 7.9 8.35 4.2 9.47a1.12 1.12 0 1 1-.65-2.15c4.25-1.29 11.04-1.04 15.39 1.54a1.12 1.12 0 1 1-1.14 1.93Z" />
    </svg>
  );
}

function IconeInstagram() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M12 2.2c3.2 0 3.6 0 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.26.07 1.64.07 4.85s0 3.6-.07 4.85c-.05 1.17-.25 1.8-.41 2.23a3.7 3.7 0 0 1-.9 1.38c-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.26.06-1.64.07-4.85.07s-3.6 0-4.85-.07c-1.17-.05-1.8-.25-2.23-.41a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.2 15.6 2.2 15.2 2.2 12s0-3.6.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.4 2.2 8.8 2.2 12 2.2Zm0 1.8c-3.15 0-3.52 0-4.76.07-1.08.05-1.66.23-2.05.38-.51.2-.88.44-1.26.82-.38.38-.62.75-.82 1.26-.15.39-.33.97-.38 2.05C2.66 9.83 2.65 10.2 2.65 12s0 2.17.07 3.42c.05 1.08.23 1.66.38 2.05.2.51.44.88.82 1.26.38.38.75.62 1.26.82.39.15.97.33 2.05.38 1.24.06 1.61.07 4.76.07s3.52 0 4.76-.07c1.08-.05 1.66-.23 2.05-.38.51-.2.88-.44 1.26-.82.38-.38.62-.75.82-1.26.15-.39.33-.97.38-2.05.06-1.25.07-1.62.07-3.42s0-2.17-.07-3.42c-.05-1.08-.23-1.66-.38-2.05a2.9 2.9 0 0 0-.82-1.26 2.9 2.9 0 0 0-1.26-.82c-.39-.15-.97-.33-2.05-.38C15.52 4 15.15 4 12 4Zm0 3.1a4.9 4.9 0 1 1 0 9.8 4.9 4.9 0 0 1 0-9.8Zm0 1.8a3.1 3.1 0 1 0 0 6.2 3.1 3.1 0 0 0 0-6.2Zm5.1-2.98a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3Z" />
    </svg>
  );
}

function IconeVoltar() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
      <path d="M14.7 5.3a1 1 0 0 1 0 1.4L9.4 12l5.3 5.3a1 1 0 0 1-1.4 1.4l-6-6a1 1 0 0 1 0-1.4l6-6a1 1 0 0 1 1.4 0Z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * A página
 * ------------------------------------------------------------------ */

export function NfcPage() {
  const { code = "" } = useParams<{ code: string }>();
  const resolution = useNfcResolution(code);
  const reducedMotion = useReducedMotion();
  const recado = useEnviarRecado(code);

  const [cena, setCena] = useState<Cena | null>(null);
  // Quantas trocas de cena já houve nesta visita — só a PRIMEIRA cena espera a estrela acender.
  const [trocas, setTrocas] = useState(0);
  const [mensagem, setMensagem] = useState("");
  const [nome, setNome] = useState("");
  const [videoFalhou, setVideoFalhou] = useState(false);
  // A cena de entrada é decidida UMA vez: um refetch em segundo plano não pode jogar a cliente
  // de volta para a capa no meio do vídeo.
  const cenaDecidida = useRef(false);

  const dados = resolution.data;
  const instagramUrl = dados?.instagram_url;
  const spotifyUrl = dados?.spotify_url;
  const introUrl = dados?.intro_video_url;
  // Feature 261: por ora no máximo uma entrega de vídeo por tag. Só chega aqui entrega PRONTA.
  const videoDelivery = dados?.deliveries.find((d) => d.kind === "video");

  useEffect(() => {
    // `isPending` cobre o único caso em que ainda não dá para decidir. Erro de rede (com
    // `retry: false`) sai de pendente sem dados e cai no menu genérico — nunca numa tela de erro.
    if (cenaDecidida.current || resolution.isPending) return;
    cenaDecidida.current = true;
    const temAbertura = Boolean(resolution.data?.intro_video_url);
    setCena(temAbertura && !aberturaJaVista(code) ? "capa" : "menu");
  }, [resolution.isPending, resolution.data, code]);

  /**
   * O `<video>` da abertura só monta DEPOIS que a capa termina de sair (`mode="wait"`), então um
   * efeito preso à troca de cena ainda encontraria `null` aqui. O callback ref roda no instante
   * do mount, ainda dentro da janela de ativação aberta pelo toque — que é o que libera o ÁUDIO,
   * já que o `autoPlay` sozinho não basta em parte dos navegadores de celular.
   *
   * A recusa é engolida de propósito: os controles estão visíveis e a cliente toca de novo. Um
   * aviso de erro aqui só assustaria quem está com a luminária na mão.
   */
  const tocarAbertura = useCallback((video: HTMLVideoElement | null) => {
    video?.play().catch(() => undefined);
  }, []);

  // Conteúdo textual sobe em fases, depois que a estrela acendeu (~0.8s).
  const enter = (delay: number) =>
    reducedMotion
      ? {}
      : {
          initial: { opacity: 0, y: 14 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.3, delay, ease: "easeOut" as const },
        };

  /**
   * Escalonamento de entrada de cada cena. A primeira cena da visita entra atrás da estrela
   * acendendo; as seguintes entram logo depois da saída da anterior, senão a página parece travada.
   */
  const atraso = (indice: number) => (trocas === 0 ? 0.8 : 0.05) + indice * 0.08;

  function irPara(proxima: Cena) {
    setTrocas((n) => n + 1);
    setCena(proxima);
  }

  function encerrarAbertura() {
    // Vale para o fim, para o "Pular" e para a falha do arquivo: o aparelho já teve sua chance de
    // ver a abertura, e uma abertura quebrada não pode prender a cliente numa capa eterna.
    marcarAberturaVista();
    irPara("menu");
  }

  function voltarAoMenu() {
    // Sair da mensagem zera o envio, senão voltar depois cairia direto no agradecimento antigo.
    // O texto só é apagado quando ele JÁ FOI enviado — rascunho da cliente não se joga fora.
    if (recado.enviado) {
      setMensagem("");
      setNome("");
    }
    recado.limpar();
    irPara("menu");
  }

  function escreverOutro() {
    recado.limpar();
    setMensagem("");
    setNome("");
  }

  function enviarRecado(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const texto = mensagem.trim();
    if (recado.enviando || !texto) return;
    const assinatura = nome.trim();
    recado.enviar({ message: texto, ...(assinatura ? { author_name: assinatura } : {}) });
  }

  const cenaVisivel: CenaVisivel | null =
    cena === "mensagem" && recado.enviado ? "agradecimento" : cena;
  const compacta = cenaVisivel === "abertura" || cenaVisivel === "mensagem";
  const erroDoTexto = recado.camposComErro.message;

  let corpo: ReactNode = null;

  if (cenaVisivel === "capa") {
    corpo = (
      <>
        <motion.p
          {...enter(atraso(0))}
          className="text-xs font-bold uppercase tracking-[0.3em] text-gold"
        >
          Manto Produções
        </motion.p>
        <motion.h1 {...enter(atraso(1))} className="font-display text-3xl leading-tight text-on-color">
          A magia da Manto também na sua casa
        </motion.h1>
        <motion.p {...enter(atraso(2))} className="text-base leading-relaxed text-on-color/70">
          Toque para abrir o portal da sua luminária. A abertura tem som — vale ouvir com o volume
          ligado.
        </motion.p>
        <motion.button
          {...enter(atraso(3))}
          type="button"
          onClick={() => irPara("abertura")}
          whileTap={reducedMotion ? undefined : { scale: 0.97 }}
          className={`${BOTAO_PRIMARIO} mt-2`}
        >
          <IconePlay />
          Tocar para abrir
        </motion.button>
      </>
    );
  } else if (cenaVisivel === "abertura" && introUrl) {
    corpo = (
      <>
        <h1 className="sr-only">Abertura da Manto Produções</h1>
        <motion.video
          {...enter(atraso(0))}
          ref={tocarAbertura}
          src={assetUrl(introUrl)}
          autoPlay
          playsInline
          controls
          controlsList="nodownload noplaybackrate noremoteplayback"
          disablePictureInPicture
          preload="auto"
          onEnded={encerrarAbertura}
          onError={encerrarAbertura}
          className="max-h-[60vh] w-full rounded-xl border border-lamp-cloud/20 bg-ink object-contain shadow-lg"
        />
        {/* "Pular" sempre visível: ninguém fica refém de um vídeo que já viu. */}
        <motion.button
          {...enter(atraso(1))}
          type="button"
          onClick={encerrarAbertura}
          whileTap={reducedMotion ? undefined : { scale: 0.97 }}
          className={BOTAO_SECUNDARIO}
        >
          Pular abertura
        </motion.button>
      </>
    );
  } else if (cenaVisivel === "menu") {
    corpo = (
      <>
        <motion.p
          {...enter(atraso(0))}
          className="text-xs font-bold uppercase tracking-[0.3em] text-gold"
        >
          Manto Produções
        </motion.p>
        <motion.h1 {...enter(atraso(1))} className="font-display text-3xl leading-tight text-on-color">
          A magia da Manto também na sua casa
        </motion.h1>
        <motion.p {...enter(atraso(2))} className="text-base leading-relaxed text-on-color/70">
          Escolha por onde continuar.
        </motion.p>

        <div className="flex w-full flex-col gap-3">
          {/* Só existe quando a tag tem vídeo PRONTO. Sem ele, o menu é o mesmo de qualquer
              código — é assim que a página não conta se um código existe (SC-006). */}
          {videoDelivery && (
            <motion.button
              {...enter(atraso(3))}
              type="button"
              onClick={() => irPara("mensagem")}
              whileTap={reducedMotion ? undefined : { scale: 0.97 }}
              className={BOTAO_PRIMARIO}
            >
              <IconePlay />
              Ver a mensagem especial
            </motion.button>
          )}

          {/* CTA só quando o servidor respondeu: botão sem destino é botão morto (Princípio V). */}
          {spotifyUrl && (
            <motion.a
              {...enter(atraso(4))}
              href={spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
              whileTap={reducedMotion ? undefined : { scale: 0.97 }}
              className={BOTAO_SECUNDARIO}
            >
              <IconeSpotify />
              Ouvir no Spotify
            </motion.a>
          )}

          {instagramUrl && (
            <motion.a
              {...enter(atraso(5))}
              href={instagramUrl}
              target="_blank"
              rel="noopener noreferrer"
              whileTap={reducedMotion ? undefined : { scale: 0.97 }}
              className={BOTAO_SECUNDARIO}
            >
              <IconeInstagram />
              Seguir {instagramHandle(instagramUrl)}
            </motion.a>
          )}
        </div>
      </>
    );
  } else if (cenaVisivel === "mensagem" && videoDelivery) {
    // O palco nasce do tamanho certo pelas dimensões que o payload manda: sem isso o layout
    // PULA quando o `<video>` descobre sozinho que é retrato. Depois da 297 quase toda entrega
    // sai 9:16, mas uma entrega sem moldura pode ser deitada — e aí o quadro deitado evita a
    // tarja preta gigante.
    const retrato = videoDelivery.height >= videoDelivery.width;
    const palco = retrato ? "aspect-[9/16] max-w-[288px]" : "aspect-video max-w-md";

    corpo = (
      <>
        <motion.button
          {...enter(atraso(0))}
          type="button"
          onClick={voltarAoMenu}
          whileTap={reducedMotion ? undefined : { scale: 0.97 }}
          className={`${BOTAO_VOLTAR} self-start`}
        >
          <IconeVoltar />
          Voltar ao menu
        </motion.button>

        <motion.h1
          {...enter(atraso(1))}
          className="font-display text-2xl leading-tight text-on-color"
        >
          {videoDelivery.title || "Um vídeo especial para você"}
        </motion.h1>

        <motion.div
          {...enter(atraso(2))}
          className={`${palco} mx-auto w-full overflow-hidden rounded-xl border border-lamp-cloud/20 bg-ink shadow-lg`}
        >
          {videoFalhou ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 p-6">
              <p className="text-sm leading-relaxed text-on-color/80">
                Não conseguimos abrir o vídeo agora. Ele continua guardado para você — confira a
                conexão e tente de novo.
              </p>
              <button
                type="button"
                onClick={() => setVideoFalhou(false)}
                className={BOTAO_VOLTAR}
              >
                Tentar de novo
              </button>
            </div>
          ) : (
            // As mesmas dimensões viajam como atributo: dão a proporção intrínseca ao navegador
            // antes de qualquer byte de mídia chegar, e o quadro acima já reservou a altura.
            <video
              src={assetUrl(videoDelivery.media_url)}
              width={videoDelivery.width}
              height={videoDelivery.height}
              controls
              playsInline
              controlsList="nodownload noplaybackrate noremoteplayback"
              preload="metadata"
              onError={() => setVideoFalhou(true)}
              className="h-full w-full object-contain"
            />
          )}
        </motion.div>

        {dados?.aceita_recado && (
          <motion.form
            {...enter(atraso(3))}
            onSubmit={enviarRecado}
            noValidate
            className="w-full space-y-4 text-left"
          >
            <div>
              <label htmlFor="recado" className="mb-2 block text-sm font-bold text-on-color">
                Escreva um recado para a Manto
              </label>
              <textarea
                id="recado"
                value={mensagem}
                onChange={(e) => setMensagem(e.target.value)}
                maxLength={LIMITE_RECADO}
                rows={4}
                required
                aria-describedby="recado-contador recado-erro"
                aria-invalid={erroDoTexto ? true : undefined}
                placeholder="Conte o que essa mensagem despertou aí na sua casa..."
                className={`${CAMPO_BASE} min-h-28 py-3 ${erroDoTexto ? "border-red" : "border-lamp-cloud/30"}`}
              />
              <div className="mt-1 flex items-start justify-between gap-3">
                {/* O erro do servidor aponta o campo culpado e NUNCA apaga o que foi digitado. */}
                <p id="recado-erro" className="text-sm text-red-soft">
                  {erroDoTexto}
                </p>
                <p
                  id="recado-contador"
                  className={`shrink-0 text-xs tabular-nums ${
                    mensagem.length >= LIMITE_RECADO ? "text-gold" : "text-on-color/50"
                  }`}
                >
                  {mensagem.length}/{LIMITE_RECADO}
                </p>
              </div>
            </div>

            <div>
              <label htmlFor="recado-nome" className="mb-2 block text-sm font-bold text-on-color">
                Seu nome <span className="font-normal text-on-color/50">(opcional)</span>
              </label>
              <input
                id="recado-nome"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                maxLength={LIMITE_NOME}
                placeholder="Como podemos te chamar?"
                className={`${CAMPO_BASE} h-12 border-lamp-cloud/30`}
              />
            </div>

            {recado.erroGeral && (
              <p role="alert" className="text-sm text-red-soft">
                {recado.erroGeral}
              </p>
            )}

            <button
              type="submit"
              disabled={recado.enviando || mensagem.trim().length === 0}
              className={BOTAO_PRIMARIO}
            >
              {recado.enviando ? "Enviando..." : "Enviar recado"}
            </button>
            {mensagem.trim().length === 0 && (
              // Botão desabilitado sem explicação é botão morto: a frase diz o que falta.
              <p className="text-center text-xs text-on-color/50">
                Escreva seu recado para liberar o envio.
              </p>
            )}
          </motion.form>
        )}

        {/* O caminho de volta também embaixo: depois de rolar o formulário, o de cima saiu da tela. */}
        <motion.button
          {...enter(atraso(4))}
          type="button"
          onClick={voltarAoMenu}
          className={BOTAO_VOLTAR_DISCRETO}
        >
          <IconeVoltar />
          Voltar ao menu
        </motion.button>
      </>
    );
  } else if (cenaVisivel === "agradecimento") {
    corpo = (
      <>
        <motion.p
          {...enter(atraso(0))}
          className="text-xs font-bold uppercase tracking-[0.3em] text-gold"
        >
          Recado enviado
        </motion.p>
        <motion.h1 {...enter(atraso(1))} className="font-display text-3xl leading-tight text-on-color">
          Obrigada por escrever de volta
        </motion.h1>
        <motion.p {...enter(atraso(2))} className="text-base leading-relaxed text-on-color/70">
          Seu recado chegou à equipe da Manto e vai ser lido com carinho. A luminária continua
          acesa aí — e o portal, aberto sempre que você encostar o celular.
        </motion.p>
        <motion.button
          {...enter(atraso(3))}
          type="button"
          onClick={escreverOutro}
          whileTap={reducedMotion ? undefined : { scale: 0.97 }}
          className={BOTAO_PRIMARIO}
        >
          Escrever outro recado
        </motion.button>
        <motion.button
          {...enter(atraso(4))}
          type="button"
          onClick={voltarAoMenu}
          className={BOTAO_VOLTAR_DISCRETO}
        >
          <IconeVoltar />
          Voltar ao menu
        </motion.button>
      </>
    );
  } else if (cenaVisivel === "mensagem" || cenaVisivel === "abertura") {
    // Rede de segurança: cena de mídia sem mídia (entrega ou abertura que sumiu entre um render e
    // outro). Devolve a cliente ao menu com um toque, sem nunca dizer que algo deu errado.
    corpo = (
      <motion.button
        {...enter(atraso(0))}
        type="button"
        onClick={voltarAoMenu}
        className={BOTAO_SECUNDARIO}
      >
        <IconeVoltar />
        Voltar ao menu
      </motion.button>
    );
  }

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
            reducedMotion ? { opacity: 0.5 } : { opacity: [0.15, 0.9, 0.15], scale: [1, 1.4, 1] }
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
        <Luminaria compacta={compacta} />

        {/* A máquina de cenas: `mode="wait"` faz a cena velha sair inteira antes de a nova entrar,
            e a `key` discriminante é o que dá à AnimatePresence o sinal da troca (molde de
            `components/ProductGallery.tsx`). Com movimento reduzido a troca é instantânea, e
            nenhum conteúdo depende da animação para existir. */}
        <AnimatePresence mode="wait">
          {cenaVisivel && (
            <motion.section
              key={cenaVisivel}
              className="flex w-full flex-col items-center gap-5"
              initial={reducedMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reducedMotion ? undefined : { opacity: 0, y: -16 }}
              transition={{ duration: reducedMotion ? 0 : 0.22, ease: "easeOut" }}
            >
              {corpo}
            </motion.section>
          )}
        </AnimatePresence>
      </main>

      <motion.footer {...enter(1.25)} className="relative mt-10 text-xs text-on-color/40">
        mantoproducoes.com.br
      </motion.footer>
    </div>
  );
}
