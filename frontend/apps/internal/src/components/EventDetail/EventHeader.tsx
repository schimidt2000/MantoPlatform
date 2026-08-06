import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";
import {
  buildCobrancaMsg,
  buildCobrancaReembolsoMsg,
  buildConfirmacaoMsg,
  buildFeedbackMsg,
  useFeedbackLink,
} from "../../lib/eventDetail";
import { useDeleteEvent, useSyncEvent, useToggleConfirm } from "../../lib/eventOps";
import { KebabMenu, type KebabMenuItem } from "../KebabMenu";
import { formatRange } from "./parts";

/** Rótulo e cor do badge de tipo do evento (mesmo mapa da tela antiga). */
const TYPE_LABELS: Record<string, { label: string; tone: "blue" | "gold" | "neutral" | "green" }> = {
  "R&I": { label: "Receptivo & Interativo", tone: "blue" },
  RI: { label: "Receptivo & Interativo", tone: "blue" },
  SHOW: { label: "Show", tone: "gold" },
  CORP: { label: "Corporativo", tone: "neutral" },
  VM: { label: "Visita Mágica", tone: "blue" },
  SOCIAL: { label: "Evento Social", tone: "green" },
};

/** Campos exportáveis do elenco, na ordem em que aparecem na linha gerada. */
const EXPORT_FIELDS = [
  { key: "personagem", label: "Personagem" },
  { key: "nome", label: "Nome completo" },
  { key: "top", label: "Top" },
  { key: "bottom", label: "Bottom" },
  { key: "shoe", label: "Calçado" },
  { key: "height", label: "Altura" },
] as const;

type ExportFieldKey = (typeof EXPORT_FIELDS)[number]["key"];

interface ExportElencoDialogProps {
  data: EventoDetalhe;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Modal "Exportar elenco": monta um texto com os campos escolhidos, pronto para copiar. */
function ExportElencoDialog({ data, open, onOpenChange }: ExportElencoDialogProps) {
  const [fields, setFields] = useState<ExportFieldKey[]>(["personagem", "nome"]);
  const [copied, setCopied] = useState(false);
  const escalados = (data.elenco ?? []).filter((r) => r.talent);

  const text = escalados
    .map((role) => {
      const talent = role.talent!;
      const partes: string[] = [];
      if (fields.includes("personagem")) partes.push(role.character_name);
      if (fields.includes("nome")) partes.push(talent.name);
      if (fields.includes("top") && talent.size_top) partes.push(`Top: ${talent.size_top}`);
      if (fields.includes("bottom") && talent.size_bottom)
        partes.push(`Bottom: ${talent.size_bottom}`);
      if (fields.includes("shoe") && talent.shoe_size) partes.push(`Calçado: ${talent.shoe_size}`);
      if (fields.includes("height") && talent.height_cm) partes.push(`${talent.height_cm}cm`);
      return partes.join(" — ");
    })
    .join("\n");

  const toggle = (key: ExportFieldKey) =>
    setFields((prev) => (prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key]));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard bloqueado: o texto segue visível no textarea para seleção manual.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Exportar elenco</DialogTitle>
        </DialogHeader>
        {escalados.length === 0 ? (
          <p className="text-sm text-muted">Nenhum talento escalado ainda.</p>
        ) : (
          <>
            <p className="mb-3 text-sm text-muted">
              {escalados.length} pessoa(s) escalada(s). Selecione os campos:
            </p>
            <div className="mb-3 flex flex-wrap gap-x-4 gap-y-2">
              {EXPORT_FIELDS.map((field) => (
                <label key={field.key} className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={fields.includes(field.key)}
                    onChange={() => toggle(field.key)}
                  />
                  {field.label}
                </label>
              ))}
            </div>
            <textarea
              readOnly
              rows={8}
              value={text}
              aria-label="Texto do elenco"
              className="w-full rounded-md border border-line bg-surface-2 p-2 font-mono text-xs text-ink"
            />
          </>
        )}
        <DialogFooter>
          <Button size="sm" onClick={copy} disabled={!text}>
            {copied ? "✓ Copiado" : "Copiar texto"}
          </Button>
        </DialogFooter>
        <span aria-live="polite" className="sr-only">
          {copied ? "Elenco copiado" : ""}
        </span>
      </DialogContent>
    </Dialog>
  );
}

/** Copia um texto e devolve se a área de transferência aceitou. */
async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export interface EventHeaderProps {
  data: EventoDetalhe;
}

/**
 * Cabeçalho da tela: título, badges de tipo/confirmação, faixa horária e o menu
 * "⋯ Ferramentas" com as ações comerciais e operacionais do evento (feature 190).
 *
 * Toda ação que copia texto dá retorno imediato na própria tela ("✓ Copiado", com
 * `aria-live`) — nenhum item do menu fica "morto" ao clique (Princípio V).
 */
export function EventHeader({ data }: EventHeaderProps) {
  const navigate = useNavigate();
  const event = data.event;
  const sync = useSyncEvent(event.id);
  const confirm = useToggleConfirm(event.id);
  const remove = useDeleteEvent(event.id);
  const feedbackLink = useFeedbackLink(event.id);
  const [exportOpen, setExportOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [aviso, setAviso] = useState("");

  const anunciar = (mensagem: string) => {
    setAviso(mensagem);
    setTimeout(() => setAviso(""), 2200);
  };

  const copiar = async (texto: string, sucesso: string) =>
    anunciar((await copyToClipboard(texto)) ? sucesso : "Não foi possível copiar.");

  const mensagens = data.mensagens;
  const canComercial = Boolean(data.flags.can_confirm);
  const canCasting = Boolean(data.flags.show_casting);
  const reembolsosPendentes = data.reembolsos_pendentes_total ?? 0;
  const cobrancaLiberada = Boolean(data.cobranca?.enabled);

  const items: KebabMenuItem[] = [];
  if (event.google_html_link && canCasting) {
    items.push({ label: "🔄 Sincronizar", onClick: () => sync.mutate() });
  }
  if (canCasting || canComercial) {
    items.push({ label: "📋 Exportar elenco", onClick: () => setExportOpen(true) });
  }
  if (canComercial) {
    if (event.google_html_link) {
      items.push({
        label: "📅 Editar no Google Agenda",
        onClick: () => window.open(event.google_html_link!, "_blank", "noopener"),
      });
    }
    if (mensagens) {
      items.push({
        label: "✅ Confirmar dados do evento",
        title: "Copiar mensagem de confirmação do evento",
        onClick: () => copiar(buildConfirmacaoMsg(mensagens), "Mensagem copiada."),
      });
      items.push({
        label: "💰 Cobrança",
        disabled: !cobrancaLiberada,
        title: cobrancaLiberada
          ? "Copiar mensagem de cobrança do valor em aberto"
          : "Disponível apenas na data limite de pagamento ou em atraso",
        onClick: () => copiar(buildCobrancaMsg(mensagens), "Mensagem de cobrança copiada."),
      });
      items.push({
        label: "💸 Cobrar reembolsos",
        disabled: reembolsosPendentes <= 0,
        title:
          reembolsosPendentes > 0
            ? `Copiar cobrança de R$ ${formatBRL(reembolsosPendentes)} em reembolsos`
            : "Nenhum reembolso pendente neste evento",
        onClick: () =>
          copiar(buildCobrancaReembolsoMsg(mensagens), "Mensagem de reembolso copiada."),
      });
    }
    items.push({
      label: event.confirmed ? "✓ Evento confirmado — desfazer" : "☐ Marcar evento como confirmado",
      onClick: () => confirm.mutate(),
    });
    items.push({
      label: "💬 Pedir feedback da cliente",
      disabled: data.feedback_link_pendente === false,
      title:
        data.feedback_link_pendente === false
          ? "A cliente já enviou feedback para este evento"
          : "Copiar link da página de avaliação deste evento",
      onClick: () =>
        feedbackLink.mutate(undefined, {
          onSuccess: ({ url }) => copiar(buildFeedbackMsg(url), "Link de avaliação copiado."),
          onError: () => anunciar("Não foi possível gerar o link."),
        }),
    });
  }
  // Desde a 210 os dados do evento são editados na própria aba onde aparecem; o formulário em
  // bloco continua aqui para quem quer mexer em elenco, clientes e valores de uma vez só —
  // deixou de ser o caminho obrigatório, então saiu da barra e virou item de menu.
  if (data.flags.can_edit_core) {
    items.push({
      label: "✏️ Editar tudo (formulário completo)",
      title: "Abrir o formulário em bloco — elenco, clientes e valores na mesma tela",
      onClick: () => navigate(`/events/${event.id}/edit`),
    });
  }
  if (data.flags.can_delete) {
    items.push({ label: "🗑 Excluir evento", destructive: true, onClick: () => setDeleteOpen(true) });
  }

  const typeInfo = TYPE_LABELS[event.event_type] ?? {
    label: event.event_type,
    tone: "neutral" as const,
  };
  const pendente =
    sync.isPending || confirm.isPending || feedbackLink.isPending || remove.isPending;

  return (
    <header className="mb-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink sm:text-2xl">{event.title}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-muted">
            {event.event_type && <Badge tone={typeInfo.tone}>{typeInfo.label}</Badge>}
            <span className="tabular-nums">{formatRange(event.start_at, event.end_at)}</span>
            {event.location && <span>• {event.location}</span>}
            {event.confirmed && (
              <Badge tone="green">
                ✓ Confirmado{event.confirmed_by ? ` por ${event.confirmed_by}` : ""}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {pendente && <span className="text-sm text-muted">Salvando…</span>}
          {items.length > 0 && (
            <KebabMenu items={items} label="Ferramentas do evento" triggerLabel="Ferramentas" />
          )}
          <Button asChild variant="outline" size="sm">
            <Link to="/agenda">
              <span aria-hidden="true">←</span>
              <span className="hidden sm:inline">Voltar para Agenda</span>
              <span className="sr-only sm:hidden">Voltar para Agenda</span>
            </Link>
          </Button>
        </div>
      </div>

      <p aria-live="polite" className="mt-2 min-h-[1.25rem] text-sm text-green">
        {aviso}
      </p>
      {sync.isError && <p className="text-sm text-red">{sync.error?.message}</p>}
      {remove.isError && <p className="text-sm text-red">{remove.error?.message}</p>}

      <ExportElencoDialog data={data} open={exportOpen} onOpenChange={setExportOpen} />

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent open={deleteOpen}>
          <DialogHeader>
            <DialogTitle>Excluir evento</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-ink">
            Excluir o evento “{event.title}”? Esta ação não pode ser desfeita.
          </p>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(false)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              className="text-red"
              variant="outline"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(undefined, {
                  onSuccess: () => navigate("/agenda"),
                  onError: () => setDeleteOpen(false),
                })
              }
            >
              Excluir evento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </header>
  );
}
