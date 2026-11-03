import type { ReactNode } from "react";
import { Table, TableCell, TableRow } from "@manto/ui";
import { MoneyInput } from "@manto/money";

export const DUR_LABELS = ["1h", "2h", "3h", "4h"];
export const INPUT_PRECOS = "h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/**
 * Tabela de 4 durações (1h..4h) da Configuração de Preços — cachês E coeficientes de markup passam
 * pelo mesmo `MoneyInput` (duas casas, digitação BR), como a tela sempre fez. Extraída da página
 * na feature 307 para o card de datas especiais reusar sem copiar.
 */
export interface PriceTableRow {
  label: string;
  /** Feature 324: linha miúda sob o nome ("Com show · sem maquiagem") — o que diferencia linhas de mesmo nome. */
  hint?: string;
  /** Chave da linha quando o `label` se repete (várias linhas "Ator (cara limpa)"). */
  key?: string;
  values: number[];
  onChange: (values: number[]) => void;
  /** Feature 307: linha recusada pelo servidor — os inputs ganham `aria-invalid` e borda vermelha. */
  invalid?: boolean;
  /** Feature 324: ação da linha (ex.: "Remover"), numa coluna extra que só existe se alguma linha tiver. */
  acao?: ReactNode;
}

export function PriceTable({ rows, itemLabel = "Item" }: { rows: PriceTableRow[]; itemLabel?: string }) {
  const temAcao = rows.some((r) => r.acao);
  return (
    <Table>
      <thead>
        <TableRow head>
          <TableCell as="th">{itemLabel}</TableCell>
          {DUR_LABELS.map((d) => (
            <TableCell as="th" align="right" key={d}>
              {d}
            </TableCell>
          ))}
          {temAcao && (
            // `relative`: o `sr-only` é absoluto e, sem âncora, escapa do `overflow-x-auto` e
            // alarga a página inteira no celular.
            <TableCell as="th" align="right" className="relative">
              <span className="sr-only">Ações</span>
            </TableCell>
          )}
        </TableRow>
      </thead>
      <tbody>
        {rows.map((row) => (
          <TableRow key={row.key ?? row.label}>
            <TableCell className="min-w-[150px] align-middle">
              <span className="font-medium text-ink">{row.label}</span>
              {row.hint && <span className="block text-xs text-muted">{row.hint}</span>}
            </TableCell>
            {DUR_LABELS.map((d, i) => (
              <TableCell key={d} align="right" className="align-middle">
                <MoneyInput
                  // `min-w`: sem ele a coluna encolhe no celular até cortar "1.234,56".
                  className={`${INPUT_PRECOS} min-w-[84px] text-right${row.invalid ? " border-red ring-1 ring-red" : ""}`}
                  aria-label={`${row.label}${row.hint ? ` (${row.hint})` : ""} — ${d}`}
                  aria-invalid={row.invalid || undefined}
                  value={row.values[i] ?? 0}
                  onValueChange={(v) => row.onChange(row.values.map((x, idx) => (idx === i ? v : x)))}
                />
              </TableCell>
            ))}
            {temAcao && (
              <TableCell align="right" className="align-middle">
                {row.acao}
              </TableCell>
            )}
          </TableRow>
        ))}
      </tbody>
    </Table>
  );
}
