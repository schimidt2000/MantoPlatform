import { Bell, FileText, Star, UserX, type LucideIcon } from "lucide-react";
import { cn } from "@manto/ui";
import { horaDeIsoLocal } from "../../lib/horaLocal";
import type { Notificacao } from "../../lib/notificacoes";

/** Ícone por `kind` — o front só precisa deste mapa; texto e link já vêm prontos do servidor. */
const ICONE_POR_KIND: Record<string, LucideIcon> = {
  "form_response.nova": FileText,
  "avaliacao.recebida": Star,
  "convite.recusado": UserX,
};

interface NotificacaoItemProps {
  item: Notificacao;
  onOpen: (item: Notificacao) => void;
}

/**
 * Uma linha da caixa (feature 272) — compartilhada entre o popover do sino e a página
 * `/notificacoes`: duas montagens divergiriam no primeiro ajuste de texto.
 *
 * O item inteiro é um `<button>`: clicar marca lida e navega para `link_path`. Não lida = ponto
 * `bg-accent` + título em negrito; `urgent` (nota baixa, recusa em cima da hora) = borda e ícone
 * vermelhos — cor e badge, não interrupção.
 */
export function NotificacaoItem({ item, onOpen }: NotificacaoItemProps) {
  const Icone = ICONE_POR_KIND[item.kind] ?? Bell;
  const naoLida = item.read_at === null;
  const urgente = item.severity === "urgent";
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className={cn(
        "flex w-full items-start gap-3 px-3 py-2 text-left transition-colors hover:bg-surface-2",
        urgente ? "border-l-2 border-red" : "border-l-2 border-transparent",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          urgente ? "bg-red-soft text-red" : "bg-accent-soft text-accent",
        )}
      >
        <Icone className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          {naoLida && (
            <span className="h-2 w-2 shrink-0 rounded-full bg-accent" aria-hidden />
          )}
          <span className={cn("truncate text-sm text-ink", naoLida && "font-semibold")}>
            {item.title}
          </span>
          {naoLida && <span className="sr-only">(não lida)</span>}
        </span>
        {item.body && <span className="block truncate text-xs text-muted">{item.body}</span>}
      </span>
      <span className="shrink-0 pt-0.5 text-[11px] tabular-nums text-muted">
        {horaDeIsoLocal(item.created_at)}
      </span>
    </button>
  );
}
