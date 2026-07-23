import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import {
  useCalcularOrcamento,
  useOrcamentoOpcoes,
  useSalvarOrcamento,
  type Acrescimo,
  type CalcularOrcamentoResult,
  type Performer,
} from "../lib/orcamento";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function emptyPerformer(): Performer {
  return { type: "ator", subtipo: "cara_limpa", nome: "", show: false, makeup: false };
}

function PerformerRow({
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
  return (
    <div className="space-y-2 rounded-md border border-line p-3">
      <div className="flex items-center justify-between">
        <select
          className={INPUT + " max-w-[160px]"}
          value={performer.type}
          onChange={(e) =>
            onChange({ ...emptyPerformer(), type: e.target.value as Performer["type"] })
          }
        >
          <option value="ator">Ator</option>
          <option value="especial">Especial</option>
        </select>
        <Button size="sm" variant="ghost" onClick={onRemove}>
          Remover
        </Button>
      </div>

      <div>
        <label className={LABEL}>Nome/personagem (opcional)</label>
        <input
          className={INPUT}
          value={performer.nome ?? ""}
          onChange={(e) => onChange({ ...performer, nome: e.target.value })}
        />
      </div>

      {performer.type === "ator" && (
        <div>
          <label className={LABEL}>Subtipo</label>
          <select
            className={INPUT}
            value={performer.subtipo ?? "cara_limpa"}
            onChange={(e) => onChange({ ...performer, subtipo: e.target.value as Performer["subtipo"] })}
          >
            <option value="cara_limpa">Cara limpa</option>
            <option value="boneco">Boneco</option>
            <option value="cantor">Cantor</option>
          </select>
        </div>
      )}

      {performer.type === "especial" && (
        <>
          <div>
            <label className={LABEL}>Personagem</label>
            <select
              className={INPUT}
              value={performer.personagem ?? ""}
              onChange={(e) => onChange({ ...performer, personagem: e.target.value })}
            >
              <option value="">Selecione…</option>
              {especiais.map((nome) => (
                <option key={nome} value={nome}>
                  {nome}
                </option>
              ))}
            </select>
          </div>
          {performer.personagem === "Boneco Grande Especial" && (
            <div>
              <label className={LABEL}>Sub-tipo do BGE</label>
              <select
                className={INPUT}
                value={performer.bge_subtipo ?? ""}
                onChange={(e) =>
                  onChange({ ...performer, bge_subtipo: e.target.value as Performer["bge_subtipo"] })
                }
              >
                <option value="">Selecione…</option>
                <option value="dinossauro">Dinossauro</option>
                <option value="transformers">Transformers</option>
                <option value="outro">Outro</option>
              </select>
              {performer.bge_subtipo === "outro" && (
                <input
                  className={`${INPUT} mt-2`}
                  placeholder="Nome do personagem"
                  value={performer.bge_outro_nome ?? ""}
                  onChange={(e) => onChange({ ...performer, bge_outro_nome: e.target.value })}
                />
              )}
            </div>
          )}
          {especiaisComCantor.includes(performer.personagem ?? "") && (
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={Boolean(performer.cantor)}
                onChange={(e) => onChange({ ...performer, cantor: e.target.checked })}
              />
              Com cantor
            </label>
          )}
        </>
      )}

      {(performer.type === "ator" ||
        (performer.type === "especial" && especiaisComShow.includes(performer.personagem ?? ""))) && (
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={Boolean(performer.show)}
            onChange={(e) => onChange({ ...performer, show: e.target.checked })}
          />
          Com show
        </label>
      )}

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={Boolean(performer.makeup)}
          onChange={(e) => onChange({ ...performer, makeup: e.target.checked })}
        />
        Maquiagem
      </label>
      {performer.makeup && (
        <select
          className={INPUT}
          value={performer.makeup_tipo ?? "comum"}
          onChange={(e) => onChange({ ...performer, makeup_tipo: e.target.value as Performer["makeup_tipo"] })}
        >
          <option value="comum">Comum</option>
          <option value="especial">Especial</option>
        </select>
      )}
    </div>
  );
}

const DURACOES = ["1h", "2h", "3h", "4h"] as const;

export function OrcamentoCalculadoraPage() {
  const opcoes = useOrcamentoOpcoes();
  const calcular = useCalcularOrcamento();
  const salvar = useSalvarOrcamento();

  const [performers, setPerformers] = useState<Performer[]>([emptyPerformer()]);
  const [coordenadorQty, setCoordenadorQty] = useState(1);
  const [eventDate, setEventDate] = useState("");
  const [eventTime, setEventTime] = useState("");
  const [clientName, setClientName] = useState("");
  const [eventLocation, setEventLocation] = useState("");
  const [foraSp, setForaSp] = useState(false);
  const [transporteTipo, setTransporteTipo] = useState<"van" | "carro">("van");
  const [kmIda, setKmIda] = useState(0);
  const [carretinha, setCarretinha] = useState(false);
  const [numCarros, setNumCarros] = useState(1);
  const [numColaboradores, setNumColaboradores] = useState(0);
  const [notaFiscal, setNotaFiscal] = useState(false);
  const [modoDuracao, setModoDuracao] = useState<"horas" | "entradas">("horas");
  const [incluirDuracao, setIncluirDuracao] = useState<string[]>(["1h", "2h", "3h", "4h"]);
  const [acrescimos, setAcrescimos] = useState<Acrescimo[]>([]);
  const [result, setResult] = useState<CalcularOrcamentoResult | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  const toggleDuracao = (d: string) =>
    setIncluirDuracao((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));

  const addAcrescimo = () =>
    setAcrescimos((prev) => [...prev, { tipo: opcoes.data?.acrescimo_tipos[0] ?? "", value: 0, is_percent: false }]);

  const handleCalcular = () => {
    setFieldErrors({});
    setSaved(false);
    calcular.mutate(
      {
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
        incluir_duracao: incluirDuracao,
        acrescimos,
      },
      {
        onSuccess: (data) => setResult(data),
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      },
    );
  };

  const handleSalvar = () => {
    if (!result) return;
    salvar.mutate(result, { onSuccess: () => setSaved(true) });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Calculadora de Orçamento"
        subtitle="Monte o elenco e calcule o orçamento do evento"
        className="mb-0"
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/orcamento/historico">Histórico ›</Link>
          </Button>
        }
      />

      {opcoes.isLoading && <Skeleton className="h-40 w-full" />}
      {opcoes.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as opções da calculadora.
        </div>
      )}

      {opcoes.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Evento</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Cliente</label>
                <input className={INPUT} value={clientName} onChange={(e) => setClientName(e.target.value)} />
              </div>
              <div>
                <label className={LABEL}>Local</label>
                <input className={INPUT} value={eventLocation} onChange={(e) => setEventLocation(e.target.value)} />
              </div>
              <div>
                <label className={LABEL}>Data</label>
                <input type="date" className={INPUT} value={eventDate} onChange={(e) => setEventDate(e.target.value)} />
              </div>
              <div>
                <label className={LABEL}>Horário</label>
                <input type="time" className={INPUT} value={eventTime} onChange={(e) => setEventTime(e.target.value)} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Elenco</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className={LABEL}>Coordenadores</label>
                <input
                  type="number"
                  min={0}
                  className={`${INPUT} max-w-[120px]`}
                  value={coordenadorQty}
                  onChange={(e) => setCoordenadorQty(Number(e.target.value))}
                />
              </div>
              {performers.map((p, i) => (
                <PerformerRow
                  key={i}
                  performer={p}
                  onChange={(np) => setPerformers((prev) => prev.map((x, idx) => (idx === i ? np : x)))}
                  onRemove={() => setPerformers((prev) => prev.filter((_, idx) => idx !== i))}
                  especiais={opcoes.data.especiais}
                  especiaisComShow={opcoes.data.especiais_com_show}
                  especiaisComCantor={opcoes.data.especiais_com_cantor}
                />
              ))}
              <Button size="sm" variant="ghost" onClick={() => setPerformers((prev) => [...prev, emptyPerformer()])}>
                + Adicionar personagem
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Transporte</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={foraSp} onChange={(e) => setForaSp(e.target.checked)} />
                Fora de São Paulo (capital)
              </label>
              {foraSp && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className={LABEL}>Tipo</label>
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
                    <input
                      type="number"
                      className={INPUT}
                      value={kmIda}
                      onChange={(e) => setKmIda(Number(e.target.value))}
                    />
                  </div>
                  {transporteTipo === "van" ? (
                    <label className="flex items-center gap-2 text-sm text-ink">
                      <input type="checkbox" checked={carretinha} onChange={(e) => setCarretinha(e.target.checked)} />
                      Com carretinha
                    </label>
                  ) : (
                    <div>
                      <label className={LABEL}>Nº de carros</label>
                      <input
                        type="number"
                        min={1}
                        className={INPUT}
                        value={numCarros}
                        onChange={(e) => setNumCarros(Number(e.target.value))}
                      />
                    </div>
                  )}
                  <div>
                    <label className={LABEL}>Nº de colaboradores (opcional)</label>
                    <input
                      type="number"
                      className={INPUT}
                      value={numColaboradores}
                      onChange={(e) => setNumColaboradores(Number(e.target.value))}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Acréscimos e opções</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
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

              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={notaFiscal} onChange={(e) => setNotaFiscal(e.target.checked)} />
                Com Nota Fiscal
              </label>

              <div>
                <label className={LABEL}>Modo de duração</label>
                <select
                  className={`${INPUT} max-w-[200px]`}
                  value={modoDuracao}
                  onChange={(e) => setModoDuracao(e.target.value as "horas" | "entradas")}
                >
                  <option value="horas">Horas</option>
                  <option value="entradas">Entradas de 30 min</option>
                </select>
              </div>

              <div>
                <label className={LABEL}>Durações a incluir</label>
                <div className="flex gap-3">
                  {DURACOES.map((d) => (
                    <label key={d} className="flex items-center gap-1 text-sm text-ink">
                      <input type="checkbox" checked={incluirDuracao.includes(d)} onChange={() => toggleDuracao(d)} />
                      {d}
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Button loading={calcular.isPending} onClick={handleCalcular}>
            Calcular orçamento
          </Button>
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
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {result.quote.show_1h && <p className="text-sm text-ink">1h: {brl(result.quote.total_1h)}</p>}
                  {result.quote.show_2h && <p className="text-sm text-ink">2h: {brl(result.quote.total_2h)}</p>}
                  {result.quote.show_3h && <p className="text-sm text-ink">3h: {brl(result.quote.total_3h)}</p>}
                  {result.quote.show_4h && <p className="text-sm text-ink">4h: {brl(result.quote.total_4h)}</p>}
                </div>
                <pre className="whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-xs text-ink">
                  {result.quote.message}
                </pre>
                <Button loading={salvar.isPending} onClick={handleSalvar} disabled={saved}>
                  {saved ? "Orçamento salvo" : "Salvar no histórico"}
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
