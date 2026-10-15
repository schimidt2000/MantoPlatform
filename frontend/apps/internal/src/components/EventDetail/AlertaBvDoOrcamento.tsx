import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { Button } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { BvDoOrcamentoPendente } from "../../lib/agenda";

/**
 * Alerta "o orçamento tem BV e a venda foi digitada sem ele" (feature 305, B9 / 3a-Q2 = A).
 *
 * O dono: "alerta sobre isso e pede para que seja preenchido com atenção o BV e o valor total com
 * BV". O BV não entra sozinho quando a venda é digitada à mão; o "Lançar o BV" abre o editor de
 * Acréscimos com uma linha já preenchida — em reais, com o valor que a criação gravaria (o do
 * orçamento, na proporção da venda) — e nada é gravado sem o clique em Salvar. O valor vem do
 * servidor: nenhuma conta de dinheiro aqui.
 *
 * Aparece em três lugares (topo do painel Acréscimos, sob o valor de venda e na edição completa);
 * some sozinho quando o servidor deixa de mandar `bv_do_orcamento_pendente` (o BV foi lançado).
 */
export function AlertaBvDoOrcamento({
  pendente,
  onLancar,
  lancarHref,
}: {
  pendente: BvDoOrcamentoPendente | null | undefined;
  /** Dentro da aba Comercial: abre o editor direto. */
  onLancar?: () => void;
  /** Fora dela (edição completa): leva à aba Comercial com o editor aberto. */
  lancarHref?: string;
}) {
  if (!pendente) return null;
  const quanto =
    pendente.valor != null
      ? `R$ ${formatBRL(pendente.valor)}${pendente.percentual != null ? ` · ${pendente.percentual}% no orçamento` : ""}`
      : pendente.percentual != null
        ? `${pendente.percentual}% no orçamento — confira a duração para saber o valor`
        : "confira o valor no orçamento";
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded-md border border-gold/40 bg-gold-soft p-3 text-sm text-ink sm:flex-row sm:items-start"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-gold" aria-hidden="true" />
      <div className="flex-1 space-y-2">
        <p>
          <strong>Este evento tem BV no orçamento ({quanto}).</strong> O BV não entra sozinho quando
          o valor de venda é digitado. Lance o BV em Acréscimos, com quem recebe e o PIX, e confira
          com atenção se o valor de venda é o total <strong>com</strong> o BV.
        </p>
        {onLancar && (
          <Button size="sm" variant="outline" onClick={onLancar}>
            Lançar o BV
          </Button>
        )}
        {!onLancar && lancarHref && (
          <Link to={lancarHref} className="inline-block text-sm font-bold text-ink underline">
            Lançar o BV na aba Comercial
          </Link>
        )}
      </div>
    </div>
  );
}
