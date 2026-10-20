import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Combobox, type ComboboxOption } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { ProdutoAplicado, ProdutoDeTabela } from "../../lib/orcamento";
import { ProdutoLinha } from "./ProdutoLinha";

export interface ProdutoSelecionado {
  chave: string;
}

/**
 * Feature 309 — card "Produtos de tabela" da calculadora: a vendedora escolhe um pacote fechado (a
 * Visita Mágica) pelo preço da tabela de venda, em vez de montar Papai Noel + coordenador à mão e
 * torcer para o markup dar 2.500. `Combobox` de `@manto/ui`, nunca `<select>` (Princípio X.1): a
 * lista cresce quando o dono cadastrar outros produtos.
 *
 * As linhas selecionadas vêm de `aplicados` (`quote.produtos`, o preço que o SERVIDOR resolveu na
 * data — 5.000 em 24/12, estimativa marcada numa faixa sem preço); enquanto a resposta não chega, a
 * linha mostra "calculando…" em vez de chutar o preço normal. Produto inativo some da lista mas
 * continua resolvendo um orçamento antigo recalculado (selo "inativo"); produto apagado da tabela é
 * recusado pelo servidor (400 em `fields.produtos`, que a página já mostra).
 */
export function ProdutosCard({
  produtos,
  selecionados,
  aplicados,
  calculando = false,
  onChange,
}: {
  produtos: Record<string, ProdutoDeTabela>;
  selecionados: ProdutoSelecionado[];
  aplicados: ProdutoAplicado[] | undefined;
  /** Recálculo em voo: a linha sem resposta diz "calculando…"; parado (erro), diz "não calculado". */
  calculando?: boolean;
  onChange: (selecionados: ProdutoSelecionado[]) => void;
}) {
  const reduzir = useReducedMotion();
  const [escolha, setEscolha] = useState<string | null>(null);

  const options = useMemo<ComboboxOption[]>(
    () =>
      Object.entries(produtos)
        .filter(([, p]) => p.ativo)
        .map(([chave, p]) => ({
          value: chave,
          label: p.rotulo,
          description: `R$ ${formatBRL(p.preco)}${p.descricao ? ` · ${p.descricao}` : ""}`,
          fallbackIcon: "🎅",
          imageShape: "square",
        })),
    [produtos],
  );

  const adicionar = () => {
    if (!escolha) return;
    onChange([...selecionados, { chave: escolha }]);
    setEscolha(null);
  };
  const remover = (indice: number) => onChange(selecionados.filter((_, i) => i !== indice));
  const transicao = reduzir ? { duration: 0 } : { duration: 0.18 };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Produtos de tabela</CardTitle>
        <p className="text-xs text-muted">
          Pacote fechado pelo preço da tabela de venda (fixo por visita, fora do markup). Os cachês das
          vagas vêm da tabela de preços na data do evento. Pode repetir o mesmo produto.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="flex-1">
            <Combobox
              aria-label="Produto de tabela"
              placeholder="Escolher produto…"
              emptyMessage="Nenhum produto ativo na tabela de preços."
              options={options}
              value={escolha}
              onChange={(valor) => setEscolha(valor)}
            />
          </div>
          <Button type="button" size="sm" variant="outline" disabled={!escolha} onClick={adicionar}>
            Adicionar
          </Button>
        </div>

        <AnimatePresence initial={false}>
          {selecionados.map((sel, i) => {
            const aplicado = aplicados?.[i];
            const tabela = produtos[sel.chave];
            const casado = aplicado && aplicado.chave === sel.chave ? aplicado : null;
            const nome = tabela?.rotulo ?? sel.chave;
            const botao = (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                aria-label={`Remover ${nome} (item ${i + 1})`}
                onClick={() => remover(i)}
              >
                Remover
              </Button>
            );
            return (
              <motion.div
                key={`${sel.chave}-${i}`}
                layout
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={transicao}
              >
                {casado ? (
                  <ProdutoLinha
                    produto={casado}
                    acao={
                      <div className="flex items-center gap-2">
                        {tabela && !tabela.ativo && <Badge tone="gold">inativo</Badge>}
                        {botao}
                      </div>
                    }
                  />
                ) : (
                  <div className="flex items-center justify-between gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-sm">
                    <p className="text-ink">
                      📦 <span className="font-medium">{nome}</span>
                      <span className="text-muted">
                        {!tabela
                          ? " — não está mais na tabela de preços"
                          : calculando
                            ? " — calculando…"
                            : " — não calculado (veja o erro abaixo)"}
                      </span>
                    </p>
                    {botao}
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
        {selecionados.length === 0 && (
          <p className="text-xs text-muted">Nenhum produto selecionado — a conta segue a fórmula normal.</p>
        )}
      </CardContent>
    </Card>
  );
}
