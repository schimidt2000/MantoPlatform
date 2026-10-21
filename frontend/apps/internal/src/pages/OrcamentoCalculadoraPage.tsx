import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { GoogleAddressInput } from "../components/GoogleAddressInput";
import { MemoriaDeCalculo } from "../components/MemoriaDeCalculo";
import { AcrescimosEditor } from "../components/orcamento/AcrescimosEditor";
import { PerformersEditor } from "../components/orcamento/PerformersEditor";
import { ProdutoLinha } from "../components/orcamento/ProdutoLinha";
import { ProdutosCard, type ProdutoSelecionado } from "../components/orcamento/ProdutosCard";
import {
  useCalcularOrcamento,
  useDistancia,
  useOrcamentoDetalhe,
  useOrcamentoHistorico,
  useOrcamentoOpcoes,
  usePersonagensNoDia,
  useSalvarOrcamento,
  diaParaTela,
  type Acrescimo,
  type CalcularOrcamentoInput,
  type CalcularOrcamentoResult,
  type DuracaoDoDesconto,
  type Performer,
  type Quote,
} from "../lib/orcamento";
import { bvDe, pixDe } from "../lib/desconto";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const CALC_DEBOUNCE_MS = 400;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

const DURACOES = ["1h", "2h", "3h", "4h"] as const;
type Duracao = (typeof DURACOES)[number];

/**
 * Deslocamento do evento: "sp" (em São Paulo, sem deslocamento), "manto" (fora de SP com
 * transporte embutido no orçamento) ou "cliente" (fora de SP, contratante assume o veículo —
 * só os adicionais da equipe entram na conta). Vira `fora_sp` + `deslocamento_responsavel`
 * no payload. Na UI a escolha é em duas etapas: em SP × fora de SP e, fora de SP, a
 * responsabilidade (padrão "manto").
 */
type Deslocamento = "sp" | "manto" | "cliente";

const INITIAL_STATE = {
  performers: [] as Performer[],
  // Feature 309: produtos de tabela selecionados (a Visita Mágica), por chave; repetição permitida.
  produtos: [] as ProdutoSelecionado[],
  coordenadorQty: 1,
  eventDate: "",
  eventTime: "",
  clientName: "",
  eventLocation: "",
  deslocamento: "sp" as Deslocamento,
  transporteTipo: "van" as "van" | "carro",
  kmIda: 0,
  carretinha: false,
  numCarros: 1,
  numColaboradores: 0,
  notaFiscal: false,
  modoDuracao: "horas" as "horas" | "entradas",
  duracaoCustom: 0,
  incluirDuracao: ["1h", "2h", "3h", "4h"] as string[],
  acrescimos: [] as Acrescimo[],
  personalizadoAtivo: false,
  personalizadoCriterio: "valor_final" as "valor_final" | "multiplicador",
  custValores: { "1h": 0, "2h": 0, "3h": 0, "4h": 0 } as Record<Duracao, number>,
  custMult: { "1h": 0, "2h": 0, "3h": 0, "4h": 0 } as Record<Duracao, number>,
  // Feature 313 (Q8 = B): o desconto é bilateral — a comercial digita o % OU o valor final de uma duração; quem foi
  // digitado por último manda (`descontoModo`), e o outro a tela mostra pela resposta do servidor.
  descontoModo: "pct" as "pct" | "valor",
  descontoPct: 0,
  descontoValor: 0,
  descontoDuracao: "2h" as DuracaoDoDesconto,
};

/**
 * Uma duração no card Resultado (feature 313): o valor final, o cheio riscado quando há desconto, o PIX à vista e —
 * com BV — o BV a repassar a quem indicou (já com o desconto). Números do servidor; quote antigo sem as chaves mostra
 * só o total.
 */
function ResultadoDaDuracao({
  label,
  quote,
  coluna,
}: {
  label: string;
  quote: Quote;
  coluna: "1h" | "2h" | "3h" | "4h" | "custom";
}) {
  const total = coluna === "custom" ? (quote.total_custom ?? 0) : quote[`total_${coluna}`];
  const bruto = coluna === "custom" ? quote.bruto_custom : quote[`bruto_${coluna}`];
  const pix = pixDe(quote, coluna);
  const bv = bvDe(quote, coluna);
  return (
    <div className="rounded-md bg-surface-2 p-3 text-center">
      <p className="text-xs uppercase text-muted">{label}</p>
      {bruto != null && Math.abs(bruto - total) >= 0.005 && (
        <p className="text-xs text-muted line-through">{brl(bruto)}</p>
      )}
      <p className="text-lg font-semibold text-ink">{brl(total)}</p>
      {pix != null && <p className="text-xs text-muted">PIX à vista: {brl(pix)}</p>}
      {bv != null && <p className="text-xs text-muted">BV a repassar: {brl(bv)}</p>}
    </div>
  );
}

/** Painel de alerta "Já na agenda neste dia" — evita venda em dobro de um personagem. */
function AgendaNoDiaAlert({ date }: { date: string }) {
  const dateValida = DATE_RE.test(date);
  const personagensNoDia = usePersonagensNoDia(dateValida ? date : "");
  const personagens = personagensNoDia.data?.personagens ?? [];

  if (!dateValida || !personagens.length) return null;

  return (
    // `gold` (cor de atenção do design system) no lugar do `amber` cru do Tailwind: o amber é
    // sempre claro e não acompanha o tema — este alerta ficaria um retângulo bege berrante no
    // tema escuro. `gold-ink` no título e `ink` no corpo porque o dourado puro é cor de
    // preenchimento, não de texto (3.25:1 sobre o próprio fundo).
    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
      <p className="mb-1 font-semibold text-gold-ink">⚠️ Já na agenda neste dia — não vender em dobro</p>
      <ul className="list-disc space-y-0.5 pl-4 text-ink">
        {personagens.map((p) => (
          <li key={p.nome}>
            <span className="font-medium">{p.nome}</span>
            {p.eventos.length > 0 && <span className="text-muted"> — {p.eventos.join(" · ")}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** "3,34×", ou "3,34–3×" quando o markup varia por duração. */
function markupLegivel(markup: number[]): string {
  const min = Math.min(...markup);
  const max = Math.max(...markup);
  const f = (v: number) => v.toLocaleString("pt-BR");
  return min === max ? `${f(min)}×` : `${f(max)}–${f(min)}×`;
}

/** Lista em pt-BR: "24/12 e 25/12", "24/12, 25/12 e 26/12". */
function listaEmPortugues(itens: string[]): string {
  if (itens.length <= 1) return itens.join("");
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

/**
 * Feature 307: aviso "a tabela especial está valendo". A fonte é o próprio resultado do servidor
 * (`quote.data_especial`) — o React não recalcula a faixa. Mesmo padrão visual do alerta da agenda.
 * No personalizado o valor digitado vence, e o aviso diz isso em vez de prometer o markup.
 */
function DataEspecialAlert({
  faixa,
  personalizado,
}: {
  faixa: NonNullable<Quote["data_especial"]>;
  personalizado: boolean;
}) {
  const reduzir = useReducedMotion();
  const natal = faixa.chave === "natal";
  return (
    <motion.div
      initial={reduzir ? false : { opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduzir ? undefined : { opacity: 0, y: -4 }}
      transition={{ duration: 0.2 }}
      className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm"
      role="status"
    >
      <p className="mb-1 font-semibold text-gold-ink">
        {natal ? "🎄 " : ""}Data especial — {faixa.rotulo}
        {personalizado ? "" : `: markup ${markupLegivel(faixa.markup)} e cachês próprios`}
      </p>
      <p className="text-ink">
        {personalizado
          ? `Orçamento personalizado: o valor digitado vence — confira se cobre a tabela de ${faixa.rotulo}.`
          : "Vale para qualquer orçamento nesta data — o preço já é o da tabela especial."}
        {natal && !personalizado
          ? ' Use o item "Ajudante do Noel" (não ator cara limpa) e não some o acréscimo "Outro".'
          : ""}
      </p>
    </motion.div>
  );
}

export function OrcamentoCalculadoraPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const recalcularId = searchParams.get("recalcular_id");
  const recalcularIdNum = recalcularId ? Number(recalcularId) : null;

  const opcoes = useOrcamentoOpcoes();
  const calcular = useCalcularOrcamento();
  const salvar = useSalvarOrcamento();
  const historicoDetalhe = useOrcamentoDetalhe(recalcularIdNum);
  const historico = useOrcamentoHistorico({});
  const distancia = useDistancia();

  const [performers, setPerformers] = useState<Performer[]>(INITIAL_STATE.performers);
  const [produtos, setProdutos] = useState<ProdutoSelecionado[]>(INITIAL_STATE.produtos);
  const [coordenadorQty, setCoordenadorQty] = useState(INITIAL_STATE.coordenadorQty);
  const [eventDate, setEventDate] = useState(INITIAL_STATE.eventDate);
  const [eventTime, setEventTime] = useState(INITIAL_STATE.eventTime);
  const [clientName, setClientName] = useState(INITIAL_STATE.clientName);
  const [eventLocation, setEventLocation] = useState(INITIAL_STATE.eventLocation);
  const [deslocamento, setDeslocamento] = useState<Deslocamento>(INITIAL_STATE.deslocamento);
  const [transporteTipo, setTransporteTipo] = useState<"van" | "carro">(INITIAL_STATE.transporteTipo);
  const [kmIda, setKmIda] = useState(INITIAL_STATE.kmIda);
  const [carretinha, setCarretinha] = useState(INITIAL_STATE.carretinha);
  const [numCarros, setNumCarros] = useState(INITIAL_STATE.numCarros);
  const [numColaboradores, setNumColaboradores] = useState(INITIAL_STATE.numColaboradores);
  const [notaFiscal, setNotaFiscal] = useState(INITIAL_STATE.notaFiscal);
  const [modoDuracao, setModoDuracao] = useState<"horas" | "entradas">(INITIAL_STATE.modoDuracao);
  const [duracaoCustom, setDuracaoCustom] = useState(INITIAL_STATE.duracaoCustom);
  const [incluirDuracao, setIncluirDuracao] = useState<string[]>(INITIAL_STATE.incluirDuracao);
  const [acrescimos, setAcrescimos] = useState<Acrescimo[]>(INITIAL_STATE.acrescimos);
  const [personalizadoAtivo, setPersonalizadoAtivo] = useState(INITIAL_STATE.personalizadoAtivo);
  const [personalizadoCriterio, setPersonalizadoCriterio] = useState(INITIAL_STATE.personalizadoCriterio);
  const [custValores, setCustValores] = useState<Record<Duracao, number>>(INITIAL_STATE.custValores);
  const [custMult, setCustMult] = useState<Record<Duracao, number>>(INITIAL_STATE.custMult);
  const [descontoModo, setDescontoModo] = useState<"pct" | "valor">(INITIAL_STATE.descontoModo);
  const [descontoPct, setDescontoPct] = useState(INITIAL_STATE.descontoPct);
  const [descontoValor, setDescontoValor] = useState(INITIAL_STATE.descontoValor);
  const [descontoDuracao, setDescontoDuracao] = useState<DuracaoDoDesconto>(INITIAL_STATE.descontoDuracao);
  const [result, setResult] = useState<CalcularOrcamentoResult | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  // Feature 307: do payload mudar até a resposta chegar, `result` é de outra conta — durante os
  // 400 ms do debounce `calcular.isPending` ainda é false, e "Gerar Orçamento" salvaria o preço
  // da data anterior (o /salvar grava o que o navegador manda, sem recalcular). `seq` descarta a
  // resposta de um cálculo antigo que chegue depois de o payload ter mudado de novo.
  const [calcPendente, setCalcPendente] = useState(false);
  const seq = useRef(0);
  const [memoriaOpen, setMemoriaOpen] = useState(false);
  const [distanciaMsg, setDistanciaMsg] = useState<{ text: string; error: boolean } | null>(null);

  /**
   * Distância pela Distance Matrix (feature 195) — antes o KM era 100% manual aqui, enquanto o
   * EducaManto já calculava. `override` chega quando o usuário escolhe uma sugestão do Google: o
   * estado `eventLocation` ainda não refletiu o novo valor nesse tick.
   */
  function handleCalcularDistancia(override?: string) {
    const alvo = (override ?? eventLocation).trim();
    if (!alvo) {
      setDistanciaMsg({ text: "Informe o endereço do evento primeiro.", error: true });
      return;
    }
    setDistanciaMsg({ text: "Calculando…", error: false });
    distancia.mutate(alvo, {
      onSuccess: (data) => {
        setKmIda(data.km_ida);
        setDistanciaMsg({
          text: `Distância: ${data.km_ida} km (ida) · ${data.km_ida * 2} km ida e volta`,
          error: false,
        });
      },
      onError: (err) => {
        setDistanciaMsg({
          text:
            err instanceof ApiRequestError
              ? err.message
              : "Não foi possível calcular a distância.",
          error: true,
        });
      },
    });
  }

  // "Recalcular" — repopula o formulário a partir do form_snapshot de um orçamento salvo.
  useEffect(() => {
    const snap = historicoDetalhe.data?.form_snapshot;
    if (!snap) return;
    setPerformers(snap.performers ?? []);
    // Feature 309: só a chave volta — o preço é resolvido de novo pela tabela vigente ("Recalcular").
    setProdutos(snap.produtos?.map((p) => ({ chave: p.chave })) ?? []);
    setCoordenadorQty(snap.coordenador_qty ?? 1);
    setEventDate(snap.event_date ?? "");
    setEventTime(snap.event_time ?? "");
    setClientName(snap.client_name ?? "");
    setEventLocation(snap.event_location ?? "");
    // Snapshot pré-feature não tem `deslocamento_responsavel` — fora de SP era sempre "manto".
    setDeslocamento(
      !snap.fora_sp ? "sp" : snap.deslocamento_responsavel === "cliente" ? "cliente" : "manto",
    );
    setTransporteTipo(snap.transporte_tipo ?? "van");
    setKmIda(Number(snap.km_ida) || 0);
    setCarretinha(Boolean(snap.carretinha));
    setNumCarros(Number(snap.num_carros) || 1);
    setNumColaboradores(Number(snap.num_colaboradores) || 0);
    setNotaFiscal(Boolean(snap.nota_fiscal));
    setModoDuracao(snap.modo_duracao ?? "horas");
    setDuracaoCustom(Number(snap.duracao_custom) || 0);
    setAcrescimos(snap.acrescimos ?? []);
    setPersonalizadoAtivo(Boolean(snap.personalizado_ativo));
    // Feature 313: o desconto reabre como foi digitado; orçamento de antes (sem as chaves) reabre SEM desconto —
    // sem zerar aqui, ele herdaria o que estava digitado na tela.
    if (snap.desconto_valor && snap.desconto_duracao) {
      setDescontoModo("valor");
      setDescontoValor(snap.desconto_valor);
      setDescontoDuracao(snap.desconto_duracao);
      setDescontoPct(0);
    } else {
      setDescontoModo("pct");
      setDescontoPct(snap.desconto_pct_digitado ?? 0);
      setDescontoValor(0);
    }
    setResult(null);
    setSaved(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historicoDetalhe.data]);

  function resetAll() {
    setPerformers(INITIAL_STATE.performers);
    setProdutos(INITIAL_STATE.produtos);
    setCoordenadorQty(INITIAL_STATE.coordenadorQty);
    setEventDate(INITIAL_STATE.eventDate);
    setEventTime(INITIAL_STATE.eventTime);
    setClientName(INITIAL_STATE.clientName);
    setEventLocation(INITIAL_STATE.eventLocation);
    setDeslocamento(INITIAL_STATE.deslocamento);
    setTransporteTipo(INITIAL_STATE.transporteTipo);
    setKmIda(INITIAL_STATE.kmIda);
    setCarretinha(INITIAL_STATE.carretinha);
    setNumCarros(INITIAL_STATE.numCarros);
    setNumColaboradores(INITIAL_STATE.numColaboradores);
    setNotaFiscal(INITIAL_STATE.notaFiscal);
    setModoDuracao(INITIAL_STATE.modoDuracao);
    setDuracaoCustom(INITIAL_STATE.duracaoCustom);
    setIncluirDuracao(INITIAL_STATE.incluirDuracao);
    setAcrescimos(INITIAL_STATE.acrescimos);
    setPersonalizadoAtivo(INITIAL_STATE.personalizadoAtivo);
    setPersonalizadoCriterio(INITIAL_STATE.personalizadoCriterio);
    setCustValores(INITIAL_STATE.custValores);
    setCustMult(INITIAL_STATE.custMult);
    setDescontoModo(INITIAL_STATE.descontoModo);
    setDescontoPct(INITIAL_STATE.descontoPct);
    setDescontoValor(INITIAL_STATE.descontoValor);
    setDescontoDuracao(INITIAL_STATE.descontoDuracao);
    setResult(null);
    setFieldErrors({});
    setSaved(false);
  }

  const toggleDuracao = (d: string) =>
    setIncluirDuracao((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));

  const payload: CalcularOrcamentoInput = useMemo(
    () => ({
      performers,
      produtos,
      coordenador_qty: coordenadorQty,
      event_date: eventDate,
      event_time: eventTime,
      client_name: clientName,
      event_location: eventLocation,
      fora_sp: deslocamento !== "sp",
      deslocamento_responsavel: deslocamento !== "sp" ? deslocamento : undefined,
      transporte_tipo: transporteTipo,
      km_ida: kmIda,
      carretinha,
      num_carros: numCarros,
      num_colaboradores: numColaboradores || undefined,
      nota_fiscal: notaFiscal,
      modo_duracao: modoDuracao,
      duracao_custom: duracaoCustom || undefined,
      incluir_duracao: incluirDuracao,
      acrescimos,
      personalizado: personalizadoAtivo,
      personalizado_criterio: personalizadoAtivo ? personalizadoCriterio : undefined,
      cust_valor_1h: personalizadoAtivo && personalizadoCriterio === "valor_final" ? String(custValores["1h"]) : undefined,
      cust_valor_2h: personalizadoAtivo && personalizadoCriterio === "valor_final" ? String(custValores["2h"]) : undefined,
      cust_valor_3h: personalizadoAtivo && personalizadoCriterio === "valor_final" ? String(custValores["3h"]) : undefined,
      cust_valor_4h: personalizadoAtivo && personalizadoCriterio === "valor_final" ? String(custValores["4h"]) : undefined,
      cust_mult_1h: personalizadoAtivo && personalizadoCriterio === "multiplicador" ? String(custMult["1h"]) : undefined,
      cust_mult_2h: personalizadoAtivo && personalizadoCriterio === "multiplicador" ? String(custMult["2h"]) : undefined,
      cust_mult_3h: personalizadoAtivo && personalizadoCriterio === "multiplicador" ? String(custMult["3h"]) : undefined,
      cust_mult_4h: personalizadoAtivo && personalizadoCriterio === "multiplicador" ? String(custMult["4h"]) : undefined,
      // Feature 313: só o campo do modo ativo vai — o outro é leitura da resposta (sem laço de recálculo).
      desconto_pct: descontoModo === "pct" && descontoPct > 0 ? descontoPct : undefined,
      desconto_valor: descontoModo === "valor" && descontoValor > 0 ? descontoValor : undefined,
      desconto_duracao: descontoModo === "valor" && descontoValor > 0 ? descontoDuracao : undefined,
    }),
    [
      performers,
      produtos,
      coordenadorQty,
      eventDate,
      eventTime,
      clientName,
      eventLocation,
      deslocamento,
      transporteTipo,
      kmIda,
      carretinha,
      numCarros,
      numColaboradores,
      notaFiscal,
      modoDuracao,
      duracaoCustom,
      incluirDuracao,
      acrescimos,
      personalizadoAtivo,
      personalizadoCriterio,
      custValores,
      custMult,
      descontoModo,
      descontoPct,
      descontoValor,
      descontoDuracao,
    ],
  );

  // Cálculo 100% reativo — qualquer alteração no payload dispara o recálculo (com pequeno
  // debounce para não bombardear a API a cada tecla digitada). Sem botão manual.
  useEffect(() => {
    if (!opcoes.data) return;
    setFieldErrors({});
    setSaved(false);
    setCalcPendente(true);
    const meu = ++seq.current;
    const timer = setTimeout(() => {
      calcular.mutate(payload, {
        onSuccess: (data) => {
          if (meu === seq.current) setResult(data);
        },
        onError: (err) => {
          if (meu === seq.current && err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
        onSettled: () => {
          if (meu === seq.current) setCalcPendente(false);
        },
      });
    }, CALC_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payload, opcoes.data]);

  // Feature 307: a faixa de data especial vem do servidor, no resultado — fonte única. Enquanto o
  // recálculo não voltou (ou falhou), o `result` é de outra data: o aviso some para não mentir.
  const resultadoVivo = !(calcPendente || calcular.isPending || calcular.isError);
  const faixaAtiva = resultadoVivo ? (result?.quote.data_especial ?? null) : null;
  // Feature 309: avisos da conta (Noel avulso sem produto, preço estimado) — mesma regra: só do
  // resultado que corresponde ao payload atual.
  const avisosAtivos = resultadoVivo ? (result?.quote.avisos ?? []) : [];
  // Feature 313: as durações que aceitam "fechar por R$" são as que a proposta mostra (decisão do servidor: o
  // só-produto mostra um valor, a extra só quando existe); sem resultado ainda, as marcadas.
  const duracoesDoDesconto = useMemo((): { valor: DuracaoDoDesconto; rotulo: string }[] => {
    const q = result?.quote;
    if (!q) return DURACOES.filter((d) => incluirDuracao.includes(d)).map((d) => ({ valor: d, rotulo: d }));
    if (q.valor_unico) return [{ valor: "1h", rotulo: "Preço de tabela" }];
    const mostra: Record<Duracao, boolean> = { "1h": q.show_1h, "2h": q.show_2h, "3h": q.show_3h, "4h": q.show_4h };
    const ops: { valor: DuracaoDoDesconto; rotulo: string }[] = DURACOES.filter((d) => mostra[d]).map((d) => ({
      valor: d,
      rotulo: d,
    }));
    if (q.total_custom) ops.push({ valor: "extra", rotulo: `${q.duracao_custom}h` });
    return ops;
  }, [result, incluirDuracao]);
  useEffect(() => {
    if (!resultadoVivo || !duracoesDoDesconto.length) return;
    if (!duracoesDoDesconto.some((o) => o.valor === descontoDuracao)) setDescontoDuracao(duracoesDoDesconto[0].valor);
  }, [resultadoVivo, duracoesDoDesconto, descontoDuracao]);
  const descontoTexto = resultadoVivo ? (result?.quote.desconto_pct_texto ?? null) : null;
  const totalDaDuracaoDoDesconto = (() => {
    const q = resultadoVivo ? result?.quote : undefined;
    if (!q) return null;
    if (descontoDuracao === "extra") return q.total_custom ?? null;
    return { "1h": q.total_1h, "2h": q.total_2h, "3h": q.total_3h, "4h": q.total_4h }[descontoDuracao];
  })();
  const errosDoDesconto = ["desconto_pct", "desconto_valor"].map((k) => fieldErrors[k]).filter(Boolean);
  const tabelaDeProdutos = opcoes.data?.settings.produtos ?? {};
  // Janela de deploy (bundle novo, backend velho): com produto selecionado e `quote.produtos` ausente,
  // o servidor NÃO aplicou o produto — gerar gravaria um orçamento sem a Visita. Trava o botão.
  const produtoSemBackend = produtos.length > 0 && !!result && result.quote.produtos === undefined;
  const produtosAplicados = result?.quote.produtos ?? [];
  // Só produto no orçamento = UM valor rotulado "Preço de tabela" — decisão do SERVIDOR
  // (`quote.valor_unico`); inferir pelos `show_*` rotulava errado produto + avulso com 2h–4h desmarcadas.
  const valorUnico = result?.quote.valor_unico === true;
  // Coordenadores que a seleção traz pela tabela (para descontar do contador ao remover um produto).
  const coordenadoresDaSelecao = (selecao: ProdutoSelecionado[]) =>
    selecao.reduce(
      (n, sel) => n + (tabelaDeProdutos[sel.chave]?.vagas ?? []).filter((v) => v.tipo === "coordenador").length,
      0,
    );
  // Ao remover um produto, o contador desconta os coordenadores que ele trazia — senão o "+" dado
  // com o produto na tela viraria coordenador da fórmula cobrado sem a vendedora ter pedido.
  const handleProdutosChange = (next: ProdutoSelecionado[]) => {
    const retirados = coordenadoresDaSelecao(produtos) - coordenadoresDaSelecao(next);
    if (retirados > 0) setCoordenadorQty((q) => Math.max(1, q - retirados));
    setProdutos(next);
  };
  const diasEspeciais = useMemo(
    () =>
      listaEmPortugues(
        Object.values(opcoes.data?.settings.datas_especiais ?? {})
          .flatMap((f) => f.dias)
          .map(diaParaTela),
      ),
    [opcoes.data],
  );

  // "Gerar Orçamento" salva no histórico e ABRE o orçamento gerado — a tela onde se copia a
  // mensagem, baixa o PDF e envia por e-mail. Salvar sem levar para lá deixava o comercial sem
  // saída depois de calcular (era o fluxo do Jinja `orcamento/resultado.html`).
  const handleSalvar = () => {
    if (!result) return;
    salvar.mutate(result, {
      onSuccess: ({ id }) => {
        setSaved(true);
        navigate(`/orcamento/${id}`);
      },
    });
  };

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Calculadora de Orçamento"
        subtitle="Monte o elenco e calcule o orçamento do evento"
        className="mb-0"
        actions={
          <Button variant="ghost" size="sm" onClick={resetAll}>
            Limpar tudo
          </Button>
        }
      />

      {historicoDetalhe.isFetching && (
        <p className="text-xs text-muted">Carregando orçamento para recalcular…</p>
      )}

      {opcoes.isLoading && <Skeleton className="h-40 w-full" />}
      {opcoes.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as opções da calculadora.
        </div>
      )}

      {opcoes.data && (
        <div className="grid gap-4 lg:grid-cols-3 lg:items-start">
          {/* ── Coluna esquerda — Dados e Segurança (1/3) ────────────────────── */}
          <div className="space-y-4 lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Dados do Evento</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className={LABEL}>Cliente</label>
                  <Input value={clientName} onChange={(e) => setClientName(e.target.value)} />
                </div>
                <div>
                  <label className={LABEL}>Local/Endereço do evento</label>
                  {/* Autocomplete do Google Places (feature 195, Princípio X.3) — endereço
                      normalizado é o que faz o botão "Calcular km (Maps)" acertar a distância. */}
                  <GoogleAddressInput
                    aria-label="Local/Endereço do evento"
                    value={eventLocation}
                    onChange={setEventLocation}
                    onSelectSuggestion={(description) => {
                      if (deslocamento !== "sp") handleCalcularDistancia(description);
                    }}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={deslocamento === "sp" ? "default" : "outline"}
                    onClick={() => setDeslocamento("sp")}
                  >
                    Evento em São Paulo
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={deslocamento !== "sp" ? "default" : "outline"}
                    onClick={() => {
                      // Já estando fora de SP, reclicar não pode descartar a escolha "cliente".
                      if (deslocamento === "sp") setDeslocamento("manto");
                    }}
                  >
                    Evento fora de São Paulo
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={LABEL}>Data</label>
                    <Input type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} />
                    {/* A data é opcional e o preço de Natal depende dela: sem data, preço comum. */}
                    {!eventDate && diasEspeciais && (
                      <p className="mt-1 text-xs text-muted">
                        Em {diasEspeciais} a tabela especial entra pela data.
                      </p>
                    )}
                  </div>
                  <div>
                    <label className={LABEL}>Horário</label>
                    <Input type="time" value={eventTime} onChange={(e) => setEventTime(e.target.value)} />
                  </div>
                </div>

                {eventDate && <AgendaNoDiaAlert date={eventDate} />}
                <AnimatePresence initial={false}>
                  {faixaAtiva && (
                    <DataEspecialAlert
                      key={faixaAtiva.chave}
                      faixa={faixaAtiva}
                      personalizado={!!result?.quote.personalizado}
                    />
                  )}
                </AnimatePresence>
                {/* Feature 309: avisos da conta vindos do servidor — borda cheia (não /40) porque
                    pedem ação da vendedora antes de enviar ("use o produto", "preço estimado"). */}
                {avisosAtivos.length > 0 && (
                  <div className="space-y-1 rounded-md border border-gold bg-gold-soft p-3 text-sm" role="alert">
                    {avisosAtivos.map((aviso) => (
                      <p key={aviso} className="text-ink">
                        <span className="font-semibold text-gold-ink">⚠️ </span>
                        {aviso}
                      </p>
                    ))}
                  </div>
                )}

                {deslocamento !== "sp" && (
                  // Mesmo motivo do alerta acima: `amber` cru não troca de tema.
                  <div className="space-y-3 rounded-md border border-gold/40 bg-gold-soft p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gold-ink">
                      {deslocamento === "cliente" ? "Adicionais — Fora de SP" : "Transporte — Fora de SP"}
                    </p>
                    <div>
                      <label className={LABEL}>Deslocamento</label>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={deslocamento === "manto" ? "default" : "outline"}
                          onClick={() => setDeslocamento("manto")}
                        >
                          Por nossa conta
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant={deslocamento === "cliente" ? "default" : "outline"}
                          onClick={() => setDeslocamento("cliente")}
                        >
                          Por conta da cliente
                        </Button>
                      </div>
                    </div>
                    {/* Veículo só quando o deslocamento é da Manto; no modo "cliente" o km e os
                        colaboradores continuam necessários (adicional por pessoa fora de SP). */}
                    {deslocamento === "manto" && (
                      <div>
                        <label className={LABEL}>Tipo de transporte</label>
                        <select
                          className={INPUT}
                          value={transporteTipo}
                          onChange={(e) => setTransporteTipo(e.target.value as "van" | "carro")}
                        >
                          <option value="van">Van</option>
                          <option value="carro">Carro</option>
                        </select>
                      </div>
                    )}
                    <div>
                      <label className={LABEL}>Km (ida)</label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          value={kmIda}
                          onChange={(e) => setKmIda(Number(e.target.value))}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          loading={distancia.isPending}
                          onClick={() => handleCalcularDistancia()}
                        >
                          Calcular km (Maps)
                        </Button>
                      </div>
                      {distanciaMsg && (
                        <p className={`mt-1 text-xs ${distanciaMsg.error ? "text-red" : "text-muted"}`}>
                          {distanciaMsg.text}
                        </p>
                      )}
                    </div>
                    {deslocamento === "manto" &&
                      (transporteTipo === "van" ? (
                        <label className="flex items-center gap-2 text-sm text-ink">
                          <input type="checkbox" checked={carretinha} onChange={(e) => setCarretinha(e.target.checked)} />
                          Com carretinha
                        </label>
                      ) : (
                        <div>
                          <label className={LABEL}>Nº de carros</label>
                          <Input
                            type="number"
                            min={1}
                            value={numCarros}
                            onChange={(e) => setNumCarros(Number(e.target.value))}
                          />
                        </div>
                      ))}
                    <div>
                      <label className={LABEL}>Nº de colaboradores (opcional)</label>
                      <Input
                        type="number"
                        value={numColaboradores}
                        onChange={(e) => setNumColaboradores(Number(e.target.value))}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Link to="/orcamento/historico" className="flex items-center gap-2 text-sm text-accent hover:underline">
              Histórico de Orçamentos
              {historico.data && (
                <Badge tone="accent">{historico.data.entries.length}</Badge>
              )}
            </Link>
          </div>

          {/* ── Coluna direita — Equipe, Customização e Resultados (2/3) ─────── */}
          <div className="space-y-4 lg:col-span-2">
            {/* Feature 309: o pacote fechado vem ANTES da equipe — é por onde a Visita Mágica se vende;
                sem produtos na tabela (ou backend velho) o card não existe. */}
            {/* `produtos.length > 0` cobre o recalcular de um orçamento cujo produto sumiu da tabela:
                sem o card não haveria como removê-lo. */}
            {(Object.keys(tabelaDeProdutos).length > 0 || produtos.length > 0) && (
              <ProdutosCard
                produtos={tabelaDeProdutos}
                selecionados={produtos}
                aplicados={resultadoVivo ? result?.quote.produtos : undefined}
                calculando={calcPendente || calcular.isPending}
                onChange={handleProdutosChange}
              />
            )}

            <Card>
              <CardHeader>
                <CardTitle>Equipe</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <PerformersEditor
                  performers={performers}
                  onPerformersChange={setPerformers}
                  coordenadorQty={coordenadorQty}
                  onCoordenadorQtyChange={setCoordenadorQty}
                  especiais={opcoes.data.especiais}
                  especiaisComShow={opcoes.data.especiais_com_show}
                  especiaisComCantor={opcoes.data.especiais_com_cantor}
                  coordenadoresInclusos={result?.quote.coordenadores_inclusos ?? 0}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Acréscimos</CardTitle>
              </CardHeader>
              <CardContent>
                <AcrescimosEditor
                  acrescimos={acrescimos}
                  onChange={setAcrescimos}
                  tipos={[...opcoes.data.acrescimo_tipos, opcoes.data.acrescimo_tipo_bv]}
                  tipoBv={opcoes.data.acrescimo_tipo_bv}
                  ajuda="O acréscimo em R$ entra uma vez, em qualquer duração; o BV é calculado sobre o valor com os acréscimos (o BV em reais também entra uma vez) e acompanha o desconto. O BV é um repasse — não aparece para o cliente — e o PIX de quem recebe é informado no evento."
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Ajustes Finos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input type="checkbox" checked={notaFiscal} onChange={(e) => setNotaFiscal(e.target.checked)} />
                    Emitir Nota Fiscal
                  </label>
                  <Badge tone="green">0.84 — valores ajustados para NF</Badge>
                </div>

                <div>
                  <label className={LABEL}>Duração extra</label>
                  <Input
                    type="number"
                    min={0}
                    className="max-w-[140px]"
                    value={duracaoCustom}
                    onChange={(e) => setDuracaoCustom(Number(e.target.value))}
                  />
                  <p className="mt-1 text-xs text-muted">
                    (preço = apresentação e transporte de 4h ÷ 4 × horas; os acréscimos em R$ entram uma vez; o BV é
                    calculado sobre tudo isso; a nota no fim. O produto de tabela não muda com as horas.)
                  </p>
                </div>

                <div>
                  <label className={LABEL}>Formato do orçamento</label>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={modoDuracao === "horas" ? "default" : "outline"}
                      onClick={() => setModoDuracao("horas")}
                    >
                      Por horas
                    </Button>
                    <Button
                      size="sm"
                      variant={modoDuracao === "entradas" ? "default" : "outline"}
                      onClick={() => setModoDuracao("entradas")}
                    >
                      Por entradas
                    </Button>
                  </div>
                </div>

                <div>
                  <label className={LABEL}>Incluir no orçamento</label>
                  <div className="flex flex-wrap gap-3">
                    {DURACOES.map((d) => (
                      <label key={d} className="flex items-center gap-1 text-sm text-ink">
                        <input type="checkbox" checked={incluirDuracao.includes(d)} onChange={() => toggleDuracao(d)} />
                        {d}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="rounded-md border border-line">
                  <label className="flex items-center gap-2 p-3 text-sm font-medium text-ink">
                    <input
                      type="checkbox"
                      checked={personalizadoAtivo}
                      onChange={(e) => setPersonalizadoAtivo(e.target.checked)}
                    />
                    Personalizar valores
                    <span className="text-xs font-normal text-muted">
                      define o valor final do orçamento manualmente
                    </span>
                  </label>
                  {personalizadoAtivo && (
                    <div className="space-y-3 border-t border-line p-3">
                      <p className="text-xs text-muted">O desconto negociado (abaixo) incide também sobre estes valores.</p>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant={personalizadoCriterio === "valor_final" ? "default" : "outline"}
                          onClick={() => setPersonalizadoCriterio("valor_final")}
                        >
                          Definir valor final
                        </Button>
                        <Button
                          size="sm"
                          variant={personalizadoCriterio === "multiplicador" ? "default" : "outline"}
                          onClick={() => setPersonalizadoCriterio("multiplicador")}
                        >
                          Mudar multiplicador
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        {DURACOES.map((d) => (
                          <div key={d}>
                            <label className={LABEL}>{d}</label>
                            {personalizadoCriterio === "valor_final" ? (
                              <MoneyInput
                                className={INPUT}
                                value={custValores[d]}
                                onValueChange={(v) => setCustValores((prev) => ({ ...prev, [d]: v }))}
                              />
                            ) : (
                              <Input
                                type="number"
                                min={0}
                                step={0.01}
                                value={custMult[d]}
                                onChange={(e) => setCustMult((prev) => ({ ...prev, [d]: Number(e.target.value) }))}
                              />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Feature 313 (D3, Q1 = A, Q8 = B): o desconto negociado, sobre o total — em % ou pelo valor final. */}
                <div className="rounded-md border border-line p-3">
                  <p className="text-sm font-medium text-ink">Desconto negociado</p>
                  <p className="mb-3 text-xs text-muted">
                    Sobre o total (transporte, acréscimos e nota inclusos). O PIX à vista de 5% continua sozinho e vale
                    o maior entre ele e este desconto.
                  </p>
                  <div className="flex flex-wrap items-end gap-3">
                    <div>
                      <label className={LABEL} htmlFor="desconto-pct">
                        Desconto (%)
                      </label>
                      <Input
                        id="desconto-pct"
                        type="number"
                        min={0}
                        max={99.99}
                        step={0.01}
                        className="max-w-[120px]"
                        value={descontoModo === "pct" && descontoPct ? descontoPct : ""}
                        placeholder={descontoModo === "valor" && descontoTexto ? descontoTexto : "0"}
                        onChange={(e) => {
                          setDescontoModo("pct");
                          setDescontoPct(Number(e.target.value) || 0);
                        }}
                        aria-invalid={Boolean(fieldErrors.desconto_pct)}
                      />
                    </div>
                    <div>
                      <label className={LABEL} htmlFor="desconto-duracao">
                        ou fechar
                      </label>
                      <select
                        id="desconto-duracao"
                        className={`${INPUT} w-auto`}
                        value={descontoDuracao}
                        onChange={(e) => setDescontoDuracao(e.target.value as DuracaoDoDesconto)}
                      >
                        {duracoesDoDesconto.map((o) => (
                          <option key={o.valor} value={o.valor}>
                            {o.rotulo}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={LABEL} htmlFor="desconto-valor">
                        por (R$)
                      </label>
                      <MoneyInput
                        id="desconto-valor"
                        className={`${INPUT} max-w-[160px]`}
                        value={descontoModo === "valor" ? descontoValor : 0}
                        onValueChange={(v) => {
                          setDescontoModo("valor");
                          setDescontoValor(v);
                        }}
                        aria-invalid={Boolean(fieldErrors.desconto_valor)}
                      />
                    </div>
                    {(descontoPct > 0 || descontoValor > 0) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setDescontoPct(0);
                          setDescontoValor(0);
                          setDescontoModo("pct");
                        }}
                      >
                        Sem desconto
                      </Button>
                    )}
                  </div>
                  {resultadoVivo && descontoModo === "pct" && descontoPct > 0 && totalDaDuracaoDoDesconto != null && (
                    <p className="mt-2 text-xs text-muted">
                      Fecha {duracoesDoDesconto.find((o) => o.valor === descontoDuracao)?.rotulo ?? descontoDuracao}{" "}
                      por {brl(totalDaDuracaoDoDesconto)}.
                    </p>
                  )}
                  {descontoModo === "valor" && descontoValor > 0 && descontoTexto && (
                    <p className="mt-2 text-xs text-muted">
                      = {descontoTexto}% de desconto, aplicado também nas outras durações.
                    </p>
                  )}
                  {errosDoDesconto.map((msg) => (
                    <p key={msg} className="mt-2 text-sm text-red" role="alert">
                      {msg}
                    </p>
                  ))}
                </div>
              </CardContent>
            </Card>

            {calcular.isError && !Object.keys(fieldErrors).length && (
              <p className="text-sm text-red">Não foi possível calcular o orçamento.</p>
            )}
            {Object.entries(fieldErrors)
              .filter(([campo]) => campo !== "desconto_pct" && campo !== "desconto_valor")
              .map(([, msg]) => msg)
              .map((msg) => (
              <p key={msg} className="text-sm text-red">
                {msg}
              </p>
            ))}

            {result && (
              <Card>
                <CardHeader>
                  <CardTitle>Resultado</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Feature 313: fora do resultado vivo (debounce, conta velha, erro) os números ficam esmaecidos e
                      marcados — o card não mostra a conta anterior como se valesse para a entrada nova. */}
                  {!resultadoVivo && (
                    <p className="text-xs text-muted" role="status">
                      {calcular.isError ? "Corrija os campos para recalcular." : "Recalculando…"}
                    </p>
                  )}
                  <div className={`grid grid-cols-2 gap-3 sm:grid-cols-4 transition-opacity ${resultadoVivo ? "" : "opacity-50"}`}>
                    {(
                      [
                        [valorUnico ? "Preço de tabela" : "1 Hora", result.quote.show_1h, "1h"],
                        ["2 Horas", result.quote.show_2h, "2h"],
                        ["3 Horas", result.quote.show_3h, "3h"],
                        ["4 Horas", result.quote.show_4h, "4h"],
                        [`${result.quote.duracao_custom} Horas`, Boolean(result.quote.total_custom) && !valorUnico, "custom"],
                      ] as const
                    )
                      .filter(([, show]) => show)
                      .map(([label, , coluna]) => (
                        <ResultadoDaDuracao key={label} label={label} quote={result.quote} coluna={coluna} />
                      ))}
                  </div>
                  {result.quote.desconto_pct_texto && (
                    <p className="text-sm text-muted">
                      Desconto de {result.quote.desconto_pct_texto}% sobre o total; o BV a repassar acompanha.
                    </p>
                  )}
                  {/* Feature 307: o resultado diz quando caiu numa faixa de data especial. */}
                  {result.quote.data_especial && (
                    <p className="text-sm text-muted">
                      🎄 Valores da data especial: {result.quote.data_especial.rotulo}.
                    </p>
                  )}
                  {/* Feature 309: o que foi vendido pela tabela, com o preço que o servidor resolveu. */}
                  {produtosAplicados.length > 0 && (
                    <div className="space-y-1">
                      {produtosAplicados.map((p, i) => (
                        <ProdutoLinha key={`${p.chave}-${i}`} produto={p} compacta />
                      ))}
                    </div>
                  )}
                  {produtoSemBackend && (
                    <p className="text-sm text-red" role="alert">
                      O servidor não aplicou o produto — recarregue a página.
                    </p>
                  )}
                  <div className="flex items-center justify-between gap-2">
                    <Button variant="outline" onClick={() => setMemoriaOpen(true)}>
                      Ver memória de cálculo
                    </Button>
                    <Button
                      loading={salvar.isPending}
                      onClick={handleSalvar}
                      disabled={
                        saved || calcPendente || calcular.isPending || calcular.isError || produtoSemBackend
                      }
                    >
                      {saved ? "Orçamento salvo" : calcPendente || calcular.isPending ? "Recalculando…" : "Gerar Orçamento"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      <Dialog open={memoriaOpen} onOpenChange={setMemoriaOpen}>
        <DialogContent open={memoriaOpen} className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Memória de cálculo</DialogTitle>
          </DialogHeader>
          <div className="max-h-[65vh] overflow-y-auto">
            <MemoriaDeCalculo linhas={result?.quote.memoria} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
