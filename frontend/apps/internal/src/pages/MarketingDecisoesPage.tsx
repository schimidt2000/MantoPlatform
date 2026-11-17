import { useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, Input, PageHeader, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  useCriarEntradaDiario,
  useDecidirProposta,
  useDiario,
  usePropostas,
  type DiarioEntrada,
  type DiarioVeredito,
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
  // Os carimbos chegam em UTC naive; aqui só se mostra a data, então o dia basta.
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
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
            className="h-10 min-w-0 flex-1 sm:max-w-xs"
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
  const { items, pode_decidir } = query.data;
  if (!items.length)
    return (
      <Card className="p-5 text-sm text-muted">
        Nenhuma proposta ainda. Toda segunda a rotina lê a Meta e o Google e propõe aqui o que mudar — nada muda sem
        aprovação.
      </Card>
    );
  return (
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
  );
}

function NovaEntrada() {
  const criar = useCriarEntradaDiario();
  const [aberto, setAberto] = useState(false);
  const [titulo, setTitulo] = useState("");
  const [motivo, setMotivo] = useState("");
  const [esperado, setEsperado] = useState("");
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
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => setAberto(false)}>
          Cancelar
        </Button>
        <Button
          type="button"
          disabled={criar.isPending}
          onClick={() =>
            criar.mutate(
              { titulo, motivo, resultado_esperado: esperado || undefined },
              {
                onSuccess: () => {
                  setTitulo("");
                  setMotivo("");
                  setEsperado("");
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
