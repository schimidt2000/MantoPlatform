import { Link } from "react-router-dom";
import { Button, CopyButton, cn } from "@manto/ui";
import { useSetPaymentStatus, type PagamentoItem, type PaymentStatus } from "../../lib/financeiro";
import {
  BUCKET_TONE,
  STATUS_OPTIONS_BY_TYPE,
  TYPE_BADGE_CLASS,
  TYPE_LABELS,
  brl,
  bucketOf,
  formatDate,
  rawAmount,
} from "../../lib/pagamentos";

/**
 * As duas caras de um item da planilha de pagamentos (feature 226): `PagamentoRow` (tabela,
 * a partir de `xl`) e `PagamentoCard` (cartão, no celular e no tablet).
 *
 * A tabela tem 7 colunas e 1040px de largura mínima — no telefone isso virava rolagem lateral
 * infinita, com o favorecido, o PIX e a situação todos fora da tela. O cartão mostra os mesmos
 * dados empilhados, e as duas versões leem faixa, cor e rótulo de `lib/pagamentos.ts`, então
 * nunca divergem.
 */

interface PagamentoViewProps {
  item: PagamentoItem;
  statusLabels: Record<string, string>;
  selected: boolean;
  selectable: boolean;
  onToggleSelect: (item: PagamentoItem) => void;
  /** Abre a janela de adiantamentos (só itens de salário chamam). */
  onOpenAdvances: (item: PagamentoItem) => void;
}

function descricaoDe(item: PagamentoItem): string {
  return item.event_title || item.copy_label || "—";
}

/** Chip do tipo do item (+ aviso de PIX faltando no BV). */
function TypeBadge({ item }: { item: PagamentoItem }) {
  return (
    <>
      <span
        className={cn(
          "rounded-md px-1.5 py-0.5 text-[10px] font-bold",
          TYPE_BADGE_CLASS[item.type],
        )}
      >
        {TYPE_LABELS[item.type]}
      </span>
      {item.type === "bv" && item.missing_data && (
        <span
          className="rounded-md bg-red-soft px-1.5 py-0.5 text-[10px] font-bold text-red"
          title="Falta o PIX de quem recebe o BV"
        >
          ⚠ falta PIX
        </span>
      )}
    </>
  );
}

/** Seletor de situação — a mesma mutation e as mesmas cores na tabela e no cartão. */
function StatusSelect({
  item,
  statusLabels,
  className,
}: {
  item: PagamentoItem;
  statusLabels: Record<string, string>;
  className?: string;
}) {
  const setStatus = useSetPaymentStatus();
  const tone = BUCKET_TONE[bucketOf(item)];
  const descricao = descricaoDe(item);

  return (
    <div className="flex flex-col items-start gap-1">
      <select
        value={item.status}
        onChange={(e) =>
          setStatus.mutate({
            item_type: item.type,
            item_id: item.id,
            status: e.target.value as PaymentStatus,
          })
        }
        disabled={setStatus.isPending}
        aria-label={`Situação de ${descricao}`}
        className={cn(
          "rounded-md border font-bold disabled:opacity-50",
          tone.select,
          className ?? "px-1.5 py-1 text-[11px]",
        )}
      >
        {STATUS_OPTIONS_BY_TYPE[item.type].map((status) => (
          <option key={status} value={status}>
            {statusLabels[status] ?? status}
          </option>
        ))}
      </select>
      <span aria-live="polite" className="sr-only">
        {setStatus.isPending ? "Salvando situação…" : ""}
      </span>
      {setStatus.isError && (
        <span className="text-[10px] text-red">Falha ao salvar — tente de novo.</span>
      )}
    </div>
  );
}

/** "adiantado R$ 500,00 (2x)" — só aparece em salário que já teve adiantamento. */
function AdvanceHint({ item }: { item: PagamentoItem }) {
  if (item.type !== "salary" || (item.advance_amount ?? 0) <= 0) return null;
  const count = item.advances?.length ?? 0;
  return (
    <div className="text-[10px] font-semibold text-gold-ink">
      adiantado {brl(item.advance_amount)}
      {count > 1 ? ` (${count}x)` : ""}
    </div>
  );
}

function AdvancesButton({
  item,
  onOpenAdvances,
  className,
}: {
  item: PagamentoItem;
  onOpenAdvances: (item: PagamentoItem) => void;
  className?: string;
}) {
  if (item.type !== "salary") return null;
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className={className}
      onClick={() => onOpenAdvances(item)}
    >
      ✎ Adiantamentos
    </Button>
  );
}

/** Linha da tabela — desktop (`xl` e acima, onde os 1040px da tabela cabem). */
export function PagamentoRow({
  item,
  statusLabels,
  selected,
  selectable,
  onToggleSelect,
  onOpenAdvances,
}: PagamentoViewProps) {
  const bucket = bucketOf(item);
  const tone = BUCKET_TONE[bucket];
  const descricao = descricaoDe(item);

  return (
    <tr className={cn("border-b border-line align-top transition-colors last:border-0", tone.row)}>
      {/* Seleção em lote — barra lateral roxa marca a linha marcada. A borda existe sempre
          (transparente quando não selecionada) para a linha não "pular" 4px ao marcar. */}
      <td
        className={cn(
          "border-l-4 border-l-transparent px-2 py-2",
          selected && "border-l-accent bg-accent-soft",
        )}
      >
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(item)}
            aria-label={`Selecionar ${descricao}`}
          />
        )}
      </td>

      {/* Vencimento */}
      <td className="whitespace-nowrap px-3 py-2 text-xs text-muted">{formatDate(item.date)}</td>

      {/* Descrição detalhada: tipo + item */}
      <td className="px-3 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <TypeBadge item={item} />
          {item.event_id ? (
            <Link to={`/events/${item.event_id}`} className="font-bold text-ink hover:underline">
              {descricao}
            </Link>
          ) : (
            <span className="font-bold text-ink">{descricao}</span>
          )}
          {item.copy_label && (
            <CopyButton value={item.copy_label} label="Copiar descrição e data" />
          )}
        </div>
        {item.sublabel && <div className="mt-0.5 text-[11px] text-muted">{item.sublabel}</div>}
      </td>

      {/* Favorecido */}
      <td className="px-3 py-2 font-bold text-ink">{item.person_name || "—"}</td>

      {/* Valor */}
      <td className="whitespace-nowrap px-3 py-2 text-right">
        <div className="flex items-center justify-end gap-1 font-bold tabular-nums text-ink">
          <span>{brl(item.amount)}</span>
          <CopyButton value={rawAmount(item.amount)} label="Copiar valor" />
        </div>
        <AdvanceHint item={item} />
        <AdvancesButton item={item} onOpenAdvances={onOpenAdvances} className="mt-1 h-7 px-2 text-[11px]" />
      </td>

      {/* Chave PIX + cópia rápida */}
      <td className="px-3 py-2 text-[11px]">
        {item.pix_key ? (
          <div className="flex items-start gap-1">
            <div className="min-w-0">
              <span className="break-all text-ink">{item.pix_key}</span>
              {item.pix_key_type && (
                <span className="mt-0.5 block text-[10px] font-semibold uppercase text-muted">
                  {item.pix_key_type}
                </span>
              )}
            </div>
            <CopyButton value={item.pix_key} label="Copiar chave PIX" />
          </div>
        ) : (
          <span className="text-muted">—</span>
        )}
      </td>

      {/* Situação */}
      <td className="whitespace-nowrap px-3 py-2">
        {bucket === "futuro" && (
          <span className="mb-1 inline-block rounded-md bg-gold-soft px-1.5 py-0.5 text-[10px] font-bold text-gold-ink">
            ⏳ Futuro
          </span>
        )}
        <StatusSelect item={item} statusLabels={statusLabels} />
      </td>
    </tr>
  );
}

/** Cartão — celular e tablet (abaixo de `xl`). */
export function PagamentoCard({
  item,
  statusLabels,
  selected,
  selectable,
  onToggleSelect,
  onOpenAdvances,
}: PagamentoViewProps) {
  const bucket = bucketOf(item);
  const tone = BUCKET_TONE[bucket];
  const descricao = descricaoDe(item);

  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        tone.row,
        selected ? "border-accent ring-2 ring-accent/30" : "border-line",
      )}
    >
      <div className="flex items-start gap-2">
        {selectable && (
          // Alvo de 44px (Princípio VIII) sem afastar o texto: o rótulo cresce com margem
          // negativa, então a caixa cresce para dentro do respiro que o card já tem.
          <label className="-m-1.5 flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={selected}
              onChange={() => onToggleSelect(item)}
              aria-label={`Selecionar ${descricao}`}
            />
          </label>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <TypeBadge item={item} />
            <span className="text-[11px] font-semibold text-muted">{formatDate(item.date)}</span>
            {bucket === "futuro" && (
              <span className="rounded-md bg-gold-soft px-1.5 py-0.5 text-[10px] font-bold text-gold-ink">
                ⏳ Futuro
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {item.event_id ? (
              <Link
                to={`/events/${item.event_id}`}
                className="break-words text-sm font-bold text-ink hover:underline"
              >
                {descricao}
              </Link>
            ) : (
              <span className="break-words text-sm font-bold text-ink">{descricao}</span>
            )}
            {item.copy_label && (
              <CopyButton value={item.copy_label} label="Copiar descrição e data" />
            )}
          </div>
          {item.sublabel && <div className="mt-0.5 text-[11px] text-muted">{item.sublabel}</div>}
          {item.person_name && (
            <div className="mt-0.5 text-xs text-muted">
              Favorecido: <span className="font-bold text-ink">{item.person_name}</span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold tabular-nums text-ink">{brl(item.amount)}</span>
            <CopyButton value={rawAmount(item.amount)} label="Copiar valor" />
          </div>
          <AdvanceHint item={item} />
        </div>
        <StatusSelect
          item={item}
          statusLabels={statusLabels}
          className="h-11 px-2 text-sm"
        />
      </div>

      {item.pix_key && (
        <div className="mt-2 flex items-start gap-1.5 border-t border-line/70 pt-2 text-[11px]">
          <span className="shrink-0 font-semibold uppercase text-muted">
            PIX{item.pix_key_type ? ` · ${item.pix_key_type}` : ""}
          </span>
          <span className="min-w-0 flex-1 break-all text-ink">{item.pix_key}</span>
          <CopyButton value={item.pix_key} label="Copiar chave PIX" />
        </div>
      )}

      {/* Alvo de toque de 44px (Princípio VIII) — o `sm` do botão tem 36px. */}
      <AdvancesButton item={item} onOpenAdvances={onOpenAdvances} className="mt-2 h-11 w-full" />
    </div>
  );
}
