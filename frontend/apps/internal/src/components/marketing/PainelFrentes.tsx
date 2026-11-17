import { useState } from "react";
import { Settings2 } from "lucide-react";
import { Badge, Button, Card } from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useCorrigirFrente,
  type CampanhaSemFrente,
  type DesempenhoFrente,
  type DesempenhoResponse,
  type FrenteEstado,
  type PlataformaSituacao,
} from "../../lib/marketing";
import { FrentesConfigDialog } from "./FrentesConfigDialog";

const brl = (valor: string | number | null | undefined) =>
  valor == null ? "—" : `R$ ${formatBRL(Number(valor))}`;

const ESTADO: Record<FrenteEstado, { texto: string; tone: "green" | "red" | "gold" | "neutral" }> = {
  ok: { texto: "Dentro do teto", tone: "green" },
  acima_do_teto: { texto: "Acima do teto", tone: "red" },
  sem_venda: { texto: "Gasto sem venda", tone: "gold" },
  sem_gasto: { texto: "Sem anúncio", tone: "neutral" },
};

const SITUACAO: Record<PlataformaSituacao["situacao"], { texto: string; tone: "green" | "gold" | "neutral" }> = {
  ok: { texto: "em dia", tone: "green" },
  atrasada: { texto: "leitura atrasada", tone: "gold" },
  sem_conexao: { texto: "sem conexão", tone: "neutral" },
};

function CardFrente({ f }: { f: DesempenhoFrente }) {
  const estado = ESTADO[f.estado];
  return (
    <Card className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{f.nome}</p>
        <Badge tone={estado.tone}>{estado.texto}</Badge>
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Custo por venda</p>
        <p className="text-2xl font-semibold leading-tight tabular-nums text-ink">
          {f.custo_venda ? brl(f.custo_venda) : f.estado === "sem_venda" ? "sem venda" : "—"}
        </p>
        <p className="text-[11px] text-muted">teto {f.teto ? brl(f.teto) : "não definido"}</p>
      </div>
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
          Não foi possível salvar a frente. Tente de novo.
        </p>
      )}
    </Card>
  );
}

/**
 * Bloco "Por frente" do Desempenho (feature 345): custo por venda de cada frente contra o teto.
 *
 * O custo é **misto** — gasto da frente ÷ todas as vendas da frente no período — porque ainda não
 * existe atribuição venda → anúncio (chega com o CRM próprio). O texto diz isso com todas as letras.
 */
export function PainelFrentes({ data }: { data: DesempenhoResponse }) {
  const [configAberto, setConfigAberto] = useState(false);
  const frentes = data.frentes ?? [];
  if (!frentes.length) return null;
  return (
    <section className="mb-4 space-y-3" aria-labelledby="titulo-por-frente">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="titulo-por-frente" className="text-base font-semibold text-ink">
            Por frente
          </h2>
          <p className="text-xs text-muted">
            Custo por venda misto: gasto em anúncio da frente ÷ todas as vendas fechadas da frente no período.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(data.plataformas ?? []).map((p) => (
            <Badge key={p.platform} tone={SITUACAO[p.situacao].tone}>
              {p.platform}: {SITUACAO[p.situacao].texto}
            </Badge>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={() => setConfigAberto(true)}>
            <Settings2 className="mr-1 h-4 w-4" aria-hidden />
            Tetos e responsáveis
          </Button>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {frentes.map((f) => (
          <CardFrente key={f.slug} f={f} />
        ))}
      </div>
      <SemFrente campanhas={data.sem_frente ?? []} opcoes={data.frente_opcoes ?? []} />
      <FrentesConfigDialog open={configAberto} onClose={() => setConfigAberto(false)} />
    </section>
  );
}
