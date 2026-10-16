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
  values: number[];
  onChange: (values: number[]) => void;
  /** Feature 307: linha recusada pelo servidor — os inputs ganham `aria-invalid` e borda vermelha. */
  invalid?: boolean;
}

export function PriceTable({ rows }: { rows: PriceTableRow[] }) {
  return (
    <Table>
      <thead>
        <TableRow head>
          <TableCell as="th">Item</TableCell>
          {DUR_LABELS.map((d) => (
            <TableCell as="th" align="right" key={d}>
              {d}
            </TableCell>
          ))}
        </TableRow>
      </thead>
      <tbody>
        {rows.map((row) => (
          <TableRow key={row.label}>
            <TableCell className="font-medium text-ink">{row.label}</TableCell>
            {DUR_LABELS.map((d, i) => (
              <TableCell key={d} align="right">
                <MoneyInput
                  className={`${INPUT_PRECOS} text-right${row.invalid ? " border-red ring-1 ring-red" : ""}`}
                  aria-invalid={row.invalid || undefined}
                  value={row.values[i] ?? 0}
                  onValueChange={(v) => row.onChange(row.values.map((x, idx) => (idx === i ? v : x)))}
                />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </tbody>
    </Table>
  );
}
