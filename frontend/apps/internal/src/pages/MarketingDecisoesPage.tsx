import { useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, Input, PageHeader, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  ALVO_LABELS,
  METRICA_LABELS,
  useCriarEntradaDiario,
  useDecidirProposta,
  useDiario,
  usePropostas,
  type AlvoTipo,
  type DiarioEntrada,
  type DiarioTeste,
  type DiarioVeredito,
  type MetricaDoTeste,
  type NovaEntradaDiario,
  type Proposta,
  type PropostaSituacao,
} from "../lib/marketing";

const TIPO_LABEL: Record<Proposta["tipo"], string> = {
  ativar: "Ativar",
  pausar: "Pausar",
  verba: "Mudar verba",
  publico: "Mudar público",
};

const SITUACAO: Record<PropostaSituacao, { texto: string; tone: "neutral" | "green" | "red" | "gold" | "blue" }> = {
  pendente: { texto: "Aguardando decisão", tone: "gold" },
  aprovada: { texto: "Aprovada — a rotina executa", tone: "blue" },
  recusada: { texto: "Recusada", tone: "neutral" },
  expirada: { texto: "Expirada", tone: "neutral" },
  executada: { texto: "Executada", tone: "green" },
  falhou: { texto: "Não executada", tone: "red" },
};

const VEREDITO: Record<DiarioVeredito, { texto: string; tone: "green" | "red" | "neutral" }> = {
  funcionou: { texto: "Funcionou", tone: "green" },
  nao_funcionou: { texto: "Não funcionou", tone: "red" },
  inconclusivo: { texto: "Inconclusivo", tone: "neutral" },
};

function dataHora(iso: string | null): string {
  if (!iso) return "—";
  // O servidor manda o horário de São Paulo (`comando_ops.iso_sp`); aqui só se mostra a data.
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

const brl = (valor: string | null | undefined) => (valor == null ? "—" : `R$ ${formatBRL(Number(valor))}`);

/** Impacto com sinal: "+R$ 450,00" / "−R$ 300,00" — a pausa tira verba do mês. */
function comSinal(valor: string | null | undefined): string {
  if (valor == null) return "—";
  const n = Number(valor);
  return `${n < 0 ? "−" : n > 0 ? "+" : ""}R$ ${formatBRL(Math.abs(n))}`;
}

/** A proposta no contexto da frente (feature 351): teto, verba do mês e quanto ela muda o mês. */
function ContextoDaProposta({ p }: { p: Proposta }) {
  if (p.frente_nome === undefined && p.impacto_mensal === undefined) return null;
  const impacto = p.impacto_mensal != null ? Number(p.impacto_mensal) : null;
  return (
    <dl className="grid grid-cols-2 gap-x-3 gap-y-1 rounded-md bg-surface-2 px-2.5 py-2 text-xs sm:grid-cols-4">
      <div>
        <dt className="text-muted">Frente</dt>
        <dd className="text-ink">{p.frente_nome ?? "Sem frente"}</dd>
      </div>
      <div>
        <dt className="text-muted">Teto por venda</dt>
        <dd className="tabular-nums text-ink">{brl(p.teto)}</dd>
      </div>
      <div>
        <dt className="text-muted">Verba do mês</dt>
        <dd className="tabular-nums text-ink">{brl(p.verba_mes)}</dd>
      </div>
      <div>
        <dt className="text-muted">Impacto no mês</dt>
        <dd className={`font-semibold tabular-nums ${impacto == null ? "text-muted" : impacto > 0 ? "text-gold" : "text-green"}`}>
          {comSinal(p.impacto_mensal)}
        </dd>
      </div>
    </dl>
  );
}

function CardProposta({ p, podeDecidir }: { p: Proposta; podeDecidir: boolean }) {
  const decidir = useDecidirProposta();
  const [obs, setObs] = useState("");
  const pendente = p.situacao === "pendente";
  const erro =
    decidir.error instanceof ApiRequestError ? decidir.error.message : decidir.error ? "Não foi possível registrar." : null;
  const situacao = SITUACAO[p.situacao];

  return (
    <Card className={`space-y-2 p-4 ${pendente ? "border-gold/50" : ""}`}>
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink">
            {TIPO_LABEL[p.tipo]}: {p.alvo_nome || p.alvo_id}
          </p>
          <p className="text-xs text-muted">
            {p.platform} · {p.alvo_tipo} · proposta em {dataHora(p.criada_em)}
            {p.expira_em ? ` · vale até ${dataHora(p.expira_em)}` : ""}
          </p>
        </div>
        <Badge tone={situacao.tone}>{situacao.texto}</Badge>
      </div>

      {(p.valor_antes || p.valor_depois) && (
        <p className="text-sm text-ink">
          <span className="text-muted">{p.valor_antes || "—"}</span> → <strong>{p.valor_depois || "—"}</strong>
          {p.custo_dia_estimado && <span className="text-muted"> · R$ {formatBRL(Number(p.custo_dia_estimado))}/dia</span>}
        </p>
      )}
      <ContextoDaProposta p={p} />
      <p className="text-sm text-ink">{p.motivo}</p>
      {p.evidencia && <p className="whitespace-pre-line text-xs text-muted">{p.evidencia}</p>}
      {p.post_titulo && <p className="text-xs text-muted">Peça: {p.post_titulo}</p>}

      {!pendente && (p.decidida_por || p.resultado_execucao) && (
        <p className="text-xs text-muted">
          {p.decidida_por ? `Decidida por ${p.decidida_por.name} em ${dataHora(p.decidida_em)}` : ""}
          {p.decisao_obs ? ` — "${p.decisao_obs}"` : ""}
          {p.resultado_execucao ? ` · ${p.resultado_execucao}` : ""}
        </p>
      )}

      {pendente && podeDecidir && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Input
            aria-label="Observação (opcional)"
            placeholder="Observação (opcional)"
            className="h-10 min-w-0 flex-1 basis-full sm:max-w-xs sm:basis-auto"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
          />
          <Button
            type="button"
            variant="outline"
            disabled={decidir.isPending}
            onClick={() => decidir.mutate({ id: p.id, decisao: "recusar", obs })}
          >
            Recusar
          </Button>
          <Button type="button" disabled={decidir.isPending} onClick={() => decidir.mutate({ id: p.id, decisao: "aprovar", obs })}>
            {decidir.isPending ? "Registrando…" : "Aprovar"}
          </Button>
        </div>
      )}
      {pendente && !podeDecidir && <p className="text-xs text-muted">Só o Superadmin aprova ou recusa.</p>}
      {erro && (
        <p className="text-sm text-red" role="alert">
          {erro}
        </p>
      )}
    </Card>
  );
}

function AbaPropostas() {
  const query = usePropostas();
  const reduceMotion = useReducedMotion();
  if (query.isLoading) return <Skeleton className="h-48 w-full" />;
  if (query.isError || !query.data)
    return (
      <p className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível carregar as propostas.
      </p>
    );
  const { items, pode_decidir, impacto_aprovado_mes } = query.data;
  if (!items.length)
    return (
      <Card className="p-5 text-sm text-muted">
        Nenhuma proposta ainda. Toda segunda a rotina lê a Meta e o Google e propõe aqui o que mudar — nada muda sem
        aprovação.
      </Card>
    );
  return (
    <div className="space-y-3">
    {impacto_aprovado_mes !== undefined && (
      <p className="text-sm text-ink">
        Aprovado neste mês: <strong className="tabular-nums">{comSinal(impacto_aprovado_mes)}</strong> de verba por mês
        <span className="text-muted"> (propostas aprovadas e executadas; mês de 30 dias).</span>
      </p>
    )}
    <ul className="space-y-3">
      <AnimatePresence initial={false}>
        {items.map((p) => (
          <motion.li
            key={p.id}
            layout={!reduceMotion}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <CardProposta p={p} podeDecidir={pode_decidir} />
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
    </div>
  );
}

const SELECT = "mt-1 h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

interface TesteRascunho {
  alvo_platform: string;
  alvo_tipo: AlvoTipo;
  alvo_id: string;
  alvo_nome: string;
  metrica: MetricaDoTeste;
  mudou_em: string;
  janela_dias: string;
  controle_id: string;
  controle_nome: string;
}

const TESTE_VAZIO: TesteRascunho = {
  alvo_platform: "Meta Ads",
  alvo_tipo: "anuncio",
  alvo_id: "",
  alvo_nome: "",
  metrica: "conversas",
  mudou_em: "",
  janela_dias: "7",
  controle_id: "",
  controle_nome: "",
};

/** Só vai o teste com o alvo preenchido; o resto é opcional e o servidor completa (dia = hoje, janela = 7). */
function camposDoTeste(t: TesteRascunho): Partial<NovaEntradaDiario> {
  if (!t.alvo_id.trim()) return {};
  return {
    alvo_platform: t.alvo_platform,
    alvo_tipo: t.alvo_tipo,
    alvo_id: t.alvo_id.trim(),
    alvo_nome: t.alvo_nome.trim() || undefined,
    metrica: t.metrica,
    mudou_em: t.mudou_em || undefined,
    janela_dias: t.janela_dias ? Number(t.janela_dias) : undefined,
    controle_tipo: t.controle_id.trim() ? t.alvo_tipo : undefined,
    controle_id: t.controle_id.trim() || undefined,
    controle_nome: t.controle_nome.trim() || undefined,
  };
}

/** O teste estruturado da entrada (feature 351): o que mudou, o que medir e o controle. */
function CamposDoTeste({
  t,
  setT,
  campo,
}: {
  t: TesteRascunho;
  setT: (proximo: TesteRascunho) => void;
  campo: (nome: string) => string | undefined;
}) {
  const erro = (nome: string) => campo(nome) && <span className="text-sm text-red">{campo(nome)}</span>;
  return (
    <details className="rounded-md border border-line px-3 py-2">
      <summary className="cursor-pointer text-sm font-medium text-ink">Medir esta mudança (opcional)</summary>
      <p className="mt-1 text-xs text-muted">
        O sistema calcula a métrica nos dias antes e depois da mudança. O controle é um alvo que ficou igual no mesmo
        período — tira o efeito da época.
      </p>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <label className="block text-sm font-medium text-ink">
          Plataforma
          <select className={SELECT} value={t.alvo_platform} onChange={(e) => setT({ ...t, alvo_platform: e.target.value })}>
            <option value="Meta Ads">Meta Ads</option>
            <option value="Google Ads">Google Ads</option>
          </select>
        </label>
        <label className="block text-sm font-medium text-ink">
          Alvo
          <select className={SELECT} value={t.alvo_tipo} onChange={(e) => setT({ ...t, alvo_tipo: e.target.value as AlvoTipo })}>
            {(Object.keys(ALVO_LABELS) as AlvoTipo[]).map((a) => (
              <option key={a} value={a}>
                {ALVO_LABELS[a]}
              </option>
            ))}
          </select>
          {erro("alvo_tipo")}
        </label>
        <label className="col-span-2 block text-sm font-medium text-ink">
          Id do alvo na plataforma
          <Input className="mt-1 h-10" value={t.alvo_id} onChange={(e) => setT({ ...t, alvo_id: e.target.value })} />
          {erro("alvo_id")}
        </label>
        <label className="col-span-2 block text-sm font-medium text-ink">
          Nome do alvo (opcional)
          <Input className="mt-1 h-10" value={t.alvo_nome} onChange={(e) => setT({ ...t, alvo_nome: e.target.value })} />
        </label>
        <label className="block text-sm font-medium text-ink">
          Métrica
          <select className={SELECT} value={t.metrica} onChange={(e) => setT({ ...t, metrica: e.target.value as MetricaDoTeste })}>
            {(Object.keys(METRICA_LABELS) as MetricaDoTeste[]).map((m) => (
              <option key={m} value={m}>
                {METRICA_LABELS[m]}
              </option>
            ))}
          </select>
          {erro("metrica")}
        </label>
        <label className="block text-sm font-medium text-ink">
          Janela (dias)
          <Input
            type="number"
            inputMode="numeric"
            min={3}
            max={28}
            className="mt-1 h-10"
            value={t.janela_dias}
            onChange={(e) => setT({ ...t, janela_dias: e.target.value })}
          />
          {erro("janela_dias")}
        </label>
        <label className="col-span-2 block text-sm font-medium text-ink">
          Dia da mudança (em branco: hoje)
          <Input type="date" className="mt-1 h-10" value={t.mudou_em} onChange={(e) => setT({ ...t, mudou_em: e.target.value })} />
          {erro("mudou_em")}
        </label>
        <label className="col-span-2 block text-sm font-medium text-ink">
          Id do controle (opcional, mesmo tipo de alvo)
          <Input className="mt-1 h-10" value={t.controle_id} onChange={(e) => setT({ ...t, controle_id: e.target.value })} />
          {erro("controle_tipo")}
        </label>
      </div>
    </details>
  );
}

function NovaEntrada() {
  const criar = useCriarEntradaDiario();
  const [aberto, setAberto] = useState(false);
  const [titulo, setTitulo] = useState("");
  const [motivo, setMotivo] = useState("");
  const [esperado, setEsperado] = useState("");
  const [teste, setTeste] = useState<TesteRascunho>(TESTE_VAZIO);
  const campo = (nome: string) => (criar.error instanceof ApiRequestError ? criar.error.fields?.[nome] : undefined);

  if (!aberto)
    return (
      <Button type="button" variant="outline" size="sm" onClick={() => setAberto(true)}>
        Nova entrada
      </Button>
    );
  return (
    <Card className="space-y-2 p-4">
      <label className="block text-sm font-medium text-ink">
        O que mudou
        <Input className="mt-1 h-10" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Ex.: trocamos a foto do anúncio de festa" />
        {campo("titulo") && <span className="text-sm text-red">{campo("titulo")}</span>}
      </label>
      <label className="block text-sm font-medium text-ink">
        Por quê
        <textarea
          className="mt-1 min-h-20 w-full rounded-md border border-line bg-panel px-2 py-1.5 text-sm text-ink"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        {campo("motivo") && <span className="text-sm text-red">{campo("motivo")}</span>}
      </label>
      <label className="block text-sm font-medium text-ink">
        O que esperamos (opcional)
        <Input className="mt-1 h-10" value={esperado} onChange={(e) => setEsperado(e.target.value)} />
      </label>
      <CamposDoTeste t={teste} setT={setTeste} campo={campo} />
      {criar.isError && !(criar.error instanceof ApiRequestError && criar.error.fields) && (
        <p className="text-sm text-red" role="alert">
          Não foi possível salvar a entrada. Tente novamente.
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => setAberto(false)}>
          Cancelar
        </Button>
        <Button
          type="button"
          disabled={criar.isPending}
          onClick={() =>
            criar.mutate(
              { titulo, motivo, resultado_esperado: esperado || undefined, ...camposDoTeste(teste) },
              {
                onSuccess: () => {
                  setTitulo("");
                  setMotivo("");
                  setEsperado("");
                  setTeste(TESTE_VAZIO);
                  setAberto(false);
                },
              },
            )
          }
        >
          {criar.isPending ? "Salvando…" : "Salvar entrada"}
        </Button>
      </div>
    </Card>
  );
}

function valorDaMetrica(metrica: MetricaDoTeste, valor: string | null): string {
  if (valor == null) return "sem leitura";
  if (metrica === "gasto" || metrica === "custo_conversa") return brl(valor);
  return Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

function pct(v: number | null): string {
  if (v == null) return "sem base";
  return `${v > 0 ? "+" : ""}${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

const dataCurta = (iso: string) => {
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
};

/** O antes e o depois calculados no servidor (feature 351). */
function TesteDaEntrada({ t }: { t: DiarioTeste }) {
  const nome = t.alvo.nome ?? t.alvo.id;
  return (
    <div className="space-y-1 rounded-md bg-surface-2 px-2.5 py-2 text-xs">
      <p className="text-ink">
        <strong>{METRICA_LABELS[t.metrica]}</strong> · {ALVO_LABELS[t.alvo.tipo]} {nome} · mudou em {dataCurta(t.mudou_em)} ·
        janela de {t.janela_dias} dias
      </p>
      <p className="text-ink">
        Antes ({dataCurta(t.antes.de)}–{dataCurta(t.antes.ate)}): {valorDaMetrica(t.metrica, t.antes.valor)} → depois (
        {dataCurta(t.depois.de)}–{dataCurta(t.depois.ate)}): {valorDaMetrica(t.metrica, t.depois.valor)}{" "}
        <strong className="tabular-nums">{pct(t.variacao)}</strong>
        {!t.completo && <span className="text-muted"> · em andamento</span>}
      </p>
      {t.controle && (
        <p className="text-muted">
          Controle ({ALVO_LABELS[t.controle.tipo]} {t.controle.nome ?? t.controle.id}):{" "}
          {valorDaMetrica(t.metrica, t.controle.antes)} → {valorDaMetrica(t.metrica, t.controle.depois)} ({pct(t.controle.variacao)})
          {t.efeito_liquido != null && (
            <>
              {" "}
              · efeito líquido{" "}
              <strong className="text-ink">
                {t.efeito_liquido > 0 ? "+" : ""}
                {t.efeito_liquido.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} pontos
              </strong>
            </>
          )}
        </p>
      )}
      {t.linha_base != null && <p className="text-muted">Linha de base: {valorDaMetrica(t.metrica, t.linha_base)}</p>}
    </div>
  );
}

function CardEntrada({ e }: { e: DiarioEntrada }) {
  return (
    <Card className={`space-y-1.5 p-4 ${e.a_reavaliar ? "border-gold/50" : ""}`}>
      <div className="flex flex-wrap items-start gap-2">
        <p className="min-w-0 flex-1 text-sm font-semibold text-ink">{e.titulo}</p>
        {e.veredito ? (
          <Badge tone={VEREDITO[e.veredito].tone}>{VEREDITO[e.veredito].texto}</Badge>
        ) : e.a_reavaliar ? (
          <Badge tone="gold">A reavaliar</Badge>
        ) : (
          <Badge tone="neutral">Reavaliar em {dataHora(e.reavaliar_em)}</Badge>
        )}
      </div>
      <p className="text-xs text-muted">
        {dataHora(e.criado_em)} · {e.origem === "proposta" ? "proposta executada" : e.origem === "rotina" ? "rotina" : e.autor?.name ?? "equipe"}
      </p>
      <p className="text-sm text-ink">{e.motivo}</p>
      {e.resultado_esperado && <p className="text-xs text-muted">Esperado: {e.resultado_esperado}</p>}
      {e.teste && <TesteDaEntrada t={e.teste} />}
      {e.resultado_observado && (
        <p className="rounded-md bg-surface-2 px-2 py-1.5 text-sm text-ink">Resultado: {e.resultado_observado}</p>
      )}
    </Card>
  );
}

function AbaDiario() {
  const query = useDiario();
  if (query.isLoading) return <Skeleton className="h-48 w-full" />;
  if (query.isError || !query.data)
    return (
      <p className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível carregar o diário.
      </p>
    );
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto text-sm text-muted">
          {query.data.a_reavaliar > 0
            ? `${query.data.a_reavaliar} decisão(ões) passaram da data de reavaliar — a rotina de segunda escreve o resultado.`
            : "Cada mudança fica registrada com o motivo; 14 dias depois a rotina diz se funcionou."}
        </p>
        <NovaEntrada />
      </div>
      {query.data.items.length === 0 ? (
        <Card className="p-5 text-sm text-muted">Nenhuma entrada ainda.</Card>
      ) : (
        <ul className="space-y-3">
          {query.data.items.map((e) => (
            <li key={e.id}>
              <CardEntrada e={e} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Decisões de marketing (feature 345): o que a rotina propõe e o que já foi feito.
 *
 * A aba fica no endereço (`?aba=diario`) — o dono abre o link do e-mail da rotina direto nela. Em
 * 390 px os cards empilham e os botões quebram linha: é pelo celular que o dono aprova.
 */
export function MarketingDecisoesPage() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const aba = params.get("aba") === "diario" ? "diario" : "propostas";
  const propostas = usePropostas();
  const pendentes = propostas.data?.pendentes ?? 0;

  return (
    <div className="w-full px-4 py-6 sm:px-8">
      <PageHeader
        title="Decisões de marketing"
        subtitle="A rotina propõe; o Superadmin aprova; o diário guarda o porquê e o resultado."
      />
      <Tabs
        value={aba}
        onValueChange={(v) =>
          setParams(
            (atual) => {
              const proximo = new URLSearchParams(atual);
              if (v === "diario") proximo.set("aba", "diario");
              else proximo.delete("aba");
              return proximo;
            },
            { replace: true, state: location.state },
          )
        }
      >
        <TabsList>
          <TabsTrigger value="propostas">Propostas{pendentes > 0 ? ` (${pendentes})` : ""}</TabsTrigger>
          <TabsTrigger value="diario">Diário</TabsTrigger>
        </TabsList>
        <TabsContent value="propostas" className="pt-3">
          <AbaPropostas />
        </TabsContent>
        <TabsContent value="diario" className="pt-3">
          <AbaDiario />
        </TabsContent>
      </Tabs>
    </div>
  );
}
