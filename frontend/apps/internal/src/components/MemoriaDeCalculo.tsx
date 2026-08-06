import { formatBRL } from "@manto/money";
import type { MemoriaLinha } from "../lib/orcamento";

/**
 * Detalhamento linha a linha do orçamento — o "abrir a conta" que o comercial mostra quando a
 * cliente pergunta de onde veio o valor. As linhas e a ordem vêm prontas do servidor
 * (`quote_ops.calculate_quote`), que é quem faz a conta; aqui só se pinta.
 */

/**
 * Cor de fundo por papel da linha na conta — mesma leitura do painel antigo.
 *
 * `markup`/`pos` usavam `bg-amber-50 dark:bg-amber-950/30` e `bg-violet-50 dark:bg-violet-950/25`,
 * cores cruas do Tailwind fora do design system. Pior: como nenhum config declarava `darkMode`,
 * valia o padrão `media` e essas DUAS linhas já escureciam sozinhas conforme o tema do sistema
 * operacional, enquanto o resto da tela continuava claro. Agora são tokens (`gold-soft` para o
 * âmbar do markup, `accent-soft` para o violeta do pós), que trocam de tema junto com a tela.
 */
const FUNDO: Record<MemoriaLinha["tipo"], string> = {
  cache: "",
  subtotal: "bg-surface-2 font-semibold",
  markup: "bg-gold-soft",
  pos: "bg-accent-soft",
  total: "bg-green-soft font-bold",
};

/** Linha de markup traz fatores (2,6×), não reais. */
function celula(linha: MemoriaLinha, valor: number): string {
  if (linha.tipo === "markup") {
    return valor > 0 ? `${valor.toLocaleString("pt-BR")}×` : "—";
  }
  return formatBRL(valor);
}

export function MemoriaDeCalculo({ linhas }: { linhas: MemoriaLinha[] | undefined }) {
  if (!linhas?.length) {
    return (
      <p className="text-sm text-muted">
        Este orçamento foi salvo antes do detalhamento existir, então a memória não foi registrada.
        Use “Recalcular” para refazer a conta e ver o detalhamento.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-xs uppercase text-muted">
            <th className="py-2 pr-3 text-left font-medium">Item</th>
            {["1h", "2h", "3h", "4h"].map((h) => (
              <th key={h} className="py-2 pl-3 text-right font-medium tabular-nums">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha, i) => (
            <tr key={`${linha.label}-${i}`} className={`border-b border-line/60 ${FUNDO[linha.tipo]}`}>
              <td className="py-2 pr-3 text-ink">
                {linha.label}
                {linha.detalhe && (
                  <span className="ml-1 text-xs font-normal text-muted">({linha.detalhe})</span>
                )}
              </td>
              {linha.valores.map((valor, j) => (
                <td key={j} className="py-2 pl-3 text-right tabular-nums text-ink">
                  {celula(linha, valor)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
