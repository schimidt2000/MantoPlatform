import { Bell, CalendarCheck, CalendarX, FileText, FileX, Star, UserX, type LucideIcon } from "lucide-react";
import { cn } from "@manto/ui";
import { horaDeIsoLocal } from "../../lib/horaLocal";
import type { Notificacao } from "../../lib/notificacoes";

/** Ícone por `kind` — o front só precisa deste mapa; texto e link já vêm prontos do servidor. */
const ICONE_POR_KIND: Record<string, LucideIcon> = {
  "form_response.nova": FileText,
  "avaliacao.recebida": Star,
  "convite.recusado": UserX,
  // Feature 303 — o mesmo ícone do selo "Sumiu do Google" na agenda.
  "evento.sumiu_google": CalendarX,
  // Feature 306 — o cancelamento: o ensaio que caiu e a escala a desfazer.
  "evento.cancelado": CalendarX,
  "evento.cancelado_escala": UserX,
  // Feature 315 — o pedido de cancelamento (o ícone do selo) e a resposta a quem pediu.
  "evento.pedido_cancelamento": FileX,
  "evento.pedido_decidido": CalendarCheck,
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
 * `bg-accent` + título em negrito; `urgent` (nota baixa, recusa em cima da hora, evento que sumiu
 * do Google) = borda e ícone vermelhos — cor e badge, não interrupção.
 *
 * O aviso `urgent` não é cortado numa linha (feature 303): o título quebra em até duas e o corpo
 * em até três, com o texto inteiro no `title`. Com o prefixo fixo "Sumiu do Google Agenda — ",
 * sobravam ~10 caracteres para o nome do evento no painel de 375 px. O `info` segue numa linha.
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
        {/* `items-start` + `mt-1.5` no ponto: com o título em duas linhas, o ponto acompanha a
            primeira linha em vez de flutuar no meio. */}
        <span className="flex items-start gap-2">
          {naoLida && (
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" aria-hidden />
          )}
          <span
            title={urgente ? item.title : undefined}
            className={cn(
              "text-sm text-ink",
              urgente ? "line-clamp-2 break-words" : "truncate",
              naoLida && "font-semibold",
            )}
          >
            {item.title}
          </span>
          {naoLida && <span className="sr-only">(não lida)</span>}
        </span>
        {item.body && (
          <span
            title={urgente ? item.body : undefined}
            // Sem `block` no ramo do `line-clamp`: o utilitário de display vem depois no CSS do
            // Tailwind e trocaria o `-webkit-box` de que o corte em linhas depende.
            className={cn(
              "text-xs text-muted",
              urgente ? "line-clamp-3 break-words" : "block truncate",
            )}
          >
            {item.body}
          </span>
        )}
      </span>
      <span className="shrink-0 pt-0.5 text-[11px] tabular-nums text-muted">
        {horaDeIsoLocal(item.created_at)}
      </span>
    </button>
  );
}
