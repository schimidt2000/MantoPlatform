import { useState } from "react";
import { CalendarDays, Settings2 } from "lucide-react";
import { Badge, Button, Card, InfoTip } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  NOMES_DOS_MESES,
  useCorrigirFrente,
  type CampanhaSemFrente,
  type DesempenhoAtribuicao,
  type DesempenhoFrente,
  type DesempenhoResponse,
  type FrenteEstado,
  type FrenteMesCorrente,
  type PlataformaSituacao,
} from "../../lib/marketing";
import { CalendarioDialog } from "./CalendarioDialog";
import { FrentesConfigDialog } from "./FrentesConfigDialog";

const brl = (valor: string | number | null | undefined) =>
  valor == null ? "—" : `R$\u00a0${formatBRL(Number(valor))}`;

const ESTADO: Record<FrenteEstado, { texto: string; tone: "green" | "red" | "gold" | "neutral" }> = {
  ok: { texto: "Dentro do teto", tone: "green" },
  acima_do_teto: { texto: "Acima do teto", tone: "red" },
  sem_venda: { texto: "Gasto sem venda", tone: "gold" },
  sem_gasto: { texto: "Sem anúncio", tone: "neutral" },
};

// O estado atribuído (351) compara o custo COM desconto ao teto — é a régua da casa.
const ESTADO_ATRIBUIDO: Record<FrenteEstado, { texto: string; tone: "green" | "red" | "gold" | "neutral" }> = {
  ...ESTADO,
  sem_venda: { texto: "Sem venda atribuída", tone: "gold" },
};

const SITUACAO: Record<PlataformaSituacao["situacao"], { texto: string; tone: "green" | "gold" | "neutral" }> = {
  ok: { texto: "em dia", tone: "green" },
  atrasada: { texto: "leitura atrasada", tone: "gold" },
  sem_conexao: { texto: "sem conexão", tone: "neutral" },
};

const dataCurta = (iso: string) => {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
};

const vendas = (n: number) => `${n.toLocaleString("pt-BR")} ${n === 1 ? "venda" : "vendas"}`;

function MesCorrente({ m }: { m: FrenteMesCorrente }) {
  return (
    <div className="rounded-md bg-surface-2 px-2.5 py-2 text-xs">
      <p className="font-semibold text-ink">{NOMES_DOS_MESES[m.mes - 1]}</p>
      <p className="text-ink">
        {m.meta_vendas != null
          ? `${m.vendas.toLocaleString("pt-BR")} de ${m.meta_vendas} ${m.meta_vendas === 1 ? "venda" : "vendas"} da meta`
          : `${vendas(m.vendas)} · sem meta`}
      </p>
      <p className="text-ink">{m.verba ? `${brl(m.gasto)} de ${brl(m.verba)} em anúncio` : `${brl(m.gasto)} em anúncio · sem verba`}</p>
      {m.foco && <p className="mt-0.5 text-muted">{m.foco}</p>}
    </div>
  );
}

/** A frente antes da 351 (bundle novo com backend velho): só o custo misto. */
function CustoMisto({ f }: { f: DesempenhoFrente }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Custo por venda</p>
      <p className="text-2xl font-semibold leading-tight tabular-nums text-ink">
        {f.custo_venda ? brl(f.custo_venda) : f.estado === "sem_venda" ? "sem venda" : "—"}
      </p>
      <p className="text-[11px] text-muted">teto {f.teto ? brl(f.teto) : "não definido"}</p>
    </div>
  );
}

function CustoAtribuido({ f }: { f: DesempenhoFrente }) {
  const atribuidas = f.vendas_atribuidas ?? 0;
  return (
    <div className="space-y-1.5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Custo por venda atribuída, com desconto</p>
        <p className="text-2xl font-semibold leading-tight tabular-nums text-ink">
          {f.custo_venda_atribuida_desconto ? brl(f.custo_venda_atribuida_desconto) : atribuidas === 0 ? "sem venda" : "—"}
        </p>
        <p className="text-[11px] text-muted">teto {f.teto ? brl(f.teto) : "não definido"}</p>
      </div>
      <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-xs">
        <dt className="text-muted">Atribuído ({vendas(atribuidas)})</dt>
        <dd className="text-right tabular-nums text-ink">{brl(f.custo_venda_atribuida)}</dd>
        <dt className="text-muted">Misto ({vendas(f.vendas)})</dt>
        <dd className="text-right tabular-nums text-ink">{brl(f.custo_venda)}</dd>
      </dl>
    </div>
  );
}

function CardFrente({ f }: { f: DesempenhoFrente }) {
  const temAtribuicao = f.vendas_atribuidas !== undefined;
  const estado = temAtribuicao && f.estado_atribuido ? ESTADO_ATRIBUIDO[f.estado_atribuido] : ESTADO[f.estado];
  return (
    <Card className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{f.nome}</p>
        <Badge tone={estado.tone}>{estado.texto}</Badge>
      </div>
      {temAtribuicao ? <CustoAtribuido f={f} /> : <CustoMisto f={f} />}
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <dt className="text-muted">Gasto</dt>
        <dd className="text-right tabular-nums text-ink">{brl(f.gasto)}</dd>
        <dt className="text-muted">Conversas</dt>
        <dd className="text-right tabular-nums text-ink">{f.conversas.toLocaleString("pt-BR")}</dd>
        <dt className="text-muted">Vendas</dt>
        <dd className="text-right tabular-nums text-ink">
          {f.vendas} <span className="text-muted">({f.vendas_cliente_novo} cliente novo)</span>
        </dd>
        <dt className="text-muted">Faturamento</dt>
        <dd className="text-right tabular-nums text-ink">{brl(f.faturamento)}</dd>
      </dl>
      {f.mes_corrente && <MesCorrente m={f.mes_corrente} />}
    </Card>
  );
}

function SemFrente({ campanhas, opcoes }: { campanhas: CampanhaSemFrente[]; opcoes: { slug: string; nome: string }[] }) {
  const corrigir = useCorrigirFrente();
  if (!campanhas.length) return null;
  return (
    <Card className="px-4 py-3">
      <p className="text-sm font-semibold text-ink">Campanhas sem frente</p>
      <p className="text-[11px] text-muted">
        O nome não começa com CORP, SOCIAL, EDU, FESTA ou LOJA. Escolha a frente; vale para as próximas leituras.
      </p>
      <ul className="mt-2 divide-y divide-line">
        {campanhas.map((c) => (
          <li key={`${c.platform}-${c.campaign_id}`} className="flex flex-wrap items-center gap-2 py-2 text-sm">
            <span className="min-w-0 flex-1 truncate text-ink" title={c.campaign_name}>
              {c.campaign_name}
            </span>
            <span className="text-xs text-muted">{c.platform}</span>
            <span className="tabular-nums text-ink">{brl(c.gasto)}</span>
            {/* 5 frentes: `<select>` nativo (Princípio XII, abaixo de 10 itens). */}
            <select
              aria-label={`Frente de ${c.campaign_name}`}
              className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
              defaultValue=""
              disabled={corrigir.isPending}
              onChange={(e) =>
                e.target.value &&
                corrigir.mutate({ platform: c.platform, campaign_id: c.campaign_id, frente: e.target.value })
              }
            >
              <option value="" disabled>
                Escolher frente…
              </option>
              {opcoes.map((o) => (
                <option key={o.slug} value={o.slug}>
                  {o.nome}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
      {corrigir.isError && (
        <p className="mt-2 text-sm text-red" role="alert">
          Não foi possível salvar a frente. Tente novamente.
        </p>
      )}
    </Card>
  );
}

/** A regra da atribuição e a premissa do desconto, escritas na tela (FR-007), e os avisos do período. */
function RegraDaAtribuicao({ a }: { a: DesempenhoAtribuicao }) {
  // `incrementalidade` é a fração que o anúncio causou; o desconto é o resto (0,50 → 50%).
  const desconto = `${100 - Math.round(Number(a.incrementalidade) * 100)}%`;
  return (
    <div className="space-y-1 text-xs text-muted">
      <p>
        <strong className="text-ink">Atribuído</strong>: gasto da frente ÷ vendas que um anúncio da frente trouxe — o
        último contato pago até {a.janela_dias} dias antes da venda, com o evento criado depois do contato.{" "}
        <strong className="text-ink">Com desconto de {desconto}</strong>: {desconto} dessas vendas teriam acontecido sem
        o anúncio. É premissa até existir teste; é esse número que vai contra o teto.{" "}
        <strong className="text-ink">Misto</strong>: gasto ÷ todas as vendas da frente.
        <InfoTip
          className="ml-1 align-middle"
          label="Atribuição"
          content="O contato pago vem da conversa do anúncio (CRM), do anúncio gravado na ficha ou da origem paga da ficha (utm da Meta ou do Google; aí vale a data de entrada na base). Quando houver mais de um contato, vale o mais recente."
        />
      </p>
      {a.parcial && (
        <p className="text-gold">
          Antes de {dataCurta(a.desde)} o evento quase nunca tem ficha de cliente: as vendas dessa parte do período
          ficam fora da atribuição.
        </p>
      )}
      {a.sem_frente.vendas > 0 && (
        <p className="text-ink">
          {vendas(a.sem_frente.vendas)} ({brl(a.sem_frente.faturamento)}) {a.sem_frente.vendas === 1 ? "veio" : "vieram"} de
          campanha sem frente — escolha a frente da campanha para ela contar.
        </p>
      )}
    </div>
  );
}

/**
 * Bloco "Por frente" do Desempenho (features 345 e 351): custo por venda de cada frente contra o teto.
 *
 * O misto (gasto ÷ todas as vendas) continua; a 351 põe ao lado o atribuído (só as vendas que um anúncio
 * da frente trouxe) e o mesmo com o desconto de incrementalidade, que é o que vai contra o teto. A regra e
 * a premissa ficam escritas na tela — o número sem a régua engana.
 */
export function PainelFrentes({ data }: { data: DesempenhoResponse }) {
  const [configAberto, setConfigAberto] = useState(false);
  const [calendarioAberto, setCalendarioAberto] = useState(false);
  const frentes = data.frentes ?? [];
  if (!frentes.length) return null;
  return (
    <section className="mb-4 space-y-3" aria-labelledby="titulo-por-frente">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="titulo-por-frente" className="text-base font-semibold text-ink">
          Por frente
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {(data.plataformas ?? []).map((p) => (
            <Badge key={p.platform} tone={SITUACAO[p.situacao].tone}>
              {p.platform}: {SITUACAO[p.situacao].texto}
            </Badge>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={() => setCalendarioAberto(true)}>
            <CalendarDays className="mr-1 h-4 w-4" aria-hidden />
            Calendário do ano
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => setConfigAberto(true)}>
            <Settings2 className="mr-1 h-4 w-4" aria-hidden />
            Metas, verba e tetos
          </Button>
        </div>
      </div>
      {data.atribuicao ? (
        <RegraDaAtribuicao a={data.atribuicao} />
      ) : (
        <p className="text-xs text-muted">
          Custo por venda misto: gasto em anúncio da frente ÷ todas as vendas fechadas da frente no período.
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {frentes.map((f) => (
          <CardFrente key={f.slug} f={f} />
        ))}
      </div>
      <SemFrente campanhas={data.sem_frente ?? []} opcoes={data.frente_opcoes ?? []} />
      <FrentesConfigDialog open={configAberto} onClose={() => setConfigAberto(false)} />
      <CalendarioDialog open={calendarioAberto} onClose={() => setCalendarioAberto(false)} />
    </section>
  );
}
