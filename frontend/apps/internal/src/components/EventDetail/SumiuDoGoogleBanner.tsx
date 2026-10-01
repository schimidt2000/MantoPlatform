import { Link } from "react-router-dom";
import { CalendarX } from "lucide-react";
import { AccordionRow, Button, ConfirmDialog, formatShortDate } from "@manto/ui";
import type { EventoDetalhe } from "../../lib/agenda";
import { DataRow, brl } from "./parts";

export interface SumiuDoGoogleBannerProps {
  data: EventoDetalhe;
  /** Abre o diálogo "Devolver ao Google Agenda" — o diálogo e a mutação moram no cabeçalho. */
  onDevolver?: () => void;
}

/**
 * Banner do evento marcado "Sumiu do Google Agenda" (feature 303). Só aparece quando o servidor
 * manda `sumiu_do_google` — preenchido apenas com o evento marcado e não cancelado.
 *
 * Para todos que abrem o evento: a marca, desde quando, e que a edição fica só no sistema — sem
 * dinheiro, sem botão, sem motivo (o resumo vai a todo papel que vê a agenda). Para o Comercial,
 * uma frase a mais: a decisão é do Superadmin. Para o Superadmin (`flags.can_delete`), o que está
 * em jogo, o botão de devolver e o caminho para quem já recriou o evento à mão. O front não decide
 * por papel, só por flag.
 */
export function SumiuDoGoogleBanner({ data, onDevolver }: SumiuDoGoogleBannerProps) {
  const marca = data.event.sumiu_do_google;
  if (!marca) return null;
  // `flags` é `Record<string, boolean>`: chave ausente é falso.
  const superadmin = Boolean(data.flags.can_delete);
  const comercial = Boolean(data.flags.can_request_delete) && !superadmin;
  return (
    <div className="mt-3 rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="status">
      <p className="flex items-center gap-1.5 font-semibold text-gold-ink">
        <CalendarX aria-hidden className="h-4 w-4 shrink-0" />
        <span>
          Sumiu do Google Agenda — percebido em {formatShortDate(marca.desde)}. O evento continua
          valendo no sistema.
        </span>
      </p>
      <p className="mt-0.5 text-ink">
        O que for editado aqui fica só no sistema e vai ao Google Agenda quando o Superadmin
        devolver o evento.
      </p>
      {comercial && (
        <p className="mt-1 text-ink">
          A decisão é do Superadmin — conte a ele por que o evento saiu do Google Agenda.
        </p>
      )}
      {superadmin && <ParteDoSuperadmin data={data} onDevolver={onDevolver} />}
    </div>
  );
}

/** O que só o Superadmin vê: o quadro, o botão, a linha da próxima entrega e os três passos. */
function ParteDoSuperadmin({ data, onDevolver }: SumiuDoGoogleBannerProps) {
  return (
    <div className="mt-3 space-y-3">
      <div className="rounded-md border border-line bg-panel px-3 py-2">
        <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
          O que está em jogo
        </p>
        <QuadroEmJogo data={data} />
      </div>
      {onDevolver && (
        <Button size="sm" className="w-full sm:w-auto" onClick={onDevolver}>
          Devolver ao Google Agenda
        </Button>
      )}
      <p className="text-ink">
        O cancelamento com devolução do dinheiro chega na próxima entrega. Se este evento foi
        cancelado de verdade, ele fica marcado até lá.
      </p>
      <div className="rounded-md border border-line bg-panel px-3 py-2">
        <AccordionRow
          summary={<span className="text-ink">O evento já foi recriado à mão no Google?</span>}
          contentClassName="pb-2"
        >
          <ol className="list-decimal space-y-1 pl-5 pt-1 text-ink">
            <li>
              Acerte neste evento a data, o horário e o local que valem agora — a devolução usa o
              que está no sistema.
            </li>
            <li>
              Abra o evento que foi recriado, tire dele o que foi lançado em duplicidade (venda,
              comprovantes, contrato, escala) e só então apague-o no Google Agenda — se for apagado
              com algo dentro, ele também fica marcado.
            </li>
            <li>
              Devolva este evento ao Google Agenda — é ele que guarda os comprovantes, o contrato e
              a escala.
            </li>
          </ol>
        </AccordionRow>
      </div>
    </div>
  );
}

/**
 * As linhas do quadro, do detalhe já carregado. `kpi`, `pagamentos`, `elenco` e `group` podem
 * faltar (ENSAIO, papel sem bloco financeiro, servidor antigo): linha ausente, nunca erro.
 *
 * No satélite o `kpi` é o do principal — mostrar a venda ali diria a venda do grupo como se fosse
 * do evento —, então as linhas de dinheiro dão lugar à frase com link para o principal.
 */
function QuadroEmJogo({ data }: { data: EventoDetalhe }) {
  const { kpi, pagamentos, elenco, contratos } = data;
  const grupo = data.event.group;
  const satelite = grupo?.role === "satellite";
  const principal = grupo?.role === "leader";
  const escalados = elenco?.filter((vaga) => vaga.talent).length;
  const comprovantes = pagamentos?.items.length ?? 0;
  return (
    <div className="divide-y divide-line">
      {satelite ? (
        <p className="py-1 text-ink">
          Venda do grupo — os valores estão no{" "}
          {grupo?.leader ? (
            <Link to={`/events/${grupo.leader.id}`} className="text-accent underline">
              evento principal
            </Link>
          ) : (
            "evento principal"
          )}
        </p>
      ) : (
        <>
          {kpi && <DataRow label="Venda">{brl(kpi.sale_value)}</DataRow>}
          {pagamentos && (
            <DataRow label={principal ? "Pago pela cliente (neste evento)" : "Pago pela cliente"}>
              {brl(pagamentos.received_total)}
            </DataRow>
          )}
          {kpi && (
            <DataRow
              label={kpi.commission_source === "estimativa" ? "Comissão (estimativa)" : "Comissão"}
            >
              {brl(kpi.commission)}
            </DataRow>
          )}
          {kpi && <DataRow label="BV">{brl(kpi.bv_total)}</DataRow>}
        </>
      )}
      {escalados !== undefined && <DataRow label="Escalados">{escalados}</DataRow>}
      {(contratos?.length ?? 0) > 0 && <DataRow label="Contrato">anexado</DataRow>}
      {comprovantes > 0 && <DataRow label="Comprovantes">{comprovantes}</DataRow>}
      {(principal || satelite) && (
        <DataRow label="Grupo comercial">{principal ? "principal" : "satélite"}</DataRow>
      )}
    </div>
  );
}

// ── O diálogo ───────────────────────────────────────────────────────────────────────────────────

interface Parede {
  data: string; // dd/mm/aaaa
  hora: string; // HH:MM
  meiaNoite: boolean;
  dia: Date; // meia-noite local do dia — só para a conta do último dia do dia inteiro
}

/** Lê dia e hora da PRÓPRIA string: o ISO vem sem fuso (parede de São Paulo). */
function lerParede(iso: string): Parede | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso);
  if (!m) return null;
  const [, ano, mes, dia, hh = "00", mm = "00"] = m;
  return {
    data: `${dia}/${mes}/${ano}`,
    hora: `${hh}:${mm}`,
    meiaNoite: hh === "00" && mm === "00",
    dia: new Date(Number(ano), Number(mes) - 1, Number(dia)),
  };
}

function dataCurta(d: Date): string {
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}/${d.getFullYear()}`;
}

/**
 * `<data e horário>` do diálogo, nos formatos do contrato: `19/09/2026 15:00 — 18:00`;
 * `19/09/2026 (dia inteiro)` ou `19/09/2026 a 21/09/2026 (dia inteiro)` (último dia inclusivo —
 * no banco o fim do dia inteiro é o exclusivo do Google); `19/09/2026 22:00 — 20/09/2026 02:00`.
 * Não reusa `formatRange`, que mostra `00:00 — 00:00` e perde o dia do fim.
 */
export function quandoSeraRecriado(startAt: string | null, endAt: string | null): string {
  const inicio = startAt ? lerParede(startAt) : null;
  if (!inicio) return "sem data";
  const fim = endAt ? lerParede(endAt) : null;
  if (!fim) return `${inicio.data} ${inicio.hora}`;
  if (inicio.meiaNoite && fim.meiaNoite && fim.dia > inicio.dia) {
    const ultimo = new Date(fim.dia);
    ultimo.setDate(ultimo.getDate() - 1);
    const ate = dataCurta(ultimo);
    return ate === inicio.data
      ? `${inicio.data} (dia inteiro)`
      : `${inicio.data} a ${ate} (dia inteiro)`;
  }
  if (fim.data === inicio.data) return `${inicio.data} ${inicio.hora} — ${fim.hora}`;
  return `${inicio.data} ${inicio.hora} — ${fim.data} ${fim.hora}`;
}

/** Agora em São Paulo, no mesmo formato do ISO sem fuso ("2026-09-30T19:05:00"). */
function agoraEmSaoPaulo(): string {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
    .format(new Date())
    .replace(" ", "T");
}

/** A data já passou? O fim — ou o início, sem fim — antes de agora; evento de hoje ainda não
 * terminado (e o dia inteiro de hoje, cujo fim é amanhã à meia-noite) não passou. */
export function dataJaPassou(startAt: string | null, endAt: string | null): boolean {
  const corte = endAt || startAt;
  if (!corte) return false;
  return corte.slice(0, 19) < agoraEmSaoPaulo();
}

export interface DevolverAoGoogleDialogProps {
  title: string;
  startAt: string | null;
  endAt: string | null;
  open: boolean;
  pending: boolean;
  error?: string | null;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
}

/** Confirmação da devolução: o que vai ser recriado, com os dados do sistema. Não destrutiva. */
export function DevolverAoGoogleDialog({
  title,
  startAt,
  endAt,
  open,
  pending,
  error,
  onConfirm,
  onOpenChange,
}: DevolverAoGoogleDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      title="Devolver ao Google Agenda?"
      confirmLabel="Devolver ao Google Agenda"
      pending={pending}
      error={error}
      onConfirm={onConfirm}
      onOpenChange={onOpenChange}
      description={
        <div className="space-y-2">
          <p className="text-ink">
            Será recriado como: {title} — {quandoSeraRecriado(startAt, endAt)}
          </p>
          {dataJaPassou(startAt, endAt) && (
            <p className="font-medium text-gold-ink">
              Esta data já passou — se o evento mudou de dia, edite a data antes de devolver.
            </p>
          )}
          <p>
            Ele volta sem convidados — os convites por e-mail não são reenviados. Ensaios que
            também foram apagados do Google não voltam.
          </p>
        </div>
      }
    />
  );
}
