import { Badge } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import { brl, DataRow, Empty, formatDay, Panel } from "./parts";

/** Rótulos legíveis das formas de pagamento gravadas no evento. */
const PAYMENT_METHOD_LABELS: Record<string, string> = {
  avista: "À vista (PIX)",
  pix_parcelado: "Dividido no PIX",
  faturado: "Faturado",
  cartao: "Cartão de crédito",
  futuro: "Pagamento futuro",
  parcelado: "Parcelado (datas)",
};

/** Um card da grade de resultado. `emphasis` destaca o lucro líquido. */
function KpiCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone: "neutral" | "green" | "red";
}) {
  const toneClass =
    tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-ink";
  return (
    <div className="rounded-md border border-line bg-surface-2/60 p-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold tabular-nums ${toneClass}`}>{value}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
    </div>
  );
}

/**
 * Grade financeira de resultado do evento (feature 190): venda, custo de cachês, gastos
 * extras, comissão e o lucro líquido em destaque — verde quando positivo, vermelho quando
 * negativo. Os números vêm prontos do servidor (`kpi`), agregados pelo grupo comercial.
 */
function KpiGrid({ data }: { data: EventoDetalhe }) {
  const kpi = data.kpi;
  if (!kpi) return null;
  const gastos = data.gastos ?? [];
  const lucro = kpi.lucro ?? 0;

  return (
    <Panel
      title={`Resultado${kpi.group_size > 1 ? ` — grupo de ${kpi.group_size} eventos` : ""}`}
    >
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <KpiCard label="Venda" value={brl(kpi.sale_value)} tone="neutral" />
        <KpiCard label="Custo (cachês)" value={brl(kpi.cost)} tone="neutral" />
        <KpiCard
          label="Gastos extras"
          value={brl(kpi.expenses_total)}
          hint={gastos.length ? `${gastos.length} aprovado(s)` : undefined}
          tone="neutral"
        />
        <KpiCard
          label={`Comissão (${kpi.rate}%)`}
          value={brl(kpi.commission)}
          hint={kpi.seller ?? undefined}
          tone="neutral"
        />
        <KpiCard
          label="Lucro líquido"
          value={brl(lucro)}
          hint="venda − cachês − gastos"
          tone={lucro < 0 ? "red" : "green"}
        />
      </div>

      {gastos.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">
            Gastos extras vinculados (aprovados)
          </div>
          <ul className="divide-y divide-line text-sm">
            {gastos.map((gasto) => (
              <li key={gasto.id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="min-w-0 truncate text-ink">
                  {gasto.description}
                  <span className="ml-2 text-xs text-muted">{gasto.category}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="text-xs text-muted tabular-nums">
                    {formatDay(gasto.expense_date)}
                  </span>
                  <span className="tabular-nums text-ink">{brl(gasto.amount)}</span>
                  {gasto.receipt_path && (
                    <a
                      href={assetUrl(gasto.receipt_path)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue underline"
                    >
                      Ver
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

/** Dados da venda: clientes, valores, acréscimos e responsável. */
function VendaPanel({ data }: { data: EventoDetalhe }) {
  const venda = data.venda;
  if (!venda) return null;
  const acrescimos = data.acrescimos ?? [];
  const bruto = venda.sale_value_gross ?? 0;
  const liquido = venda.sale_value ?? 0;
  const desconto = bruto > liquido ? bruto - liquido : 0;

  return (
    <Panel title="Comercial — dados da venda">
      <div className="mb-2">
        <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">
          Clientes
        </div>
        {venda.clients.length === 0 ? (
          <Empty>Nenhum cliente associado.</Empty>
        ) : (
          <ul className="space-y-1">
            {venda.clients.map((client) => (
              <li
                key={client.client_id}
                className="flex items-center justify-between gap-2 rounded-md border border-line bg-surface-2/60 px-2 py-1.5 text-sm"
              >
                <span className="truncate text-ink">{client.name ?? "—"}</span>
                <Badge>{client.relation}</Badge>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="divide-y divide-line">
        {bruto > 0 && <DataRow label="Valor antes do desconto">{brl(bruto)}</DataRow>}
        {desconto > 0 && (
          <DataRow label="Desconto">
            <span className="text-red">− {brl(desconto)}</span>
          </DataRow>
        )}
        <DataRow label="Valor de venda final">
          <span className="font-semibold tabular-nums">{brl(liquido)}</span>
        </DataRow>
        {venda.transport_value ? (
          <DataRow label="Transporte">{brl(venda.transport_value)}</DataRow>
        ) : null}
        {venda.payment_method && (
          <DataRow label="Forma de pagamento">
            {PAYMENT_METHOD_LABELS[venda.payment_method] ?? venda.payment_method}
            {venda.payment_installments ? ` — ${venda.payment_installments}x` : ""}
          </DataRow>
        )}
        {venda.sale_date && <DataRow label="Data da venda">{formatDay(venda.sale_date)}</DataRow>}
        {venda.seller && <DataRow label="Vendedor responsável">{venda.seller}</DataRow>}
        {venda.commission_rate != null && (
          <DataRow label="Taxa de comissão">{venda.commission_rate}%</DataRow>
        )}
        {venda.is_cortesia_permuta && (
          <DataRow label="Cortesia / permuta">
            <Badge tone="gold">Sim</Badge>
          </DataRow>
        )}
        {venda.with_invoice && (
          <DataRow label="Nota fiscal">
            <Badge tone="blue">Solicitada</Badge>
          </DataRow>
        )}
      </div>

      <div className="mt-3">
        <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">
          Acréscimos
        </div>
        {acrescimos.length === 0 ? (
          <Empty>Nenhum acréscimo.</Empty>
        ) : (
          <ul className="divide-y divide-line text-sm">
            {acrescimos.map((acrescimo) => (
              <li key={acrescimo.id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="truncate text-ink">
                  {acrescimo.label}
                  {acrescimo.is_bv && (
                    <Badge tone="gold" className="ml-2">
                      BV — repasse
                    </Badge>
                  )}
                  {acrescimo.is_bv && acrescimo.bv_recipient && (
                    <span className="ml-2 text-xs text-muted">{acrescimo.bv_recipient}</span>
                  )}
                </span>
                <span className="shrink-0 tabular-nums text-ink">{brl(acrescimo.amount_brl)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}

export interface ComercialSectionProps {
  data: EventoDetalhe;
}

/** Bloco comercial + grade de resultado (coluna direita, feature 190). */
export function ComercialSection({ data }: ComercialSectionProps) {
  return (
    <>
      <VendaPanel data={data} />
      <KpiGrid data={data} />
    </>
  );
}
