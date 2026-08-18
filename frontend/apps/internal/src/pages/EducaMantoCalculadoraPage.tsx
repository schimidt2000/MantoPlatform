import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import {
  AccordionRow,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InfoTip,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { GoogleAddressInput } from "../components/GoogleAddressInput";
import { AcrescimosEditor } from "../components/orcamento/AcrescimosEditor";
import { PerformersEditor } from "../components/orcamento/PerformersEditor";
import { useCurrentUser } from "../lib/useAuth";
import { useOrcamentoOpcoes, type Acrescimo, type Performer } from "../lib/orcamento";
import {
  isSnapshotV2,
  RESPONSABILIDADES_PADRAO,
  useCalcularConfig,
  useDistanciaEducaManto,
  useEducaMantoQuoteDetalhe,
  useEducaMantoTextos,
  useGerarOrcamento,
  useMusicals,
  usePersonagensNoDiaEducaManto,
  type ConfigBreakdown,
  type ConfigInput,
  type Responsabilidades,
  type ResponsabilidadeChave,
} from "../lib/educamanto";

const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";
const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_OBSERVACAO = 2000;

const TECNICO_LABELS: Record<string, string> = {
  sonoplasta: "Sonoplasta",
  tecnico_som: "Técnico de som",
  tecnico_iluminacao: "Técnico de iluminação",
};

/** Ordem das responsabilidades quando os textos do servidor ainda não chegaram. */
const RESPONSABILIDADES_ORDEM: ResponsabilidadeChave[] = ["som", "iluminacao", "alimentacao"];

/**
 * Rótulos de reserva em pt-BR: se `/api/educamanto/textos` falhar ou ainda estiver
 * carregando, a tela mostra "Sonorização" — nunca a chave crua "som".
 */
const RESPONSABILIDADE_LABELS: Record<ResponsabilidadeChave, string> = {
  som: "Sonorização",
  iluminacao: "Iluminação",
  alimentacao: "Alimentação",
};

function brl(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `R$ ${formatBRL(v)}`;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiRequestError ? err.message : fallback;
}

/** Contratação Manto embutida (apresentação tradicional junto do EducaManto). */
interface ContratacaoState {
  ativa: boolean;
  performers: Performer[];
  coordenadorQty: number;
  acrescimos: Acrescimo[];
  eventTime: string;
  /** Durações fixas selecionadas (1h–4h). */
  duracoes: string[];
  /** Duração extra acima de 4h (0 = nenhuma). */
  duracaoCustom: number;
}

const CONTRATACAO_INICIAL: ContratacaoState = {
  ativa: false,
  performers: [],
  coordenadorQty: 1,
  acrescimos: [],
  eventTime: "",
  duracoes: ["1h"],
  duracaoCustom: 0,
};

const DURACOES_FIXAS = ["1h", "2h", "3h", "4h"] as const;

/** Estado editável de UMA página (configuração) do orçamento. */
interface ConfigState {
  musicalId: number | null;
  d1: number;
  d2: number;
  ensemble: number;
  responsabilidades: Responsabilidades;
  foraSp: boolean;
  endereco: string;
  kmIda: number | null;
  acrescimo: number;
  contratacao: ContratacaoState;
}

function novaConfig(musicalId: number | null): ConfigState {
  return {
    musicalId,
    d1: 0,
    d2: 0,
    ensemble: 0,
    responsabilidades: { ...RESPONSABILIDADES_PADRAO },
    foraSp: false,
    endereco: "",
    kmIda: null,
    acrescimo: 0,
    contratacao: { ...CONTRATACAO_INICIAL },
  };
}

/**
 * Durações fixas efetivamente marcadas: as dos checkboxes MAIS a do campo "Extra (h)"
 * quando ele recebe 1–4 (antes esse valor era descartado em silêncio).
 */
function duracoesFixasDaContratacao(c: ContratacaoState): string[] {
  const doCustom =
    c.duracaoCustom >= 1 && c.duracaoCustom <= 4 ? `${c.duracaoCustom}h` : null;
  return DURACOES_FIXAS.filter((d) => c.duracoes.includes(d) || d === doCustom);
}

/** Durações enviadas ao servidor: as fixas + a extra acima de 4h, quando houver. */
function duracoesDaContratacao(c: ContratacaoState): string[] {
  const fixas = duracoesFixasDaContratacao(c);
  return c.duracaoCustom > 4 ? [...fixas, `${c.duracaoCustom}h`] : fixas;
}

/** Cópia profunda da contratação — páginas novas não podem compartilhar performers/acréscimos. */
function clonarContratacao(c: ContratacaoState): ContratacaoState {
  return {
    ...c,
    performers: c.performers.map((p) => ({ ...p })),
    acrescimos: c.acrescimos.map((a) => ({ ...a })),
    duracoes: [...c.duracoes],
  };
}

function configParaInput(config: ConfigState, eventDate: string): ConfigInput | null {
  if (!config.musicalId) return null;
  const c = config.contratacao;
  const duracoes = duracoesDaContratacao(c);
  return {
    musical_id: config.musicalId,
    d1: config.d1,
    d2: config.d2,
    ensemble: config.ensemble,
    responsabilidades: config.responsabilidades,
    fora_sp: config.foraSp,
    km_ida: config.foraSp && config.kmIda ? config.kmIda : null,
    acrescimo: config.acrescimo,
    // Vai sempre que a contratação está ativa, mesmo sem duração marcada: é assim que a
    // validação do servidor recusa o orçamento em vez de congelá-lo sem a parte Manto.
    contratacao_manto: c.ativa
      ? {
          duracoes,
          payload: {
            performers: c.performers,
            coordenador_qty: c.coordenadorQty,
            acrescimos: c.acrescimos,
            event_date: eventDate || undefined,
            event_time: c.eventTime || undefined,
            event_location: config.endereco || undefined,
            modo_duracao: "horas",
            incluir_duracao: duracoesFixasDaContratacao(c),
          },
        }
      : null,
  };
}

/**
 * "Recalcular" de snapshot v1 (pacotes por nível): mapeia o pacote antigo para o musical e
 * pré-marca as responsabilidades pelo nível que o nome carregava — Econômica era "sem
 * iluminação e sem alimentação da Manto". O aviso na tela explica o mapeamento aplicado.
 */
function responsabilidadesDeNomeAntigo(nomePacote: string): Responsabilidades {
  const nome = nomePacote.toLowerCase();
  if (nome.includes("econ") || nome.includes("basic")) {
    return { ...RESPONSABILIDADES_PADRAO, iluminacao: "contratante", alimentacao: "contratante" };
  }
  return { ...RESPONSABILIDADES_PADRAO };
}

function AgendaNoDiaAlert({ date }: { date: string }) {
  const dateValida = DATE_RE.test(date);
  const consulta = usePersonagensNoDiaEducaManto(dateValida ? date : "");
  const personagens = consulta.data?.personagens ?? [];

  if (!dateValida || personagens.length === 0) return null;

  return (
    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
      <p className="mb-1 font-semibold text-gold-ink">
        ⚠️ Já na agenda neste dia — não vender em dobro
      </p>
      <ul className="list-disc space-y-0.5 pl-4 text-ink">
        {personagens.map((p) => (
          <li key={p.nome}>
            <span className="font-medium">{p.nome}</span>
            {p.eventos.length > 0 && (
              <span className="text-muted"> — {p.eventos.join(" · ")}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tabela de custos internos — só existe quando a API devolve o breakdown (superadmin). */
function BreakdownTable({ breakdown }: { breakdown: ConfigBreakdown }) {
  if (breakdown.item_rows.length === 0) return null;
  return (
    <Table>
      <thead>
        <TableRow head>
          <TableCell as="th">Item</TableCell>
          <TableCell as="th" align="right">Qtd</TableCell>
          <TableCell as="th" align="right">Custo total</TableCell>
          <TableCell as="th" align="right">Preço venda</TableCell>
        </TableRow>
      </thead>
      <tbody>
        {breakdown.item_rows.map((row) => (
          <TableRow key={row.name}>
            <TableCell className="text-ink">{row.name}</TableCell>
            <TableCell align="right">{row.qty}</TableCell>
            <TableCell align="right">{brl(row.raw)}</TableCell>
            <TableCell align="right" className="font-medium">{brl(row.sell)}</TableCell>
          </TableRow>
        ))}
      </tbody>
    </Table>
  );
}

export function EducaMantoCalculadoraPage() {
  const reduceMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const recalcularId = searchParams.get("recalcular_id");
  const recalcularIdNum = recalcularId ? Number(recalcularId) : null;
  const musicalIdParam = searchParams.get("musical_id") ?? searchParams.get("package_id");

  const musicalsQuery = useMusicals();
  const textosQuery = useEducaMantoTextos();
  const user = useCurrentUser();
  // A contratação Manto usa o módulo da calculadora de eventos, restrito a
  // Comercial/Superadmin — para os demais papéis a seção nem aparece.
  const podeContratacao = Boolean(
    user.data &&
      (user.data.is_superadmin || user.data.roles.some((r) => r === "COMERCIAL" || r === "SUPERADMIN")),
  );
  const opcoes = useOrcamentoOpcoes();
  const distancia = useDistanciaEducaManto();
  const calcular = useCalcularConfig();
  const gerarOrcamento = useGerarOrcamento();
  const quoteDetalhe = useEducaMantoQuoteDetalhe(recalcularIdNum);

  const [configs, setConfigs] = useState<ConfigState[]>([novaConfig(null)]);
  const [ativa, setAtiva] = useState(0);
  const [clientName, setClientName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [observacao, setObservacao] = useState("");
  const [enderecoMsg, setEnderecoMsg] = useState<{ text: string; error: boolean } | null>(null);
  const [gerarMsg, setGerarMsg] = useState<{ text: string; error: boolean } | null>(null);
  const [recalcularAviso, setRecalcularAviso] = useState<string | null>(null);

  const musicals = musicalsQuery.data?.musicals ?? [];
  const podeGerir = musicalsQuery.data?.pode_gerir ?? false;
  const textos = textosQuery.data;
  const config = configs[ativa];

  function alterarConfig(mudancas: Partial<ConfigState>) {
    setConfigs((prev) => prev.map((c, i) => (i === ativa ? { ...c, ...mudancas } : c)));
  }

  // Seleção inicial do musical (query param `musical_id`/`package_id` ou o primeiro da lista).
  useEffect(() => {
    if (config?.musicalId !== null || musicals.length === 0) return;
    const paramId = musicalIdParam ? Number(musicalIdParam) : null;
    const inicial =
      paramId && musicals.some((m) => m.id === paramId) ? paramId : musicals[0].id;
    setConfigs((prev) => prev.map((c) => (c.musicalId === null ? { ...c, musicalId: inicial } : c)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [musicals, musicalIdParam]);

  // "Recalcular" — repopula a partir do snapshot salvo (v2 direto; v1 mapeado com aviso).
  useEffect(() => {
    const snap = quoteDetalhe.data;
    if (!snap || musicals.length === 0) return;

    if (isSnapshotV2(snap)) {
      setConfigs(
        snap.configs.map((c) => {
          const inputs = c.contratacao_manto?.inputs as
            | { performers?: Performer[]; coordenador_qty?: number; acrescimos?: Acrescimo[]; event_time?: string }
            | undefined;
          const duracoes = c.contratacao_manto?.duracoes ?? [];
          const custom = duracoes.find((d) => !["1h", "2h", "3h", "4h"].includes(d));
          return {
            musicalId: c.musical_id,
            d1: c.d1,
            d2: c.d2,
            ensemble: c.ensemble,
            responsabilidades: { ...c.responsabilidades },
            foraSp: c.fora_sp,
            endereco: "",
            kmIda: c.km_ida,
            acrescimo: c.acrescimo,
            contratacao: c.contratacao_manto
              ? {
                  ativa: true,
                  performers: inputs?.performers ?? [],
                  coordenadorQty: inputs?.coordenador_qty ?? 1,
                  acrescimos: inputs?.acrescimos ?? [],
                  eventTime: inputs?.event_time ?? "",
                  duracoes: duracoes.filter((d) => ["1h", "2h", "3h", "4h"].includes(d)),
                  duracaoCustom: custom ? Number(custom.replace("h", "")) || 0 : 0,
                }
              : { ...CONTRATACAO_INICIAL },
          };
        }),
      );
      setClientName(snap.client_name ?? "");
      setEventDate(snap.event_date ?? "");
      setObservacao(snap.observacao ?? "");
      setAtiva(0);
      return;
    }

    // v1: acha o musical pelo id preservado ou pelo prefixo do nome do pacote antigo.
    const pacote = snap.packages[0];
    if (!pacote) return;
    const porId = musicals.find((m) => m.id === pacote.id);
    const porNome = musicals.find((m) => pacote.name.startsWith(m.name));
    const musical = porId ?? porNome ?? null;
    setConfigs([
      {
        ...novaConfig(musical?.id ?? musicals[0].id),
        d1: snap.d1,
        d2: snap.d2,
        ensemble: snap.ensemble,
        responsabilidades: responsabilidadesDeNomeAntigo(pacote.name),
        foraSp: Boolean(snap.transporte?.km_ida),
        kmIda: snap.transporte?.km_ida ?? null,
        acrescimo: snap.acrescimo,
      },
    ]);
    setClientName(snap.client_name ?? "");
    setEventDate(snap.event_date ?? "");
    setAtiva(0);
    setRecalcularAviso(
      musical
        ? `Orçamento antigo (por pacote) mapeado para o musical "${musical.name}". As responsabilidades foram pré-marcadas pelo nível do pacote — confira antes de gerar.`
        : "Orçamento antigo: o pacote original não existe mais; usei o primeiro musical. Confira tudo antes de gerar.",
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quoteDetalhe.data, musicals]);

  const totalDias = (config?.d1 ?? 0) + (config?.d2 ?? 0);

  // Recalcula a página ATIVA com debounce a cada mudança relevante.
  useEffect(() => {
    if (!config) return undefined;
    const input = configParaInput(config, eventDate);
    if (!input || totalDias <= 0) return undefined;
    if (config.foraSp && !config.kmIda) return undefined;
    const timer = setTimeout(() => calcular.mutate(input), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    config?.musicalId, config?.d1, config?.d2, config?.ensemble, config?.acrescimo,
    config?.foraSp, config?.kmIda,
    config?.responsabilidades.som, config?.responsabilidades.iluminacao,
    config?.responsabilidades.alimentacao,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(config?.contratacao), eventDate,
    ativa,
  ]);

  function handleCalcularDistancia(override?: string) {
    const alvo = (override ?? config.endereco).trim();
    if (!alvo) {
      setEnderecoMsg({ text: "Informe o endereço primeiro.", error: true });
      return;
    }
    setEnderecoMsg({ text: "Calculando…", error: false });
    distancia.mutate(alvo, {
      onSuccess: (data) => {
        alterarConfig({ kmIda: data.km_ida });
        setEnderecoMsg({
          text: `Distância: ${data.km_ida} km (ida) · ${data.km_ida * 2} km ida e volta`,
          error: false,
        });
      },
      onError: (err) => {
        setEnderecoMsg({
          text: errorMessage(err, "Não foi possível calcular a distância."),
          error: true,
        });
      },
    });
  }

  function handleNovaPagina() {
    setConfigs((prev) => [
      ...prev,
      {
        ...prev[ativa],
        responsabilidades: { ...prev[ativa].responsabilidades },
        contratacao: clonarContratacao(prev[ativa].contratacao),
      },
    ]);
    setAtiva(configs.length);
    setGerarMsg(null);
  }

  function handleRemoverPagina(idx: number) {
    if (configs.length <= 1) return;
    setConfigs((prev) => prev.filter((_, i) => i !== idx));
    setAtiva((atual) => (idx <= atual ? Math.max(0, atual - 1) : atual));
  }

  /**
   * Liga/desliga uma duração fixa da contratação. Desmarcar uma duração que estava marcada
   * por causa do campo "Extra (h)" (1–4) também zera o extra — senão ela voltaria sozinha.
   */
  function alternarDuracaoContratacao(d: string) {
    const c = config.contratacao;
    const marcada = duracoesFixasDaContratacao(c).includes(d);
    const vemDoExtra = c.duracaoCustom >= 1 && c.duracaoCustom <= 4 && `${c.duracaoCustom}h` === d;
    alterarConfig({
      contratacao: {
        ...c,
        duracoes: marcada ? c.duracoes.filter((x) => x !== d) : [...c.duracoes, d],
        duracaoCustom: marcada && vemDoExtra ? 0 : c.duracaoCustom,
      },
    });
  }

  const inputsValidos = useMemo(
    () => configs.map((c) => configParaInput(c, eventDate)).filter((c): c is ConfigInput => c !== null),
    [configs, eventDate],
  );

  /** Páginas com a contratação Manto ligada e nenhuma duração marcada — o servidor recusa. */
  const paginasSemDuracao = useMemo(
    () =>
      configs
        .map((c, i) => (c.contratacao.ativa && duracoesDaContratacao(c.contratacao).length === 0 ? i + 1 : 0))
        .filter((n) => n > 0),
    [configs],
  );
  const contratacaoSemDuracao = paginasSemDuracao.length > 0;
  const avisoSemDuracao = contratacaoSemDuracao
    ? `Marque ao menos uma duração da contratação Manto (${
        paginasSemDuracao.length > 1
          ? `páginas ${paginasSemDuracao.join(", ")}`
          : `página ${paginasSemDuracao[0]}`
      }) para gerar o orçamento.`
    : null;

  function handleGerarOrcamento() {
    // O cálculo é debounced: gerar no meio congelaria um valor que já não é o da tela.
    if (calcular.isPending || contratacaoSemDuracao || inputsValidos.length !== configs.length) return;
    setGerarMsg({ text: "Gerando…", error: false });
    gerarOrcamento.mutate(
      {
        configs: inputsValidos,
        client_name: clientName,
        event_date: eventDate || undefined,
        observacao: observacao || undefined,
      },
      {
        onSuccess: () => setGerarMsg({ text: "Orçamento gerado e baixado com sucesso.", error: false }),
        onError: (err) =>
          setGerarMsg({
            text: errorMessage(err, "Não foi possível gerar o orçamento."),
            error: true,
          }),
      },
    );
  }

  const resultado = calcular.data;
  const transporte = resultado?.transporte;
  const breakdown = resultado?.breakdown;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Calculadora"
        className="mb-0"
        actions={
          <div className="flex flex-wrap gap-3 text-sm">
            {(resultado || contratacaoSemDuracao) && totalDias > 0 && (
              <Button
                size="sm"
                loading={gerarOrcamento.isPending}
                disabled={calcular.isPending || contratacaoSemDuracao}
                title={
                  contratacaoSemDuracao
                    ? (avisoSemDuracao ?? undefined)
                    : calcular.isPending
                      ? "Aguarde o recálculo terminar para não congelar um valor antigo no PDF"
                      : undefined
                }
                onClick={handleGerarOrcamento}
              >
                Gerar orçamento{configs.length > 1 ? ` (${configs.length} páginas)` : ""}
              </Button>
            )}
            <Button asChild variant="ghost" size="sm">
              <Link to="/educamanto/historico">Histórico</Link>
            </Button>
            {podeGerir && (
              <Button asChild variant="ghost" size="sm">
                <Link to="/educamanto/musicais">Musicais</Link>
              </Button>
            )}
            {avisoSemDuracao && (
              <p className="w-full text-xs text-red sm:text-right" role="alert">
                {avisoSemDuracao}
              </p>
            )}
          </div>
        }
      />

      {quoteDetalhe.isFetching && (
        <p className="text-xs text-muted">Carregando orçamento para recalcular…</p>
      )}

      {recalcularAviso && (
        <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm text-ink" role="alert">
          {recalcularAviso}
        </div>
      )}

      {musicalsQuery.isLoading && <Skeleton className="h-40 w-full" />}

      {musicalsQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os musicais. Confira se você tem permissão para usar o
          EducaManto.
        </div>
      )}

      {musicals.length > 0 && config && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          {/* ── Páginas do orçamento ─────────────────────────────────────── */}
          <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Páginas do orçamento">
            {configs.map((c, i) => {
              const nome = musicals.find((m) => m.id === c.musicalId)?.name ?? "…";
              return (
                <div key={i} className="flex items-center">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={i === ativa}
                    onClick={() => { setAtiva(i); setEnderecoMsg(null); }}
                    className={`rounded-l-md border border-line px-3 py-1.5 text-xs font-medium transition-colors ${
                      i === ativa ? "bg-blue text-white" : "bg-panel text-muted hover:text-ink"
                    } ${configs.length === 1 ? "rounded-r-md" : ""}`}
                  >
                    Página {i + 1} · {nome}
                    {c.contratacao.ativa ? " + Manto" : ""}
                  </button>
                  {configs.length > 1 && (
                    <button
                      type="button"
                      aria-label={`Remover página ${i + 1}`}
                      onClick={() => handleRemoverPagina(i)}
                      className="rounded-r-md border border-l-0 border-line bg-panel px-2 py-1.5 text-xs text-muted hover:text-red"
                    >
                      ×
                    </button>
                  )}
                </div>
              );
            })}
            <Button type="button" variant="outline" size="sm" onClick={handleNovaPagina}>
              + Nova página
            </Button>
          </div>

          <div>
            <label className={LABEL} htmlFor="musical">
              Musical
            </label>
            <select
              id="musical"
              className={`${FIELD} max-w-md`}
              value={config.musicalId ?? ""}
              onChange={(e) => alterarConfig({ musicalId: Number(e.target.value) })}
            >
              {musicals.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              {/* ── Responsabilidades ─────────────────────────────────────── */}
              <Card>
                <CardHeader>
                  <CardTitle>Responsabilidades</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-xs text-muted">
                    Marque o que fica por conta da Manto e o que a contratante fornece — o valor
                    e a equipe técnica se ajustam na hora.
                  </p>
                  {textosQuery.isError && (
                    <p className="text-xs text-red" role="alert">
                      Não foi possível carregar as dicas de cada responsabilidade. O cálculo
                      continua normal — recarregue a página para tentar de novo.
                    </p>
                  )}
                  {(textos?.ordem ?? RESPONSABILIDADES_ORDEM).map(
                    (chave) => {
                      const info = textos?.responsabilidades[chave];
                      const rotulo = info?.label ?? RESPONSABILIDADE_LABELS[chave] ?? chave;
                      const valor = config.responsabilidades[chave];
                      return (
                        <div
                          key={chave}
                          className="flex items-center justify-between gap-3 rounded-md border border-line bg-panel px-3 py-2"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-medium text-ink">{rotulo}</span>
                            {info?.tooltip ? (
                              <InfoTip label={rotulo} content={info.tooltip} />
                            ) : (
                              // Sem texto ainda: o gatilho fica visível porém inerte enquanto
                              // carrega (ou quando a busca falhou), sem sumir da linha.
                              <InfoTip
                                label={rotulo}
                                content=""
                                disabled
                                className={textosQuery.isLoading ? "animate-pulse" : ""}
                              />
                            )}
                          </div>
                          <div className="flex overflow-hidden rounded-md border border-line" role="group" aria-label={rotulo}>
                            {(["manto", "contratante"] as const).map((opcao) => (
                              <button
                                key={opcao}
                                type="button"
                                aria-pressed={valor === opcao}
                                onClick={() =>
                                  alterarConfig({
                                    responsabilidades: {
                                      ...config.responsabilidades,
                                      [chave]: opcao,
                                    },
                                  })
                                }
                                className={`px-3 py-1 text-xs font-medium transition-colors ${
                                  valor === opcao
                                    ? opcao === "manto"
                                      ? "bg-blue text-white"
                                      : "bg-gold text-white"
                                    : "bg-panel text-muted hover:text-ink"
                                }`}
                              >
                                {opcao === "manto" ? "Manto" : "Contratante"}
                              </button>
                            ))}
                          </div>
                        </div>
                      );
                    },
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Dias e ensemble</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <label className={LABEL} htmlFor="d1">
                      Dias — 1 sessão
                    </label>
                    <Input
                      id="d1"
                      type="number"
                      min={0}
                      value={config.d1}
                      onChange={(e) => alterarConfig({ d1: Math.max(0, Number(e.target.value) || 0) })}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="d2">
                      Dias — 2 sessões
                    </label>
                    <Input
                      id="d2"
                      type="number"
                      min={0}
                      value={config.d2}
                      onChange={(e) => alterarConfig({ d2: Math.max(0, Number(e.target.value) || 0) })}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="ensemble">
                      Ensemble
                    </label>
                    <Input
                      id="ensemble"
                      type="number"
                      min={0}
                      value={config.ensemble}
                      onChange={(e) => alterarConfig({ ensemble: Math.max(0, Number(e.target.value) || 0) })}
                    />
                  </div>
                  <div className="sm:col-span-3">
                    <label className={LABEL} htmlFor="event_date">
                      Data da apresentação
                    </label>
                    <Input
                      id="event_date"
                      type="date"
                      className="max-w-[200px]"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                    />
                    <p className="mt-1 text-xs text-muted">
                      Não entra no preço — serve para conferir quem já está escalado no dia.
                    </p>
                  </div>
                  {eventDate && (
                    <div className="sm:col-span-3">
                      <AgendaNoDiaAlert date={eventDate} />
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Contratação Manto embutida (US4) — módulo da calculadora de
                  eventos como fonte única; NF e transporte ficam com o EducaManto.
                  Fica logo após "Dias e ensemble" porque no fim da coluna ninguém achava. */}
              {podeContratacao && (
                <Card>
                  <CardHeader>
                    <CardTitle>Contratação Manto (apresentação tradicional)</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {!config.contratacao.ativa && (
                      <>
                        <p className="text-xs text-muted">
                          Vai ter uma apresentação da Manto tradicional junto do EducaManto?
                          Monte a equipe aqui — o valor soma ao desta página e a nota fiscal é
                          aplicada sobre o total.
                        </p>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            alterarConfig({
                              contratacao: { ...config.contratacao, ativa: true },
                            })
                          }
                        >
                          + Adicionar contratação Manto
                        </Button>
                      </>
                    )}
                    {config.contratacao.ativa && (
                      <>
                        {opcoes.isLoading && <Skeleton className="h-24 w-full" />}
                        {opcoes.isError && (
                          <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
                            Não foi possível carregar as opções da calculadora de eventos.
                          </div>
                        )}
                        {opcoes.data && (
                          <>
                            <div className="flex flex-wrap items-end gap-3">
                              <div>
                                <label className={LABEL} htmlFor="contratacao_horario">
                                  Horário da apresentação
                                </label>
                                <Input
                                  id="contratacao_horario"
                                  type="time"
                                  className="max-w-[140px]"
                                  value={config.contratacao.eventTime}
                                  onChange={(e) =>
                                    alterarConfig({
                                      contratacao: { ...config.contratacao, eventTime: e.target.value },
                                    })
                                  }
                                />
                              </div>
                              <div>
                                <span className={LABEL}>Durações no orçamento</span>
                                <div className="flex flex-wrap items-center gap-3">
                                  {DURACOES_FIXAS.map((d) => (
                                    <label key={d} className="flex items-center gap-1 text-sm text-ink">
                                      <input
                                        type="checkbox"
                                        checked={duracoesFixasDaContratacao(config.contratacao).includes(d)}
                                        onChange={() => alternarDuracaoContratacao(d)}
                                      />
                                      {d}
                                    </label>
                                  ))}
                                  <label className="flex items-center gap-1 text-sm text-ink">
                                    <span className="text-xs text-muted">Extra (h):</span>
                                    <Input
                                      type="number"
                                      min={0}
                                      className="h-8 w-16"
                                      value={config.contratacao.duracaoCustom || ""}
                                      onChange={(e) =>
                                        alterarConfig({
                                          contratacao: {
                                            ...config.contratacao,
                                            duracaoCustom: Math.max(0, Number(e.target.value) || 0),
                                          },
                                        })
                                      }
                                    />
                                  </label>
                                </div>
                                {duracoesDaContratacao(config.contratacao).length === 0 ? (
                                  <p className="mt-1 text-xs text-red" role="alert">
                                    Marque ao menos uma duração — sem isso o orçamento não sai
                                    com a contratação Manto.
                                  </p>
                                ) : (
                                  <p className="mt-1 text-xs text-muted">
                                    Extra de 1h a 4h marca a duração correspondente; acima de 4h
                                    entra como duração adicional.
                                  </p>
                                )}
                              </div>
                            </div>

                            <div className="overflow-x-auto rounded-md border border-line">
                              <PerformersEditor
                                performers={config.contratacao.performers}
                                onPerformersChange={(performers) =>
                                  alterarConfig({ contratacao: { ...config.contratacao, performers } })
                                }
                                coordenadorQty={config.contratacao.coordenadorQty}
                                onCoordenadorQtyChange={(coordenadorQty) =>
                                  alterarConfig({ contratacao: { ...config.contratacao, coordenadorQty } })
                                }
                                especiais={opcoes.data.especiais}
                                especiaisComShow={opcoes.data.especiais_com_show}
                                especiaisComCantor={opcoes.data.especiais_com_cantor}
                              />
                            </div>

                            <AcrescimosEditor
                              acrescimos={config.contratacao.acrescimos}
                              onChange={(acrescimos) =>
                                alterarConfig({ contratacao: { ...config.contratacao, acrescimos } })
                              }
                              tipos={[...opcoes.data.acrescimo_tipos, opcoes.data.acrescimo_tipo_bv]}
                            />

                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                alterarConfig({ contratacao: { ...CONTRATACAO_INICIAL } })
                              }
                            >
                              Remover contratação Manto
                            </Button>
                          </>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* ── Transporte ────────────────────────────────────────────── */}
              <Card>
                <CardHeader>
                  <CardTitle>Transporte</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={config.foraSp}
                      onChange={(e) => {
                        alterarConfig({ foraSp: e.target.checked });
                        setEnderecoMsg(null);
                      }}
                    />
                    Evento fora da cidade de São Paulo
                  </label>
                  <p className="text-xs text-muted">
                    {config.foraSp
                      ? "Fora de SP: o caminhão sai e entram 2 vans (uma com carretinha) — km ida e volta × dias + adicional por pessoa."
                      : "Dentro de SP: caminhão de cenografia incluso no valor; sem cálculo de km."}
                  </p>

                  {config.foraSp && (
                    <>
                      <div>
                        <label className={LABEL} htmlFor="endereco">
                          Endereço do evento
                        </label>
                        <div className="flex gap-2">
                          <GoogleAddressInput
                            id="endereco"
                            aria-label="Endereço do evento"
                            className="flex-1"
                            placeholder="Rua, número, cidade…"
                            value={config.endereco}
                            onChange={(valor) => alterarConfig({ endereco: valor })}
                            onSelectSuggestion={(description) => handleCalcularDistancia(description)}
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            loading={distancia.isPending}
                            onClick={() => handleCalcularDistancia()}
                          >
                            Calcular
                          </Button>
                        </div>
                        {enderecoMsg && (
                          <p className={`mt-1 text-xs ${enderecoMsg.error ? "text-red" : "text-muted"}`}>
                            {enderecoMsg.text}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className={LABEL} htmlFor="km_ida">
                          Km (ida)
                        </label>
                        <Input
                          id="km_ida"
                          type="number"
                          min={0}
                          step="any"
                          className="max-w-[160px]"
                          value={config.kmIda ?? ""}
                          onChange={(e) => {
                            const valor = e.target.value;
                            alterarConfig({ kmIda: valor === "" ? null : Math.max(0, Number(valor) || 0) });
                            setEnderecoMsg(null);
                          }}
                        />
                        <p className="mt-1 text-xs text-muted">
                          Preenchido pelo botão Calcular, mas editável — o transporte cobra ida e volta.
                        </p>
                      </div>

                      {transporte?.modo === "vans_fora_sp" && transporte.total > 0 && (
                        <div className="rounded-md bg-surface-2 px-3 py-2 text-sm text-ink">
                          🚐{" "}
                          <strong>
                            Transporte:{" "}
                            {transporte.dias > 1
                              ? `${brl(transporte.valor_viagem)} por viagem × ${transporte.dias} dias = ${brl(transporte.total)}`
                              : `${brl(transporte.total)} (1 viagem)`}
                          </strong>{" "}
                          <span className="text-muted">
                            — {transporte.km_total} km (ida e volta) · 2 vans (1 c/ carretinha) ·
                            adicional {transporte.pessoas} pessoa(s). Já somado ao valor final.
                          </span>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Acréscimo do vendedor</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted">
                    Valor acrescentado ao orçamento — esta é a sua comissão.
                  </p>
                  <MoneyInput
                    className={`${FIELD} w-40 text-right`}
                    value={config.acrescimo}
                    onValueChange={(valor) => alterarConfig({ acrescimo: valor })}
                    aria-label="Acréscimo do vendedor"
                  />
                  {resultado?.acrescimo_capado && (
                    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
                      <p className="font-semibold text-gold-ink">
                        ⚠️ Acima do máximo — só entrou {brl(resultado.acrescimo_efetivo)}
                      </p>
                      <p className="mt-0.5 text-ink">
                        A comissão não pode passar do valor desta página, que é{" "}
                        {brl(resultado.acrescimo_maximo)}. Os {brl(config.acrescimo)} digitados
                        foram cortados até esse teto.
                      </p>
                    </div>
                  )}
                  <div>
                    <label className={LABEL} htmlFor="client_name">
                      Nome do cliente (opcional)
                    </label>
                    <Input
                      id="client_name"
                      type="text"
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="observacao">
                      Observação no orçamento (opcional)
                    </label>
                    <textarea
                      id="observacao"
                      className={`${FIELD} h-24 resize-y py-2`}
                      maxLength={MAX_OBSERVACAO}
                      placeholder="Texto livre que sai formatado no PDF…"
                      value={observacao}
                      onChange={(e) => setObservacao(e.target.value)}
                    />
                    <p className="mt-1 text-right text-xs text-muted">
                      {observacao.length}/{MAX_OBSERVACAO}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* ── Resultado ─────────────────────────────────────────────── */}
            <div className="space-y-4">
              {totalDias <= 0 && (
                <p className="text-sm text-muted">Preencha os dias para calcular.</p>
              )}
              {config.foraSp && !config.kmIda && totalDias > 0 && (
                <p className="text-sm text-muted">
                  Informe os km de ida (ou calcule pelo endereço) para fechar o valor fora de SP.
                </p>
              )}

              {calcular.isError && (
                <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
                  {errorMessage(calcular.error, "Não foi possível calcular a configuração.")}
                </div>
              )}

              {calcular.isPending && totalDias > 0 && <Skeleton className="h-40 w-full" />}

              {resultado && totalDias > 0 && (
                <>
                  <p className="text-xs uppercase text-muted">{resultado.scenario}</p>
                  {resultado.desconto_aplicado && (
                    <p className="text-xs text-green">Desconto de duração aplicado</p>
                  )}

                  {/* Equipe do caso — matriz técnica visível pro vendedor conferir. */}
                  <div className="rounded-md bg-surface-2 px-3 py-2 text-sm text-ink">
                    👥 <strong>Equipe: {resultado.headcount} pessoas</strong>{" "}
                    <span className="text-muted">
                      — {resultado.tecnicos.map((t) => TECNICO_LABELS[t] ?? t).join(", ")}
                      {config.ensemble > 0 ? ` · +${config.ensemble} ensemble` : ""}
                    </span>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg border border-green bg-green-soft p-4">
                      <p className="text-xs font-semibold uppercase text-green">Sem Nota Fiscal</p>
                      <p className="text-2xl font-semibold text-ink">
                        {brl(resultado.valor_final_sem_nota)}
                      </p>
                      <div className="mt-2 space-y-0.5 text-xs text-ink/80">
                        <p>À vista (PIX, −5%): {brl(resultado.a_vista_sem_nota)}</p>
                        {breakdown && <p>Custo base: {brl(breakdown.raw_cost)}</p>}
                        <p>Comissão do vendedor: {brl(resultado.acrescimo_efetivo)}</p>
                      </div>
                    </div>
                    <div className="rounded-lg border border-blue bg-blue-soft p-4">
                      <p className="text-xs font-semibold uppercase text-blue">Com Nota Fiscal</p>
                      <p className="text-2xl font-semibold text-ink">
                        {brl(resultado.valor_final_com_nota)}
                      </p>
                      <div className="mt-2 space-y-0.5 text-xs text-ink/80">
                        <p>À vista (PIX, −5%): {brl(resultado.a_vista_com_nota)}</p>
                        {breakdown && <p>Custo base: {brl(breakdown.raw_cost)}</p>}
                        <p>Comissão do vendedor: {brl(resultado.acrescimo_efetivo)}</p>
                      </div>
                    </div>
                  </div>

                  {config.contratacao.ativa && (
                    <div
                      className="rounded-md border border-gold/40 bg-gold-soft px-3 py-2 text-xs font-medium text-gold-ink"
                      role="note"
                    >
                      ⚠️ Estes dois valores são só do EducaManto — NÃO incluem a contratação
                      Manto. Use os totais combinados abaixo.
                    </div>
                  )}

                  {resultado.combinados && Object.keys(resultado.combinados).length > 0 && (
                    <div className="rounded-lg border border-gold/60 bg-gold-soft p-4">
                      <p className="text-xs font-semibold uppercase text-gold-ink">
                        Totais com contratação Manto (NF sobre a soma)
                      </p>
                      <div className="mt-2 space-y-1 text-sm text-ink">
                        {Object.entries(resultado.combinados)
                          .sort(([a], [b]) => a.length - b.length || a.localeCompare(b))
                          .map(([dur, tot]) => (
                            <p key={dur}>
                              <strong>{dur}:</strong> {brl(tot.sem_nota)} sem NF ·{" "}
                              {brl(tot.com_nota)} com NF{" "}
                              <span className="text-xs text-muted">
                                (à vista {brl(tot.a_vista_sem)} / {brl(tot.a_vista_com)})
                              </span>
                            </p>
                          ))}
                      </div>
                    </div>
                  )}

                  {breakdown && (
                    <Card>
                      <CardContent className="p-0">
                        <AccordionRow
                          summary={<span className="p-3 font-medium text-ink">Ver detalhes de custos</span>}
                        >
                          <BreakdownTable breakdown={breakdown} />
                        </AccordionRow>
                      </CardContent>
                    </Card>
                  )}

                  {gerarMsg && (
                    <p className={`text-xs ${gerarMsg.error ? "text-red" : "text-muted"}`}>
                      {gerarMsg.text}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
