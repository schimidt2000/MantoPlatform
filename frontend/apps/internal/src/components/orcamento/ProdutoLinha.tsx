import type { ReactNode } from "react";
import { Badge } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { ProdutoAplicado } from "../../lib/orcamento";

/**
 * Feature 309 — a linha de um produto de tabela aplicado ao orçamento, fonte única entre o card da
 * calculadora, o painel de resultado e a tela do orçamento gerado: "📦 Visita Mágica — Papai Noel
 * (visita padrão, até 1h) — preço de tabela R$ 2.500,00" e, quando a faixa não tem preço, a marca
 * "estimativa" em dourado — a vendedora confere antes de mandar. `acao` é o botão à direita
 * (Remover, no card); `compacta` tira o fundo para a linha viver dentro de um card de resultado.
 */
export function ProdutoLinha({
  produto,
  acao,
  compacta = false,
}: {
  produto: ProdutoAplicado;
  acao?: ReactNode;
  compacta?: boolean;
}) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-2 text-sm${
        compacta ? "" : " rounded-md border border-line bg-surface-2 px-3 py-2"
      }`}
    >
      <div className="min-w-0">
        <p className="text-ink">
          📦 <span className="font-medium">{produto.rotulo}</span>
          {produto.descricao && <span className="text-muted"> ({produto.descricao})</span>}
          <span className="text-muted"> — {produto.estimado ? "preço estimado" : "preço de tabela"} </span>
          <span className="font-semibold tabular-nums">R$ {formatBRL(produto.preco_aplicado)}</span>
          {produto.estimado && (
            <Badge tone="gold" className="ml-2">
              estimativa
            </Badge>
          )}
        </p>
        {produto.vagas.length > 0 && (
          <p className="text-xs text-muted">Inclui: {produto.vagas.join(" · ")}</p>
        )}
      </div>
      {acao}
    </div>
  );
}
