import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion, type Transition } from "framer-motion";
import { AlertTriangle, Film, Frame, Trash2, Upload } from "lucide-react";
import { assetUrl } from "@manto/api-client";
import {
  Badge,
  Button,
  cn,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
} from "@manto/ui";
import {
  useRemoverAberturaNfc,
  useRemoverMolduraNfc,
  useSalvarAberturaNfc,
  useSalvarMolduraNfc,
} from "../../lib/nfc";
import { UploadProgressBar } from "../UploadProgressBar";
import { fieldError, NFC_VIDEO_ACCEPT } from "./helpers";

export interface MolduraDialogProps {
  aberto: boolean;
  onFechar: () => void;
}

/** PNG só — a moldura precisa de canal alfa (espelha `NFC_MOLDURA_EXTENSOES` de `app/constants.py`). */
const MOLDURA_ACCEPT = ".png,image/png";

/** O vídeo entregue é sempre em pé; fora de 9:16 a moldura estica na conversão. */
const PROPORCAO_RETRATO = 9 / 16;

/** Folga de ~2%: 1080×1920 e 1000×1800 passam; 3:4, 2:3 e paisagem avisam. */
const TOLERANCIA_PROPORCAO = 0.02;

/**
 * Fundo xadrez da prévia — o único jeito de VER a transparência do PNG.
 *
 * Sem ele, uma moldura opaca (que cobriria o vídeo inteiro) fica idêntica a uma correta sobre
 * fundo branco, e o erro só apareceria no vídeo da cliente. Os quadrados vêm de dois
 * `linear-gradient` iguais, deslocados meio quadrado, em classes utilitárias: nada de arquivo
 * `.css` solto nem `style={{...}}` (Princípio II). Os dois tons saem dos tokens do tema
 * (`--c-panel` no fundo, `--c-line` nos quadrados), então o xadrez acompanha claro e escuro.
 */
const FUNDO_XADREZ =
  // Cada classe fica INTEIRA num literal só: o Tailwind lê o texto do arquivo, e um token
  // partido entre duas linhas simplesmente não vira CSS — o xadrez sumiria sem erro nenhum.
  "bg-panel [background-size:16px_16px] [background-position:0_0,8px_8px] " +
  "[background-image:linear-gradient(45deg,rgb(var(--c-line))_25%,transparent_25%,transparent_75%,rgb(var(--c-line))_75%),linear-gradient(45deg,rgb(var(--c-line))_25%,transparent_25%,transparent_75%,rgb(var(--c-line))_75%)]";

const TRANSICAO: Transition = { duration: 0.2, ease: "easeOut" };

/**
 * O que já se sabe sobre cada arquivo único. `verificando` existe porque a presença é descoberta
 * pelo carregamento da própria prévia (ver `presencaDe`), e não por uma resposta em JSON.
 */
type EstadoArquivo = "verificando" | "cadastrado" | "ausente";

const ROTULO_MOLDURA: Record<EstadoArquivo, string> = {
  verificando: "Verificando…",
  cadastrado: "Cadastrada",
  ausente: "Nenhuma",
};

const ROTULO_ABERTURA: Record<EstadoArquivo, string> = {
  verificando: "Verificando…",
  cadastrado: "Cadastrado",
  ausente: "Nenhum",
};

/** Dimensões do PNG escolhido, presas à URL medida — trocar de arquivo rápido não mistura. */
interface MedidaDaMoldura {
  url: string;
  largura: number;
  altura: number;
}

/** `assetUrl` só devolve `undefined` para caminho vazio — impossível aqui; o `?? ""` é só o tipo. */
function urlDoServidor(caminho: string): string {
  return assetUrl(caminho) ?? "";
}

/**
 * Quem responde se o arquivo existe.
 *
 * Não há GET em JSON deste estado: `GET /api/3d/nfc/moldura` devolve o PNG (ou 404) e
 * `/api/nfc/abertura/video` devolve o vídeo (ou 404). Então, ao abrir, quem responde é o próprio
 * carregamento da prévia (`onLoad`/`onError`, a "sonda"). Depois do primeiro PUT/DELETE da sessão
 * a resposta do servidor vale mais e é ela que manda — `undefined` é justamente "ainda não
 * gravamos nada nesta sessão".
 */
function presencaDe(urlSalva: string | null | undefined, sonda: EstadoArquivo): EstadoArquivo {
  if (urlSalva === undefined) return sonda;
  return urlSalva === null ? "ausente" : "cadastrado";
}

/** URL da prévia: a que o servidor acabou de devolver ou, antes disso, a da sonda. */
function srcDe(urlSalva: string | null | undefined, caminhoDaSonda: string): string | null {
  if (urlSalva === undefined) return urlDoServidor(caminhoDaSonda);
  return urlSalva === null ? null : urlDoServidor(urlSalva);
}

/**
 * Os DOIS arquivos únicos do sistema NFC (feature 297): a moldura e o vídeo de abertura.
 *
 * Não pertencem a nenhuma tag — valem para todas as luminárias de uma vez, e é por isso que
 * moram num diálogo do cabeçalho da aba Vídeos, longe do envio de uma tag específica.
 *
 * A moldura espera um "Salvar" explícito: a prévia sobre o xadrez e o aviso de proporção existem
 * para serem LIDOS antes de gravar. O vídeo de abertura sobe assim que é escolhido (mesmo padrão
 * do `VideoDialog`), porque ali não há nada para decidir — só a barra de progresso a acompanhar.
 */
export function MolduraDialog({ aberto, onFechar }: MolduraDialogProps) {
  const reduceMotion = useReducedMotion();
  const inputMoldura = useRef<HTMLInputElement>(null);
  const inputAbertura = useRef<HTMLInputElement>(null);

  /** Marca de versão da sonda — ver o bloco de reabertura, logo abaixo dos estados. */
  const [versao, setVersao] = useState(() => Date.now());
  const estavaAberto = useRef(false);
  const [sondaMoldura, setSondaMoldura] = useState<EstadoArquivo>("verificando");
  const [sondaAbertura, setSondaAbertura] = useState<EstadoArquivo>("verificando");
  /** `undefined` = nada gravado nesta sessão; `null` = o servidor disse que não há arquivo. */
  const [molduraSalva, setMolduraSalva] = useState<string | null | undefined>(undefined);
  const [aberturaSalva, setAberturaSalva] = useState<string | null | undefined>(undefined);
  const [arquivoMoldura, setArquivoMoldura] = useState<File | null>(null);
  const [previaLocal, setPreviaLocal] = useState<string | null>(null);
  const [medida, setMedida] = useState<MedidaDaMoldura | null>(null);
  /** `null` esconde a barra; `0..1` vem do `xhr.upload.onprogress`. */
  const [progressoAbertura, setProgressoAbertura] = useState<number | null>(null);
  const [confirmando, setConfirmando] = useState<"moldura" | "abertura" | null>(null);

  const salvarMoldura = useSalvarMolduraNfc();
  const removerMoldura = useRemoverMolduraNfc();
  const salvarAbertura = useSalvarAberturaNfc();
  const removerAbertura = useRemoverAberturaNfc();

  // Cada abertura refaz a sonda com marca nova. Os dois arquivos têm NOME FIXO e são sobrescritos
  // no lugar, e o servidor manda `max-age` (300 s na moldura, 3600 s na abertura): sem a marca,
  // quem trocou a moldura ontem continuaria vendo a antiga hoje.
  //
  // Isto é ajuste de estado DURANTE a render (padrão do React para reagir à mudança de uma prop),
  // e não um `useEffect`, de propósito: no efeito a marca só mudaria DEPOIS do primeiro commit, e
  // a prévia já teria pedido o arquivo com a marca velha — um pedido a mais e, pior, um lampejo
  // da moldura antiga saída do cache. Roda uma vez por abertura porque o `ref` fecha a condição.
  if (aberto !== estavaAberto.current) {
    estavaAberto.current = aberto;
    if (aberto) {
      setVersao(Date.now());
      setSondaMoldura("verificando");
      setSondaAbertura("verificando");
      setMolduraSalva(undefined);
      setAberturaSalva(undefined);
    }
  }

  // A prévia local é um object URL: sem revogar, cada arquivo escolhido fica preso na memória da
  // aba até o F5. A limpeza roda depois que o `<img>` novo já está no DOM, então nada pisca.
  useEffect(() => {
    if (!previaLocal) return;
    return () => URL.revokeObjectURL(previaLocal);
  }, [previaLocal]);

  const estadoMoldura = presencaDe(molduraSalva, sondaMoldura);
  const estadoAbertura = presencaDe(aberturaSalva, sondaAbertura);
  const srcMoldura = srcDe(molduraSalva, `/api/3d/nfc/moldura?v=${versao}`);
  const srcAbertura = srcDe(aberturaSalva, `/api/nfc/abertura/video?v=${versao}`);

  // A medida só vale para o arquivo que está na tela agora (a leitura é assíncrona).
  const medidaAtual = medida !== null && medida.url === previaLocal ? medida : null;
  const foraDeRetrato =
    medidaAtual !== null &&
    medidaAtual.altura > 0 &&
    Math.abs(medidaAtual.largura / medidaAtual.altura - PROPORCAO_RETRATO) > TOLERANCIA_PROPORCAO;

  const erroMoldura = salvarMoldura.error
    ? (fieldError(salvarMoldura.error, "file") ?? salvarMoldura.error.message)
    : null;
  const erroAbertura = salvarAbertura.error
    ? (fieldError(salvarAbertura.error, "file") ?? salvarAbertura.error.message)
    : null;
  const enviando = salvarMoldura.isPending || salvarAbertura.isPending;

  const removendo =
    confirmando === "moldura" ? removerMoldura.isPending : removerAbertura.isPending;
  const erroRemocao = confirmando === "moldura" ? removerMoldura.error : removerAbertura.error;
  const textoRemocao =
    confirmando === "moldura"
      ? {
          titulo: "Remover a moldura",
          descricao:
            "Os próximos vídeos enviados saem SEM moldura, mesmo com a caixinha marcada. Os vídeos já entregues continuam como estão.",
          confirmar: "Remover moldura",
        }
      : {
          titulo: "Remover o vídeo de abertura",
          descricao:
            "A página da luminária passa a abrir direto no menu, sem a capa. O arquivo é apagado do servidor.",
          confirmar: "Remover abertura",
        };

  function escolherMoldura(file: File) {
    salvarMoldura.reset();
    const url = URL.createObjectURL(file);
    setArquivoMoldura(file);
    setPreviaLocal(url);
    setMedida(null);
    // `new Image()` é o único jeito de saber a proporção ANTES de enviar. Arquivo que o navegador
    // não decodifica simplesmente não gera aviso — quem recusa PNG inválido é o servidor.
    const imagem = new Image();
    imagem.onload = () =>
      setMedida({ url, largura: imagem.naturalWidth, altura: imagem.naturalHeight });
    imagem.src = url;
  }

  function limparEscolha() {
    setArquivoMoldura(null);
    setPreviaLocal(null);
    setMedida(null);
  }

  function enviarMoldura() {
    if (!arquivoMoldura) return;
    salvarMoldura.mutate(
      { file: arquivoMoldura },
      {
        // A escolha só se desfaz no SUCESSO: erro de validação (o PNG opaco) mantém o arquivo e a
        // prévia na tela, com a mensagem do servidor ao lado, para tentar de novo (Princípio V).
        onSuccess: (resposta) => {
          setMolduraSalva(resposta.moldura_url);
          limparEscolha();
        },
      },
    );
  }

  function enviarAbertura(file: File) {
    salvarAbertura.reset();
    // Zero antes do primeiro `onprogress`: a barra nasce na hora, e não depois do primeiro pedaço.
    setProgressoAbertura(0);
    salvarAbertura.mutate(
      { file, onProgress: setProgressoAbertura },
      {
        onSuccess: (resposta) => setAberturaSalva(resposta.abertura_url),
        onSettled: () => setProgressoAbertura(null),
      },
    );
  }

  function confirmarRemocao() {
    if (confirmando === null) return;
    if (confirmando === "moldura") {
      removerMoldura.mutate(undefined, {
        onSuccess: (resposta) => {
          setMolduraSalva(resposta.moldura_url);
          setConfirmando(null);
        },
      });
      return;
    }
    removerAbertura.mutate(undefined, {
      onSuccess: (resposta) => {
        setAberturaSalva(resposta.abertura_url);
        setConfirmando(null);
      },
    });
  }

  function fechar() {
    limparEscolha();
    setConfirmando(null);
    setProgressoAbertura(null);
    salvarMoldura.reset();
    salvarAbertura.reset();
    removerMoldura.reset();
    removerAbertura.reset();
    onFechar();
  }

  return (
    <Dialog open={aberto} onOpenChange={(open) => !open && fechar()}>
      <DialogContent open={aberto} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Moldura e vídeo de abertura</DialogTitle>
          <DialogDescription>
            Os dois arquivos são únicos e valem para TODAS as luminárias — trocar aqui muda o que a
            próxima cliente vê ao encostar o celular.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <input
            ref={inputMoldura}
            type="file"
            accept={MOLDURA_ACCEPT}
            className="hidden"
            aria-label="Arquivo da moldura (PNG)"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) escolherMoldura(file);
            }}
          />
          <input
            ref={inputAbertura}
            type="file"
            accept={NFC_VIDEO_ACCEPT}
            className="hidden"
            aria-label="Arquivo do vídeo de abertura"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) enviarAbertura(file);
            }}
          />

          <section aria-label="Moldura dos vídeos" className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Frame className="h-4 w-4 flex-none text-muted" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-ink">Moldura dos vídeos</h3>
              <Badge tone={estadoMoldura === "cadastrado" ? "accent" : "neutral"}>
                {ROTULO_MOLDURA[estadoMoldura]}
              </Badge>
            </div>
            <p className="text-xs text-muted">
              É gravada na borda de todo vídeo enviado com a caixinha marcada: quem recebe a
              luminária vê o vídeo já emoldurado.
            </p>

            <AnimatePresence initial={false} mode="wait">
              {previaLocal !== null ? (
                <motion.div
                  key="moldura-escolha"
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                  transition={TRANSICAO}
                  className="space-y-2"
                >
                  <div
                    className={cn(
                      "relative mx-auto aspect-[9/16] w-full max-w-[11rem] overflow-hidden rounded-md border border-line",
                      FUNDO_XADREZ,
                    )}
                  >
                    <img
                      src={previaLocal}
                      alt="Prévia da moldura escolhida, sobre fundo xadrez"
                      className="h-full w-full object-contain"
                    />
                  </div>
                  <p className="text-center text-xs text-muted">
                    {arquivoMoldura?.name}
                    {medidaAtual && ` · ${medidaAtual.largura} × ${medidaAtual.altura} px`}
                  </p>

                  <AnimatePresence initial={false}>
                    {foraDeRetrato && (
                      <motion.p
                        key="aviso-proporcao"
                        role="status"
                        initial={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                        transition={TRANSICAO}
                        className="flex items-start gap-2 overflow-hidden rounded-md border border-line bg-gold-soft p-2 text-xs text-gold-ink"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
                        <span>
                          Esta imagem não está em 9:16 (o formato em pé dos vídeos). Ela vai ser
                          esticada até preencher o quadro. Pode salvar assim mesmo — a decisão é
                          sua.
                        </span>
                      </motion.p>
                    )}
                  </AnimatePresence>

                  {erroMoldura && (
                    <p className="text-sm text-red" role="alert">
                      {erroMoldura}
                    </p>
                  )}

                  <div className="flex justify-center gap-2">
                    <Button size="sm" loading={salvarMoldura.isPending} onClick={enviarMoldura}>
                      Salvar moldura
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={salvarMoldura.isPending}
                      onClick={limparEscolha}
                    >
                      Cancelar
                    </Button>
                  </div>
                </motion.div>
              ) : estadoMoldura === "ausente" ? (
                <motion.div
                  key="moldura-vazia"
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                  transition={TRANSICAO}
                  className="rounded-md border border-dashed border-line-strong bg-surface-2 p-4 text-center"
                >
                  <p className="text-sm text-ink">
                    Nenhuma moldura cadastrada — os vídeos sairão sem moldura
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    PNG com fundo transparente, em pé (9:16). O servidor recusa PNG opaco.
                  </p>
                  <Button
                    size="sm"
                    className="mt-3"
                    disabled={enviando}
                    onClick={() => inputMoldura.current?.click()}
                  >
                    <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                    Escolher moldura
                  </Button>
                  {erroMoldura && (
                    <p className="mt-2 text-sm text-red" role="alert">
                      {erroMoldura}
                    </p>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="moldura-salva"
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                  transition={TRANSICAO}
                  className="space-y-2"
                >
                  <div
                    className={cn(
                      "relative mx-auto aspect-[9/16] w-full max-w-[11rem] overflow-hidden rounded-md border border-line",
                      FUNDO_XADREZ,
                    )}
                  >
                    {srcMoldura && (
                      <img
                        key={srcMoldura}
                        src={srcMoldura}
                        alt="Moldura cadastrada, sobre fundo xadrez"
                        className="h-full w-full object-contain"
                        onLoad={() => setSondaMoldura("cadastrado")}
                        onError={() => setSondaMoldura("ausente")}
                      />
                    )}
                    <AnimatePresence>
                      {estadoMoldura === "verificando" && (
                        <motion.div
                          key="moldura-carregando"
                          initial={false}
                          exit={reduceMotion ? undefined : { opacity: 0 }}
                          transition={TRANSICAO}
                          className="absolute inset-0"
                        >
                          <Skeleton className="h-full w-full rounded-none" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <p className="text-center text-xs text-muted">
                    O xadrez mostra o que é transparente: se ele sumiu atrás da imagem, a moldura
                    vai cobrir o vídeo inteiro.
                  </p>
                  <div className="flex justify-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={enviando}
                      onClick={() => inputMoldura.current?.click()}
                    >
                      <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Substituir
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red"
                      disabled={enviando}
                      onClick={() => setConfirmando("moldura")}
                    >
                      <Trash2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Remover
                    </Button>
                  </div>
                  {erroMoldura && (
                    <p className="text-center text-sm text-red" role="alert">
                      {erroMoldura}
                    </p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          <section aria-label="Vídeo de abertura" className="space-y-2 border-t border-line pt-5">
            <div className="flex flex-wrap items-center gap-2">
              <Film className="h-4 w-4 flex-none text-muted" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-ink">Vídeo de abertura</h3>
              <Badge tone={estadoAbertura === "cadastrado" ? "accent" : "neutral"}>
                {ROTULO_ABERTURA[estadoAbertura]}
              </Badge>
            </div>
            <p className="text-xs text-muted">
              Toca no primeiro acesso de qualquer luminária, antes do menu — é a abertura da marca,
              igual para todo mundo.
            </p>

            <AnimatePresence initial={false} mode="wait">
              {estadoAbertura === "ausente" ? (
                <motion.div
                  key="abertura-vazia"
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                  transition={TRANSICAO}
                  className="rounded-md border border-dashed border-line-strong bg-surface-2 p-4 text-center"
                >
                  <p className="text-sm text-ink">
                    Nenhum vídeo de abertura — a página abre direto no menu
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    MP4, MOV, WEBM ou M4V, em pé. Ele é convertido no servidor, sem moldura.
                  </p>
                  <Button
                    size="sm"
                    className="mt-3"
                    loading={salvarAbertura.isPending}
                    disabled={salvarMoldura.isPending}
                    onClick={() => inputAbertura.current?.click()}
                  >
                    <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                    Escolher vídeo
                  </Button>
                </motion.div>
              ) : (
                <motion.div
                  key="abertura-salva"
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
                  transition={TRANSICAO}
                  className="space-y-2"
                >
                  <div className="relative mx-auto aspect-[9/16] w-full max-w-[11rem] overflow-hidden rounded-md border border-line bg-media">
                    {srcAbertura && (
                      // `preload="metadata"` é inegociável (incidente de `revisao/VideoPlayer.tsx`:
                      // `auto` baixa o arquivo inteiro por thread) — e aqui ele é também a sonda:
                      // 404 dispara `onError`, que revela o estado vazio.
                      <video
                        key={srcAbertura}
                        src={srcAbertura}
                        controls
                        playsInline
                        preload="metadata"
                        className="h-full w-full object-contain"
                        onLoadedMetadata={() => setSondaAbertura("cadastrado")}
                        onError={() => setSondaAbertura("ausente")}
                      />
                    )}
                    <AnimatePresence>
                      {estadoAbertura === "verificando" && (
                        <motion.div
                          key="abertura-carregando"
                          initial={false}
                          exit={reduceMotion ? undefined : { opacity: 0 }}
                          transition={TRANSICAO}
                          className="absolute inset-0"
                        >
                          <Skeleton className="h-full w-full rounded-none" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className="flex justify-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      loading={salvarAbertura.isPending}
                      disabled={salvarMoldura.isPending}
                      onClick={() => inputAbertura.current?.click()}
                    >
                      <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Substituir
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red"
                      disabled={enviando}
                      onClick={() => setConfirmando("abertura")}
                    >
                      <Trash2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                      Remover
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* O vídeo de abertura é o arquivo mais pesado desta tela: sem número na tela o
                silêncio parece conclusão e a janela é fechada no meio do envio. */}
            <AnimatePresence initial={false}>
              {progressoAbertura !== null && (
                <motion.div
                  key="progresso-abertura"
                  initial={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                  transition={TRANSICAO}
                  className="overflow-hidden"
                >
                  <UploadProgressBar fraction={progressoAbertura} />
                </motion.div>
              )}
            </AnimatePresence>

            {erroAbertura && (
              <p className="text-sm text-red" role="alert">
                {erroAbertura}
              </p>
            )}
          </section>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={fechar} disabled={enviando}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>

      {/* Fora do DialogContent de propósito: diálogos irmãos, não aninhados (cada um com seu
          portal Radix). Erro da remoção aparece DENTRO da confirmação, que fica aberta. */}
      <ConfirmDialog
        open={confirmando !== null}
        title={textoRemocao.titulo}
        description={textoRemocao.descricao}
        confirmLabel={textoRemocao.confirmar}
        destructive
        pending={removendo}
        error={erroRemocao?.message ?? null}
        onConfirm={confirmarRemocao}
        onOpenChange={(open) => {
          if (open) return;
          setConfirmando(null);
          removerMoldura.reset();
          removerAbertura.reset();
        }}
      />
    </Dialog>
  );
}
