import { type ReactNode, type TableHTMLAttributes, type ThHTMLAttributes, type TdHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export interface TableProps extends TableHTMLAttributes<HTMLTableElement> {
  children: ReactNode;
}

/**
 * Tabela densa padrão do design system Manto — extraída da convenção já usada em
 * `PagamentosPage`/`GastosRecorrentesPage` (feature 189): `border-collapse`, corpo em
 * `text-[13px]`, sem sticky header (convenção do projeto não usa), densidade via
 * `overflow-x-auto` no wrapper em vez de encolher colunas.
 */
function Table({ className, children, ...props }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full border-collapse text-[13px]", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export interface TableRowProps extends TableHTMLAttributes<HTMLTableRowElement> {
  /** Linha de cabeçalho (dentro de `<thead>`) — borda mais grossa, sem tinta de status. */
  head?: boolean;
  children: ReactNode;
}

function TableRow({ head = false, className, children, ...props }: TableRowProps) {
  return (
    <tr
      className={cn(
        head
          ? "border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted"
          : "border-b border-line align-top last:border-0",
        className,
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export interface TableCellProps
  extends ThHTMLAttributes<HTMLTableCellElement>,
    TdHTMLAttributes<HTMLTableCellElement> {
  /** Renderiza `<th>` (cabeçalho) em vez de `<td>`. Default: `<td>`. */
  as?: "th" | "td";
  align?: "left" | "right";
  children?: ReactNode;
}

function TableCell({ as = "td", align = "left", className, children, ...props }: TableCellProps) {
  const Comp = as;
  return (
    <Comp
      className={cn(
        "px-3 py-2",
        align === "right" && "text-right tabular-nums",
        className,
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}

export { Table, TableRow, TableCell };
