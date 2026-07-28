import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useDashboardComercial,
  type ContractStatus,
  type SalePaymentStatus,
  type VendaFechada,
} from "../lib/vendas";
import type { PeriodFilter } from "../lib/financeiro";

/** Períodos oferecidos no Dashboard Comercial — subconjunto do que `_resolve_period` aceita. */
const PERIOD_OPTIONS: { value: PeriodFilter; label: string }[] = [
  { value: "este_mes", label: "Mês atual" },
  { value: "mes_anterior", label: "Mês anterior" },
  { value: "30d", label: "Últimos 30 dias" },
];

const CONTRACT_TONE: Record<ContractStatus, "green" | "gold" | "neutral"> = {
  assinado: "green",
  pendente: "gold",
  sem_contrato: "neutral",
};

const PAYMENT_TONE: Record<SalePaymentStatus, "green" | "gold" | "red" | "accent" | "neutral"> = {
  pago_total: "green",
  parcial: "gold",
  pendente: "red",
  permuta: "accent",
  sem_valor: "neutral",
};

/** Formata em BRL sempre com prefixo (Princípio VII) — 0 vira "R$ 0,00", nunca travessão. */
function brl(value: number | null | undefined): string {
  return `R$ ${formatBRL(value ?? 0)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
}

interface KpiCardProps {
  label: string;
  value: string;
  sub: string;
  /** Destaque do card — `green` é usado na comissão, para incentivar o comercial. */
  highlight?: boolean;
}

function KpiCard({ label, value, sub, highlight = false }: KpiCardProps) {
  return (
    <Card className={highlight ? "border-green/40 bg-green-soft/40 p-4" : "p-4"}>
      <p className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p
        className={`mt-1 text-2xl font-extrabold tabular-nums ${
          highlight ? "text-green" : "text-ink"
        }`}
      >
        {value}
      </p>
      <p className="mt-0.5 text-[11px] text-muted">{sub}</p>
    </Card>
  );
}

function KpiGrid({
  kpis,
  periodLabel,
  comissaoSub,
}: {
  kpis: {
    total_vendido: number;
    ticket_medio: number;
    eventos_fechados: number;
    comissao_prevista: number;
    desconto_concedido: number;
  };
  periodLabel: string;
  comissaoSub: string;
}) {
  const descontoSub =
    kpis.desconto_concedido > 0
      ? `${brl(kpis.desconto_concedido)} de desconto concedido`
      : "Sem desconto sobre o preço de tabela";
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Total vendido" value={brl(kpis.total_vendido)} sub={descontoSub} />
      <KpiCard
        label="Ticket médio"
        value={brl(kpis.ticket_medio)}
        sub={`Média por evento fechado — ${periodLabel.toLowerCase()}`}
      />
      <KpiCard
        label="Eventos fechados"
        value={String(kpis.eventos_fechados)}
        sub="Vendas com valor, sem permutas"
      />
      <KpiCard
        label="Comissão prevista"
        value={brl(kpis.comissao_prevista)}
        sub={comissaoSub}
        highlight
      />
    </div>
  );
}

function SaleRow({ venda, showSeller }: { venda: VendaFechada; showSeller: boolean }) {
  const desconto =
    venda.sale_value_gross !== null && venda.sale_value_gross > venda.sale_value
      ? venda.sale_value_gross
      : null;
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-muted">
        {formatDate(venda.event_date)}
      </TableCell>
      <TableCell className="text-ink">{venda.client_name ?? "Sem cliente vinculado"}</TableCell>
      <TableCell className="text-ink">
        {venda.group_label ?? venda.title}
        {venda.group_label && (
          <Badge tone="blue" className="ml-1">
            GRUPO
          </Badge>
        )}
        {venda.is_permuta && (
          <Badge tone="accent" className="ml-1">
            PERMUTA
          </Badge>
        )}
        <span className="block text-[11px] text-muted">
          Venda fechada em {formatDate(venda.closing_date)}
        </span>
      </TableCell>
      <TableCell align="right" className="whitespace-nowrap font-semibold text-ink">
        {brl(venda.sale_value)}
        {desconto && (
          <span className="block text-[11px] font-normal text-muted line-through">
            {brl(desconto)}
          </span>
        )}
      </TableCell>
      {showSeller && (
        <TableCell className="text-ink">{venda.seller_name ?? "Sem vendedor"}</TableCell>
      )}
      <TableCell className="whitespace-nowrap">
        <Badge tone={CONTRACT_TONE[venda.contract_status]}>
          {venda.contract_status_label.toUpperCase()}
        </Badge>
      </TableCell>
      <TableCell className="whitespace-nowrap">
        <Badge tone={PAYMENT_TONE[venda.payment_status]}>
          {venda.payment_status_label.toUpperCase()}
        </Badge>
      </TableCell>
      <TableCell align="right">
        <Button asChild variant="outline" size="sm">
          <Link to={`/events/${venda.event_id}`}>Ver evento</Link>
        </Button>
      </TableCell>
    </TableRow>
  );
}

function FunilTable({ eventos, showSeller }: { eventos: VendaFechada[]; showSeller: boolean }) {
  if (eventos.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-muted">
        Nenhuma venda fechada neste período. Troque o filtro acima para ver outro mês.
      </p>
    );
  }
  return (
    <Table className="min-w-[920px]">
      <thead>
        <TableRow head>
          <TableCell as="th">Data do evento</TableCell>
          <TableCell as="th">Cliente</TableCell>
          <TableCell as="th">Evento</TableCell>
          <TableCell as="th" align="right">
            Valor da venda
          </TableCell>
          {showSeller && <TableCell as="th">Vendedor</TableCell>}
          <TableCell as="th">Contrato</TableCell>
          <TableCell as="th">Cobrança</TableCell>
          <TableCell as="th" align="right">
            Ações
          </TableCell>
        </TableRow>
      </thead>
      <tbody>
        {eventos.map((venda) => (
          <SaleRow key={venda.event_id} venda={venda} showSeller={showSeller} />
        ))}
      </tbody>
    </Table>
  );
}

/**
 * Dashboard Comercial (`/vendas`, feature 196).
 *
 * Substitui o antigo "Pipeline de Vendas", que era uma cópia empobrecida da tabela do Painel
 * Financeiro. Aqui o foco é meta e performance: KPIs do período no topo e o funil já fechado
 * embaixo. Custo e lucro líquido ficaram de fora de propósito — são do setor financeiro, e o
 * papel `COMERCIAL` não acessa aquele painel.
 */
export function VendasPipelinePage() {
  const [period, setPeriod] = useState<PeriodFilter>("este_mes");
  const [sellerId, setSellerId] = useState<number | null>(null);
  const reduceMotion = useReducedMotion();
  const query = useDashboardComercial({ period, sellerId });

  const data = query.data;
  const isGestor = data?.can_filter_seller ?? false;
  const comissaoSub =
    data && data.scope_label === "Empresa toda"
      ? "Comissões projetadas da equipe"
      : "Projeção sobre as suas vendas do período";

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 sm:p-6">
      <PageHeader title="Dashboard Comercial" className="mb-0" />
      <p className="text-sm text-muted">
        Metas, performance e acompanhamento das vendas fechadas
        {data ? ` — ${data.scope_label.toLowerCase()}` : ""}.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-panel p-1">
          {PERIOD_OPTIONS.map((option) => (
            <Button
              key={option.value}
              size="sm"
              variant={period === option.value ? "default" : "ghost"}
              onClick={() => setPeriod(option.value)}
              aria-pressed={period === option.value}
            >
              {option.label}
            </Button>
          ))}
        </div>
        {isGestor && (
          <select
            value={sellerId ?? ""}
            onChange={(event) => setSellerId(event.target.value ? Number(event.target.value) : null)}
            className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            aria-label="Filtrar por vendedor"
          >
            <option value="">Todos os vendedores</option>
            {data?.sellers?.map((seller) => (
              <option key={seller.id} value={seller.id}>
                {seller.name}
              </option>
            ))}
          </select>
        )}
        {data && (
          <span className="text-xs text-muted">
            {formatDate(data.start)} a {formatDate(data.end)}
          </span>
        )}
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-72 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o dashboard comercial. Tente novamente em instantes.
        </div>
      )}

      {data && (
        <motion.div
          key={`${data.period}-${data.seller_id ?? "todos"}`}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          <KpiGrid kpis={data.kpis} periodLabel={data.period_label} comissaoSub={comissaoSub} />

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-2">
              <CardTitle>Acompanhamento de vendas — {data.period_label}</CardTitle>
              <span className="shrink-0 text-xs text-muted">
                {data.eventos.length} evento(s) no período
              </span>
            </CardHeader>
            <CardContent className="p-0">
              <FunilTable eventos={data.eventos} showSeller={isGestor} />
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
