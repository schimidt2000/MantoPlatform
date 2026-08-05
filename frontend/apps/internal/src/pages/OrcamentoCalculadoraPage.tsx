import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
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
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { GoogleAddressInput } from "../components/GoogleAddressInput";
import { MemoriaDeCalculo } from "../components/MemoriaDeCalculo";
import {
  useCalcularOrcamento,
  useDistancia,
  useOrcamentoDetalhe,
  useOrcamentoHistorico,
  useOrcamentoOpcoes,
  usePersonagensNoDia,
  useSalvarOrcamento,
  type Acrescimo,
  type CalcularOrcamentoInput,
  type CalcularOrcamentoResult,
  type Performer,
} from "../lib/orcamento";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const CALC_DEBOUNCE_MS = 400;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function emptyPerformer(type: Performer["type"] = "ator"): Performer {
  return { type, subtipo: "cara_limpa", nome: "", show: false, makeup: false };
}

const DURACOES = ["1h", "2h", "3h", "4h"] as const;
type Duracao = (typeof DURACOES)[number];

const INITIAL_STATE = {
  performers: [] as Performer[],
  coordenadorQty: 1,
  eventDate: "",
  eventTime: "",
  clientName: "",
  eventLocation: "",
  foraSp: false,
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
};

function PerformerTableRow({
  performer,
  onChange,
  onRemove,
  especiais,
  especiaisComShow,
  especiaisComCantor,
}: {
  performer: Performer;
  onChange: (p: Performer) => void;
  onRemove: () => void;
  especiais: string[];
  especiaisComShow: string[];
  especiaisComCantor: string[];
}) {
  const canShow =
    performer.type === "ator" ||
    (performer.type === "especial" && especiaisComShow.includes(performer.personagem ?? ""));
  const canCantor =
    performer.type === "especial" && especiaisComCantor.includes(performer.personagem ?? "");

  return (
    <TableRow>
      <TableCell>
        {performer.type === "ator" ? (
          <select
            className={INPUT}
            value={performer.subtipo ?? "cara_limpa"}
            onChange={(e) => onChange({ ...performer, subtipo: e.target.value as Performer["subtipo"] })}
          >
            <option value="cara_limpa">Ator — Cara limpa</option>
            <option value="boneco">Ator — Boneco</option>
            <option value="cantor">Ator — Cantor</option>
          </select>
        ) : (
          <div className="space-y-1.5">
            <select
              className={INPUT}
              value={performer.personagem ?? ""}
              onChange={(e) => onChange({ ...performer, personagem: e.target.value })}
            >
              <option value="">Selecione o especial…</option>
              {especiais.map((nome) => (
                <option key={nome} value={nome}>
                  {nome}
                </option>
              ))}
            </select>
            {performer.personagem === "Boneco Grande Especial" && (
              <select
                className={INPUT}
                value={performer.bge_subtipo ?? ""}
                onChange={(e) =>
                  onChange({ ...performer, bge_subtipo: e.target.value as Performer["bge_subtipo"] })
                }
              >
                <option value="">Sub-tipo do BGE…</option>
                <option value="dinossauro">Dinossauro</option>
                <option value="transformers">Transformers</option>
                <option value="outro">Outro</option>
              </select>
            )}
            {performer.bge_subtipo === "outro" && (
              <input
                className={INPUT}
                placeholder="Nome do personagem"
                value={performer.bge_outro_nome ?? ""}
                onChange={(e) => onChange({ ...performer, bge_outro_nome: e.target.value })}
              />
            )}
          </div>
        )}
      </TableCell>
      <TableCell>
        <input
          className={INPUT}
          placeholder="Opcional"
          value={performer.nome ?? ""}
          onChange={(e) => onChange({ ...performer, nome: e.target.value })}
        />
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-1">
          {canShow && (
            <label className="flex items-center gap-1.5 text-xs text-ink">
              <input
                type="checkbox"
                checked={Boolean(performer.show)}
                onChange={(e) => onChange({ ...performer, show: e.target.checked })}
              />
              Com show
            </label>
          )}
          {canCantor && (
            <label className="flex items-center gap-1.5 text-xs text-ink">
              <input
                type="checkbox"
                checked={Boolean(performer.cantor)}
                onChange={(e) => onChange({ ...performer, cantor: e.target.checked })}
              />
              Com cantor
            </label>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-1">
          <label className="flex items-center gap-1.5 text-xs text-ink">
            <input
              type="checkbox"
              checked={Boolean(performer.makeup)}
              onChange={(e) => onChange({ ...performer, makeup: e.target.checked })}
            />
            Maquiagem
          </label>
          {performer.makeup && (
            <select
              className={`${INPUT} h-8 text-xs`}
              value={performer.makeup_tipo ?? "comum"}
              onChange={(e) => onChange({ ...performer, makeup_tipo: e.target.value as Performer["makeup_tipo"] })}
            >
              <option value="comum">Comum</option>
              <option value="especial">Especial</option>
            </select>
          )}
        </div>
      </TableCell>
      <TableCell align="right">
        <Button size="sm" variant="ghost" onClick={onRemove}>
          Remover
        </Button>
      </TableCell>
    </TableRow>
  );
}

/** Painel de alerta "Já na agenda neste dia" — evita venda em dobro de um personagem. */
function AgendaNoDiaAlert({ date }: { date: string }) {
  const dateValida = DATE_RE.test(date);
  const personagensNoDia = usePersonagensNoDia(dateValida ? date : "");
  const personagens = personagensNoDia.data?.personagens ?? [];

  if (!dateValida || !personagens.length) return null;

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm" role="alert">
      <p className="mb-1 font-semibold text-amber-800">⚠️ Já na agenda neste dia — não vender em dobro</p>
      <ul className="list-disc space-y-0.5 pl-4 text-amber-900">
        {personagens.map((p) => (
          <li key={p.nome}>
            <span className="font-medium">{p.nome}</span>
            {p.eventos.length > 0 && <span className="text-amber-700"> — {p.eventos.join(" · ")}</span>}
          </li>
        ))}
      </ul>
    </div>
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
  const [coordenadorQty, setCoordenadorQty] = useState(INITIAL_STATE.coordenadorQty);
  const [eventDate, setEventDate] = useState(INITIAL_STATE.eventDate);
  const [eventTime, setEventTime] = useState(INITIAL_STATE.eventTime);
  const [clientName, setClientName] = useState(INITIAL_STATE.clientName);
  const [eventLocation, setEventLocation] = useState(INITIAL_STATE.eventLocation);
  const [foraSp, setForaSp] = useState(INITIAL_STATE.foraSp);
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
  const [result, setResult] = useState<CalcularOrcamentoResult | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
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
    setCoordenadorQty(snap.coordenador_qty ?? 1);
    setEventDate(snap.event_date ?? "");
    setEventTime(snap.event_time ?? "");
    setClientName(snap.client_name ?? "");
    setEventLocation(snap.event_location ?? "");
    setForaSp(Boolean(snap.fora_sp));
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
    setResult(null);
    setSaved(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historicoDetalhe.data]);

  function resetAll() {
    setPerformers(INITIAL_STATE.performers);
    setCoordenadorQty(INITIAL_STATE.coordenadorQty);
    setEventDate(INITIAL_STATE.eventDate);
    setEventTime(INITIAL_STATE.eventTime);
    setClientName(INITIAL_STATE.clientName);
    setEventLocation(INITIAL_STATE.eventLocation);
    setForaSp(INITIAL_STATE.foraSp);
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
    setResult(null);
    setFieldErrors({});
    setSaved(false);
  }

  const toggleDuracao = (d: string) =>
    setIncluirDuracao((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));

  const addAcrescimo = () =>
    setAcrescimos((prev) => [...prev, { tipo: opcoes.data?.acrescimo_tipos[0] ?? "", value: 0, is_percent: false }]);

  const payload: CalcularOrcamentoInput = useMemo(
    () => ({
      performers,
      coordenador_qty: coordenadorQty,
      event_date: eventDate,
      event_time: eventTime,
      client_name: clientName,
      event_location: eventLocation,
      fora_sp: foraSp,
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
    }),
    [
      performers,
      coordenadorQty,
      eventDate,
      eventTime,
      clientName,
      eventLocation,
      foraSp,
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
    ],
  );

  // Cálculo 100% reativo — qualquer alteração no payload dispara o recálculo (com pequeno
  // debounce para não bombardear a API a cada tecla digitada). Sem botão manual.
  useEffect(() => {
    if (!opcoes.data) return;
    setFieldErrors({});
    setSaved(false);
    const timer = setTimeout(() => {
      calcular.mutate(payload, {
        onSuccess: (data) => setResult(data),
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      });
    }, CALC_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payload, opcoes.data]);

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
                      if (foraSp) handleCalcularDistancia(description);
                    }}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input type="checkbox" checked={foraSp} onChange={(e) => setForaSp(e.target.checked)} />
                  Evento Fora de São Paulo
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={LABEL}>Data</label>
                    <Input type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} />
                  </div>
                  <div>
                    <label className={LABEL}>Horário</label>
                    <Input type="time" value={eventTime} onChange={(e) => setEventTime(e.target.value)} />
                  </div>
                </div>

                {eventDate && <AgendaNoDiaAlert date={eventDate} />}

                {foraSp && (
                  <div className="space-y-3 rounded-md border border-amber-300 bg-amber-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                      Transporte — Fora de SP
                    </p>
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
                    {transporteTipo === "van" ? (
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
                    )}
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
            <Card>
              <CardHeader>
                <CardTitle>Equipe</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table className="min-w-[720px]">
                  <thead>
                    <TableRow head>
                      <TableCell as="th">Tipo / Subtipo</TableCell>
                      <TableCell as="th">Personagem/Nome</TableCell>
                      <TableCell as="th">Flags</TableCell>
                      <TableCell as="th">Maquiagem</TableCell>
                      <TableCell as="th" align="right">
                        Ações
                      </TableCell>
                    </TableRow>
                  </thead>
                  <tbody>
                    <TableRow>
                      <TableCell className="font-medium text-ink">Coordenador</TableCell>
                      <TableCell colSpan={2} className="text-xs text-muted">
                        Obrigatório — sempre presente na equipe
                      </TableCell>
                      <TableCell colSpan={2} align="right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setCoordenadorQty((q) => Math.max(0, q - 1))}
                          >
                            −
                          </Button>
                          <span className="w-6 text-center tabular-nums text-ink">{coordenadorQty}</span>
                          <Button size="sm" variant="outline" onClick={() => setCoordenadorQty((q) => q + 1)}>
                            +
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {performers.map((p, i) => (
                      <PerformerTableRow
                        key={i}
                        performer={p}
                        onChange={(np) => setPerformers((prev) => prev.map((x, idx) => (idx === i ? np : x)))}
                        onRemove={() => setPerformers((prev) => prev.filter((_, idx) => idx !== i))}
                        especiais={opcoes.data.especiais}
                        especiaisComShow={opcoes.data.especiais_com_show}
                        especiaisComCantor={opcoes.data.especiais_com_cantor}
                      />
                    ))}
                  </tbody>
                </Table>
                <div className="flex gap-2 p-3">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setPerformers((prev) => [...prev, emptyPerformer("ator")])}
                  >
                    + Ator / Cantor
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setPerformers((prev) => [...prev, emptyPerformer("especial")])}
                  >
                    + Especial
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Acréscimos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted">
                  O BV entra no total, mas é um repasse (não aparece para o cliente) e o PIX de quem
                  recebe é informado no evento.
                </p>
                {acrescimos.map((a, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <select
                      className={`${INPUT} max-w-[160px]`}
                      value={a.tipo}
                      onChange={(e) =>
                        setAcrescimos((prev) => prev.map((x, idx) => (idx === i ? { ...x, tipo: e.target.value } : x)))
                      }
                    >
                      {[...opcoes.data.acrescimo_tipos, opcoes.data.acrescimo_tipo_bv].map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <MoneyInput
                      className={`${INPUT} max-w-[120px]`}
                      value={a.value}
                      onValueChange={(v) =>
                        setAcrescimos((prev) => prev.map((x, idx) => (idx === i ? { ...x, value: v } : x)))
                      }
                    />
                    <label className="flex items-center gap-1 text-xs text-muted">
                      <input
                        type="checkbox"
                        checked={a.is_percent}
                        onChange={(e) =>
                          setAcrescimos((prev) =>
                            prev.map((x, idx) => (idx === i ? { ...x, is_percent: e.target.checked } : x)),
                          )
                        }
                      />
                      %
                    </label>
                    <Button size="sm" variant="ghost" onClick={() => setAcrescimos((prev) => prev.filter((_, idx) => idx !== i))}>
                      Remover
                    </Button>
                  </div>
                ))}
                <Button size="sm" variant="ghost" onClick={addAcrescimo}>
                  + Adicionar acréscimo
                </Button>
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
                  <p className="mt-1 text-xs text-muted">(preço = 4h + N × 4h × markup × 4h)</p>
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
              </CardContent>
            </Card>

            {calcular.isError && !Object.keys(fieldErrors).length && (
              <p className="text-sm text-red">Não foi possível calcular o orçamento.</p>
            )}
            {Object.values(fieldErrors).map((msg) => (
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
                  <div className={`grid grid-cols-2 gap-3 sm:grid-cols-4 transition-opacity ${calcular.isPending ? "opacity-50" : ""}`}>
                    {([
                      ["1 Hora", result.quote.show_1h, result.quote.total_1h],
                      ["2 Horas", result.quote.show_2h, result.quote.total_2h],
                      ["3 Horas", result.quote.show_3h, result.quote.total_3h],
                      ["4 Horas", result.quote.show_4h, result.quote.total_4h],
                    ] as const)
                      .filter(([, show]) => show)
                      .map(([label, , total]) => (
                        <div key={label} className="rounded-md bg-surface-2 p-3 text-center">
                          <p className="text-xs uppercase text-muted">{label}</p>
                          <p className="text-lg font-semibold text-ink">{brl(total)}</p>
                        </div>
                      ))}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <Button variant="outline" onClick={() => setMemoriaOpen(true)}>
                      Ver memória de cálculo
                    </Button>
                    <Button loading={salvar.isPending} onClick={handleSalvar} disabled={saved}>
                      {saved ? "Orçamento salvo" : "Gerar Orçamento"}
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
