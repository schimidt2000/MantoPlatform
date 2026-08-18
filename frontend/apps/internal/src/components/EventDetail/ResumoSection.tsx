import { useState } from "react";
import { Pencil, TriangleAlert } from "lucide-react";
import { Badge, Button, Card } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import type { EventoDetalhe } from "../../lib/agenda";
import { useUpdateEventBasics, type EventBasicsInput } from "../../lib/eventInline";
import { dataDeIsoLocal, horaDeIsoLocal } from "../../lib/horaLocal";
import { GoogleAddressInput } from "../GoogleAddressInput";
import { descriptionToText } from "./ObservacoesSection";
import { brl, DataRow, formatDay, formatTime, INPUT_CLASS, Panel } from "./parts";

/** Tipos oferecidos na edição — os mesmos do formulário de criação (`DadosEventoBlock`). */
const EVENT_TYPES: { value: string; label: string }[] = [
  { value: "SHOW", label: "SHOW — Show com som" },
  { value: "CORP", label: "CORP — Corporativo" },
  { value: "R&I", label: "R&I — Receptivo e Interativo" },
  { value: "VM", label: "VM — Visita Mágica" },
];

const LABEL_CLASS = "mb-1 block text-[11px] font-bold uppercase tracking-wider text-muted";

/** Avisos não-bloqueantes do que a edição removeu automaticamente (feature 239, decisão 7 —
 * troca de tipo saindo de SHOW cancela ensaio e vagas de som). Não impede o formulário de
 * fechar: aparece depois de salvo, com um "Fechar" para dispensar. */
function AvisosCard({ avisos, onFechar }: { avisos: string[]; onFechar: () => void }) {
  return (
    <Card className="mb-4 flex items-start gap-3 border-l-4 border-l-gold px-4 py-3">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-gold-ink" aria-hidden="true" />
      <div className="flex-1 space-y-1 text-sm text-ink">
        {avisos.map((aviso, i) => (
          <p key={i}>{aviso}</p>
        ))}
      </div>
      <button type="button" className="text-xs text-muted hover:text-ink" onClick={onFechar}>
        Fechar
      </button>
    </Card>
  );
}

/** Estado inicial do formulário a partir do evento — datas recortadas, nunca via `Date`. */
function valoresIniciais(data: EventoDetalhe): EventBasicsInput {
  const event = data.event;
  return {
    title: event.title,
    event_type: event.event_type || "",
    date: dataDeIsoLocal(event.start_at),
    start: horaDeIsoLocal(event.start_at),
    end: horaDeIsoLocal(event.end_at),
    location: event.location ?? "",
    description: event.description ? descriptionToText(event.description) : "",
  };
}

/**
 * Formulário de edição dos dados do evento, aberto no lugar da leitura (feature 215).
 *
 * Salva pelo endpoint estreito `PATCH /events/<id>/basico`: mexer no horário aqui não toca
 * elenco nem clientes. Em caso de erro o que foi digitado permanece na tela (Princípio VI) —
 * o formulário só fecha depois do sucesso.
 */
function DadosForm({
  data,
  onClose,
  onSaved,
}: {
  data: EventoDetalhe;
  onClose: () => void;
  onSaved: (warnings: string[]) => void;
}) {
  const salvar = useUpdateEventBasics(data.event.id);
  const [form, setForm] = useState<EventBasicsInput>(() => valoresIniciais(data));
  const [erros, setErros] = useState<Record<string, string>>({});
  // A descrição chega do Google Agenda como HTML (`<br>`, âncoras). O textarea mostra a versão
  // legível em texto puro, mas enviar essa conversão de volta achataria o HTML original —
  // e o achatamento seria empurrado para o Google no próximo sync. Então só mandamos o texto
  // digitado se o usuário realmente mexeu no campo; caso contrário vai o HTML intacto.
  const [descricaoTocada, setDescricaoTocada] = useState(false);

  const set = <K extends keyof EventBasicsInput>(key: K, value: EventBasicsInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const tipoAtual = data.event.event_type;
  const tipos = EVENT_TYPES.some((t) => t.value === tipoAtual)
    ? EVENT_TYPES
    : [...EVENT_TYPES, { value: tipoAtual, label: tipoAtual }].filter((t) => t.value);

  const submit = () => {
    setErros({});
    const payload: EventBasicsInput = {
      ...form,
      description: descricaoTocada ? form.description : (data.event.description ?? ""),
    };
    salvar.mutate(payload, {
      onSuccess: (updated) => {
        onClose();
        onSaved(updated.warnings ?? []);
      },
      onError: (error) => {
        setErros(error instanceof ApiRequestError ? (error.fields ?? {}) : {});
      },
    });
  };

  return (
    <div className="space-y-3">
      <div>
        <label className={LABEL_CLASS} htmlFor="resumo-title">
          Título
        </label>
        <input
          id="resumo-title"
          className={INPUT_CLASS}
          value={form.title}
          onChange={(e) => set("title", e.target.value)}
        />
        {erros.title && <p className="mt-1 text-sm text-red">{erros.title}</p>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL_CLASS} htmlFor="resumo-tipo">
            Tipo
          </label>
          <select
            id="resumo-tipo"
            className={INPUT_CLASS}
            value={form.event_type}
            onChange={(e) => set("event_type", e.target.value)}
          >
            <option value="">— Selecionar —</option>
            {tipos.map((tipo) => (
              <option key={tipo.value} value={tipo.value}>
                {tipo.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={LABEL_CLASS} htmlFor="resumo-data">
            Data
          </label>
          <input
            id="resumo-data"
            type="date"
            className={INPUT_CLASS}
            value={form.date}
            onChange={(e) => set("date", e.target.value)}
          />
          {erros.event_date && <p className="mt-1 text-sm text-red">{erros.event_date}</p>}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL_CLASS} htmlFor="resumo-inicio">
            Início
          </label>
          <input
            id="resumo-inicio"
            type="time"
            className={INPUT_CLASS}
            value={form.start}
            onChange={(e) => set("start", e.target.value)}
          />
        </div>
        <div>
          <label className={LABEL_CLASS} htmlFor="resumo-fim">
            Fim
          </label>
          <input
            id="resumo-fim"
            type="time"
            className={INPUT_CLASS}
            value={form.end}
            onChange={(e) => set("end", e.target.value)}
          />
        </div>
      </div>
      {erros.event_time && <p className="text-sm text-red">{erros.event_time}</p>}

      <div>
        <label className={LABEL_CLASS} htmlFor="resumo-local">
          Local
        </label>
        <GoogleAddressInput
          id="resumo-local"
          aria-label="Local do evento"
          placeholder="Endereço do evento"
          value={form.location}
          onChange={(value) => set("location", value)}
        />
      </div>

      <div>
        <label className={LABEL_CLASS} htmlFor="resumo-descricao">
          Descrição
        </label>
        <textarea
          id="resumo-descricao"
          rows={4}
          className="w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
          value={form.description}
          onChange={(e) => {
            setDescricaoTocada(true);
            set("description", e.target.value);
          }}
        />
        <p className="mt-1 text-xs text-muted">
          É o mesmo texto que vai para o Google Agenda. Sem edição aqui, a formatação original é
          preservada.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button loading={salvar.isPending} onClick={submit}>
          Salvar dados
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={salvar.isPending}>
          Cancelar
        </Button>
        {salvar.isError && Object.keys(erros).length === 0 && (
          <span className="text-sm text-red">{salvar.error?.message}</span>
        )}
      </div>
    </div>
  );
}

/**
 * Leitura dos dados do evento — o estado padrão do painel.
 *
 * A descrição **não** entra aqui de propósito: ela já é o painel "Resumo para WhatsApp" ao lado,
 * onde tem fonte monoespaçada e botão de copiar. Repeti-la aqui era justamente o tipo de
 * duplicação (o mesmo conteúdo em dois lugares da mesma tela) que a 215 veio desfazer — e é o
 * bloco mais longo da tela, então duplicá-lo dobrava a altura do Resumo.
 */
function DadosLeitura({ data }: { data: EventoDetalhe }) {
  const event = data.event;
  return (
    <div className="divide-y divide-line">
      <DataRow label="Tipo">{event.event_type || "—"}</DataRow>
      <DataRow label="Data">{formatDay(event.start_at) || "—"}</DataRow>
      <DataRow label="Horário">
        {[formatTime(event.start_at), formatTime(event.end_at)].filter(Boolean).join(" — ") || "—"}
      </DataRow>
      <DataRow label="Local">{event.location || "—"}</DataRow>
      {event.description && (
        <DataRow label="Descrição">
          <span className="text-muted">no painel “Resumo para WhatsApp”</span>
        </DataRow>
      )}
    </div>
  );
}

/**
 * Painel "Dados do evento" da aba Resumo (feature 215).
 *
 * Antes, mudar o horário de um evento exigia sair da tela para o formulário de edição em
 * bloco. Aqui o mesmo dado é editado onde é exibido — o formulário grande continua acessível
 * pelo menu Ferramentas, para quem quiser mexer em elenco e clientes de uma vez.
 */
export function DadosEventoPanel({ data }: { data: EventoDetalhe }) {
  const [editando, setEditando] = useState(false);
  const [avisos, setAvisos] = useState<string[]>([]);
  const canEdit = Boolean(data.flags.can_edit_core);

  return (
    <>
      {avisos.length > 0 && <AvisosCard avisos={avisos} onFechar={() => setAvisos([])} />}
      <Panel
        title="Dados do evento"
        actions={
          canEdit && !editando ? (
            <Button variant="outline" size="sm" onClick={() => setEditando(true)}>
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              Editar
            </Button>
          ) : null
        }
      >
        {editando ? (
          <DadosForm
            data={data}
            onClose={() => setEditando(false)}
            onSaved={(warnings) => setAvisos(warnings)}
          />
        ) : (
          <DadosLeitura data={data} />
        )}
      </Panel>
    </>
  );
}

/** Uma pendência calculada: rótulo, estado e a aba onde ela se resolve. */
interface Pendencia {
  key: string;
  label: string;
  valor: string;
  ok: boolean;
  tab: string;
}

/** Monta a lista de pendências a partir do que o RBAC deixou no payload. */
function calcularPendencias(data: EventoDetalhe): Pendencia[] {
  const lista: Pendencia[] = [];
  const roles = data.elenco ?? [];
  const personagens = roles.filter((r) => r.role_type !== "extra");

  if (data.flags.show_casting || data.flags.show_figurino) {
    const escalados = roles.filter((r) => r.talent && !r.dismissed).length;
    const vagas = roles.filter((r) => !r.dismissed).length;
    lista.push({
      key: "casting",
      label: "Elenco",
      valor: `${escalados}/${vagas} escalados`,
      ok: vagas > 0 && escalados === vagas,
      tab: "producao",
    });

    const confirmados = roles.filter((r) => r.invite_status === "accepted").length;
    if (vagas > 0) {
      lista.push({
        key: "convites",
        label: "Presença",
        valor: `${confirmados}/${vagas} confirmadas`,
        ok: confirmados === vagas,
        tab: "producao",
      });
    }
  }

  if (data.flags.show_figurino && personagens.length > 0) {
    const comFicha = personagens.filter((r) => r.figurino_sheet_id).length;
    lista.push({
      key: "figurino",
      label: "Figurino",
      valor: `${comFicha}/${personagens.length} com ficha`,
      ok: comFicha === personagens.length,
      tab: "producao",
    });
  }

  const conflitos = roles.filter((r) => r.availability?.status === "conflict").length;
  if (conflitos > 0) {
    lista.push({
      key: "conflitos",
      label: "Agenda",
      valor: `${conflitos} com conflito`,
      ok: false,
      tab: "producao",
    });
  }

  if (data.contratos) {
    const assinado = data.contratos.some((c) => c.is_signed);
    lista.push({
      key: "contrato",
      label: "Contrato",
      valor: data.contratos.length === 0 ? "não anexado" : assinado ? "assinado" : "sem assinatura",
      ok: assinado,
      tab: "comercial",
    });
  }

  if (data.cobranca) {
    const aberto = data.cobranca.outstanding ?? 0;
    lista.push({
      key: "cobranca",
      label: "Recebimento",
      valor: aberto > 0 ? `${brl(aberto)} em aberto` : "quitado",
      ok: aberto <= 0,
      tab: "comercial",
    });
  }

  if (data.flags.can_confirm) {
    lista.push({
      key: "confirmado",
      label: "Evento",
      valor: data.event.confirmed ? "confirmado" : "não confirmado",
      ok: data.event.confirmed,
      tab: "resumo",
    });
  }

  return lista;
}

export interface PendenciasStripProps {
  data: EventoDetalhe;
  /** Leva para a aba onde a pendência se resolve — o chip é atalho, não só enfeite. */
  onNavigate: (tab: string) => void;
}

/**
 * Faixa de pendências do evento (feature 215) — a resposta imediata a "falta o quê aqui?".
 *
 * Cada chip resume um estado que antes só existia enterrado em algum dos 16 painéis da tela
 * antiga, e clicar leva para a aba que resolve aquilo. O que o RBAC não mandou no payload
 * simplesmente não vira chip — a tela nunca adivinha permissão por conta própria.
 */
export function PendenciasStrip({ data, onNavigate }: PendenciasStripProps) {
  const pendencias = calcularPendencias(data);
  if (pendencias.length === 0) return null;

  return (
    <div className="-mx-4 mb-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <ul className="flex min-w-max items-center gap-2 sm:min-w-0 sm:flex-wrap">
        {pendencias.map((p) => (
          <li key={p.key}>
            <button
              type="button"
              onClick={() => onNavigate(p.tab)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
                p.ok
                  ? "border-green/40 bg-green-soft/40 text-green hover:bg-green-soft"
                  : "border-gold/50 bg-gold-soft/40 text-ink hover:bg-gold-soft"
              }`}
            >
              <span aria-hidden="true">{p.ok ? "✓" : "●"}</span>
              <span className="font-semibold uppercase tracking-wide">{p.label}</span>
              <span className="text-muted">{p.valor}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Selo de confirmação do evento, reaproveitado no cabeçalho da aba Resumo. */
export function ConfirmadoBadge({ data }: { data: EventoDetalhe }) {
  if (!data.event.confirmed) return null;
  return (
    <Badge tone="green">
      ✓ Confirmado{data.event.confirmed_by ? ` por ${data.event.confirmed_by}` : ""}
    </Badge>
  );
}
