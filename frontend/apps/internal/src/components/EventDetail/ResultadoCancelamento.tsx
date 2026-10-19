import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@manto/ui";
import type { EstadoPagamento, EventoDetalhe, ResumoCancelado } from "../../lib/agenda";
import { AlterarDevolucaoDialog } from "./AlterarDevolucaoDialog";
import { brl, Panel } from "./parts";

const ESTADO: Record<EstadoPagamento, string> = {
  nao_pago: "a pagar",
  no_banco: "no banco",
  pago: "paga",
};

/** `AAAA-MM-DD…` → `DD/MM/AAAA` pela string: a data pura com `new Date` mostraria o dia anterior. */
function dia(iso: string | null): string {
  if (!iso) return "";
  const [ano, mes, d] = iso.slice(0, 10).split("-");
  return d ? `${d}/${mes}/${ano}` : "";
}

function Card({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-line bg-surface-2/60 p-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-0.5 text-lg font-semibold tabular-nums text-ink">{value}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
    </div>
  );
}

/** O link de Comissões aponta o ciclo e o beneficiário do ajuste mais recente (FR-022). */
function linkDeComissoes(eventId: number, resumo: ResumoCancelado): string | undefined {
  const linhas = resumo.comissao?.linhas ?? [];
  const alvo = [...linhas].reverse().find((l) => l.status !== "cancelado" && l.ciclo) ?? null;
  if (!alvo?.ciclo) return undefined;
  return `/financeiro/comissoes?mes=${alvo.ciclo}&vendedor=${alvo.seller_id}&evento=${eventId}`;
}

/**
 * "Resultado do cancelamento" (feature 306, FR-022): no lugar do `KpiGrid` no evento cancelado.
 * Pago, devolvido com o estado, retido, comissão do retido, BV e imposto — os três últimos só com
 * `show_financeiro` (o servidor nem os manda sem a flag). "Alterar devolução" pela flag.
 */
export function ResultadoCancelamento({ data }: { data: EventoDetalhe }) {
  const resumo = data.event.cancelamento;
  const [alterando, setAlterando] = useState(false);
  if (!resumo) return null;
  // Feature 306, H5: o dia cortado (`dia`) também corrige a devolução dele (piso e teto do corte).
  const podeAlterar =
    Boolean(data.flags.can_edit_venda_cancelado) &&
    (resumo.regime === "venda" || resumo.regime === "legado" || resumo.regime === "dia");
  const bv = (resumo.bvs ?? []).reduce((soma, b) => soma + (b.conta ?? 0), 0);
  const linkComissoes = resumo.comissao ? linkDeComissoes(data.event.id, resumo) : undefined;

  return (
    <Panel title="Resultado do cancelamento">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <Card label="Pago pela cliente" value={brl(resumo.pago)} />
        <Card
          label="Devolvido"
          value={brl(resumo.devolvido)}
          hint={
            resumo.devolucoes.length > 0
              ? resumo.devolucoes.map((d) => `${brl(d.valor)} ${ESTADO[d.estado] ?? d.estado}`).join(" · ")
              : "nada a devolver"
          }
        />
        <Card label="Retido pela Manto" value={brl(resumo.retido)} />
        {resumo.comissao && (
          <div className="rounded-md border border-line bg-surface-2/60 p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted">Comissão do retido</div>
            <div className="mt-0.5 text-lg font-semibold tabular-nums text-ink">{brl(resumo.comissao.retido)}</div>
            <div className="text-[11px] text-muted">
              {resumo.comissao.beneficiario?.nome ?? "sem comissionado"} · cheia {brl(resumo.comissao.cheia)}
            </div>
            {linkComissoes && (
              <Link to={linkComissoes} className="mt-1 inline-block text-[11px] text-blue underline">
                ver em comissões
              </Link>
            )}
          </div>
        )}
        {resumo.bvs && resumo.bvs.length > 0 && <Card label="BV que conta" value={brl(bv)} />}
        {resumo.imposto != null && <Card label="Imposto retido" value={brl(resumo.imposto)} />}
      </div>

      {resumo.devolucoes.length > 0 && (
        <ul className="mt-3 divide-y divide-line text-sm">
          {resumo.devolucoes.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
              <span className="min-w-0 text-ink">
                Devolução a {d.nome ?? "—"}
                {d.pix && <span className="ml-2 text-xs text-muted">PIX {d.pix}</span>}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-muted tabular-nums">{dia(d.data)}</span>
                <span className="tabular-nums text-ink">{brl(d.valor)}</span>
                <span className="text-xs text-muted">{ESTADO[d.estado] ?? d.estado}</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {resumo.venda_passou_para && (
        <p className="mt-3 text-sm text-ink">
          A venda passou para{" "}
          <Link to={`/events/${resumo.venda_passou_para.id}`} className="text-blue underline">
            {resumo.venda_passou_para.titulo}
            {resumo.venda_passou_para.data ? ` (${dia(resumo.venda_passou_para.data)})` : ""}
          </Link>
          .
        </p>
      )}

      {podeAlterar && (
        <div className="mt-3">
          <Button variant="outline" size="sm" onClick={() => setAlterando(true)}>
            Alterar devolução
          </Button>
          <AlterarDevolucaoDialog
            eventId={data.event.id}
            resumo={resumo}
            open={alterando}
            onOpenChange={setAlterando}
          />
        </div>
      )}
    </Panel>
  );
}
