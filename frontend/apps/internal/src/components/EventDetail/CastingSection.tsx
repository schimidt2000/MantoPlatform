import { useState } from "react";
import { AvatarThumb, Badge, Button } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import type { EventoDetalhe, PaymentStatus, RoleItem } from "../../lib/agenda";
import {
  useAddRole,
  useAssignRole,
  useDeleteRole,
  useDismissRole,
  useRestoreRole,
  useSendInvite,
} from "../../lib/casting";
import { buildConviteMsg, useSetPaymentStatus } from "../../lib/eventDetail";
import { brl, Empty, formatDay, formatTime, INPUT_CLASS, Panel } from "./parts";
import { TalentPicker } from "./TalentPicker";

const PAYMENT_LABELS: Record<PaymentStatus, string> = {
  nao_pago: "A pagar",
  pago: "Pago",
  no_banco: "No banco",
  fora_do_banco: "Fora do banco",
};

const INVITE_LABELS: Record<string, { text: string; tone: "green" | "gold" | "red" }> = {
  accepted: { text: "✓ Presença confirmada", tone: "green" },
  pending: { text: "⏳ Aguardando", tone: "gold" },
  rejected: { text: "✕ Recusado", tone: "red" },
};

/** Badge de atenção quando o talento tem outro compromisso na mesma data. */
function AvailabilityBadge({ role }: { role: RoleItem }) {
  const availability = role.availability;
  if (!availability || availability.status === "free") return null;
  const isConflict = availability.status === "conflict";
  return (
    <Badge tone={isConflict ? "red" : "gold"} className="max-w-full truncate">
      <span title={availability.info}>{isConflict ? "● Conflito" : "● Mesmo dia"}</span>
    </Badge>
  );
}

/** Seletor do status de pagamento do cachê — some para quem não pode editar o evento. */
function PaymentStatusSelect({
  role,
  eventId,
  canEdit,
}: {
  role: RoleItem;
  eventId: number;
  canEdit: boolean;
}) {
  const setStatus = useSetPaymentStatus(eventId);
  if (!role.talent) return null;
  if (!canEdit) {
    return (
      <Badge tone={role.payment_status === "pago" ? "green" : "neutral"}>
        {PAYMENT_LABELS[role.payment_status]}
      </Badge>
    );
  }
  return (
    <label className="inline-flex items-center gap-1.5">
      <span className="sr-only">Status de pagamento de {role.character_name}</span>
      <select
        className={`h-8 rounded-md border px-1.5 text-xs ${
          role.payment_status === "pago"
            ? "border-green bg-green-soft text-green"
            : "border-line bg-panel text-ink"
        }`}
        value={role.payment_status}
        disabled={setStatus.isPending}
        onChange={(e) =>
          setStatus.mutate({ roleId: role.role_id, payment_status: e.target.value as PaymentStatus })
        }
      >
        {(Object.keys(PAYMENT_LABELS) as PaymentStatus[]).map((status) => (
          <option key={status} value={status}>
            {PAYMENT_LABELS[status]}
          </option>
        ))}
      </select>
      {setStatus.isPending && <span className="text-xs text-muted">Salvando…</span>}
    </label>
  );
}

/** Botão que copia a mensagem de convite do talento, com retorno visível no próprio botão. */
function CopyInviteButton({ role, data }: { role: RoleItem; data: EventoDetalhe }) {
  const [copied, setCopied] = useState(false);
  if (!role.talent) return null;

  const copy = async () => {
    const event = data.event;
    const texto = buildConviteMsg(
      role,
      {
        title: event.title,
        dateLabel: formatDay(event.start_at),
        timeLabel: [formatTime(event.start_at), formatTime(event.end_at)]
          .filter(Boolean)
          .join(" - "),
        location: event.location,
        makeupTime: event.makeup_time,
        makeupLocation: event.makeup_location,
      },
      role.cache_value ? `R$ ${formatBRL(role.cache_value)}` : "",
    );
    try {
      await navigator.clipboard.writeText(texto);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard bloqueado (contexto não seguro) — nada a fazer além de não travar a tela.
    }
  };

  return (
    <Button variant="ghost" size="sm" onClick={copy}>
      {copied ? "✓ Copiado" : "📋 Copiar convite"}
    </Button>
  );
}

interface RoleCardProps {
  role: RoleItem;
  data: EventoDetalhe;
  canEdit: boolean;
}

/**
 * Card de um cargo escalado — nome do personagem, talento, cachê e as ações inline
 * (convite, WhatsApp, status de pagamento, remover). Cada mutação coloca só o seu botão em
 * "Salvando…", nunca a tela inteira (Princípio V).
 *
 * No mobile o card vira uma pilha de linhas inteiras (`sm:` reabre em linha); a busca de
 * talento ocupa a largura toda e o cachê fica ao lado do botão Salvar — nada de campo de
 * 40px espremido entre botões.
 */
function RoleCard({ role, data, canEdit }: RoleCardProps) {
  const eventId = data.event.id;
  const assign = useAssignRole(eventId);
  const remove = useDeleteRole(eventId);
  const invite = useSendInvite(eventId);
  const dismiss = useDismissRole(eventId);
  const restore = useRestoreRole(eventId);
  const [talentId, setTalentId] = useState<number | null>(role.talent?.id ?? null);
  const [cache, setCache] = useState<number>(role.cache_value ?? 0);

  const inviteInfo = role.invite_status ? INVITE_LABELS[role.invite_status] : undefined;
  const alerta = role.availability && role.availability.status !== "free";
  const cacheAlterado = cache !== (role.cache_value ?? 0);
  const sujo = talentId !== (role.talent?.id ?? null) || cacheAlterado;

  /**
   * Teto de cachê do orçamento (`cache_cap`, gravado na criação quando o evento nasce da
   * calculadora). O **valor** do teto é deliberadamente invisível — o casting não negocia
   * contra um número exposto na tela; o que ele precisa saber é só que passou dele.
   *
   * Sem este aviso, `assign_casting_role` rebaixava o valor para o teto em silêncio: quem
   * digitava acima via "✓ Salvo" e o número voltava sozinho, sem explicação (a tela Jinja
   * antiga avisava; a migração para o React perdeu isso).
   */
  // Feature 238: o teto efetivo considera o valor JÁ salvo no papel — se um superadmin o
  // subiu acima do cap, o casting pode usar até ele (o servidor aplica a mesma regra).
  const tetoEfetivo =
    role.cache_cap != null ? Math.max(role.cache_cap, role.cache_value ?? 0) : null;
  const acimaDoTeto = tetoEfetivo != null && cache > tetoEfetivo;
  const podeUltrapassar = Boolean(data.flags.is_superadmin);

  return (
    <li
      className={`rounded-md border p-3 ${
        alerta ? "border-gold bg-gold-soft/20" : "border-line bg-surface-2/40"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <AvatarThumb
          src={role.talent?.photo_url ? assetUrl(role.talent.photo_url) : null}
          name={role.talent?.name}
          shape="circle"
          size="lg"
          fallbackIcon="🎭"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-bold uppercase tracking-wide text-ink">
              {role.character_name}
            </span>
            {role.dismissed && <Badge>dispensado</Badge>}
            <AvailabilityBadge role={role} />
            {inviteInfo && (
              <Badge tone={inviteInfo.tone} className="sm:ml-auto">
                {inviteInfo.text}
              </Badge>
            )}
          </div>
          <div className="text-sm text-muted">
            {role.talent ? role.talent.name : "— sem talento —"}
          </div>
          <div className="text-xs text-muted">
            {role.assigned_at && <span>Atribuído em {formatDay(role.assigned_at)}</span>}
            {role.cache_value != null && (
              <span className="ml-2 tabular-nums">Cachê: {brl(role.cache_value)}</span>
            )}
          </div>
        </div>
      </div>

      {canEdit && (
        <div className="mt-2 space-y-2 sm:flex sm:items-center sm:gap-2 sm:space-y-0">
          <TalentPicker
            className="sm:min-w-48 sm:flex-1"
            eventId={eventId}
            value={talentId}
            onChange={setTalentId}
            ariaLabel={`Talento de ${role.character_name}`}
          />
          <div className="flex items-center gap-2">
            <MoneyInput
              // Vermelho só enquanto o valor está pendente de decisão: um cachê acima do teto
              // que já foi gravado (autorizado pelo admin) é um estado legítimo, não um erro
              // — quem abre o card depois não pode ver o campo em alerta permanente.
              className={`h-11 w-28 rounded-md border bg-panel px-2 text-sm text-ink ${
                acimaDoTeto && cacheAlterado ? "border-red" : "border-line"
              }`}
              value={cache}
              onValueChange={setCache}
              aria-label={`Cachê de ${role.character_name}`}
              aria-invalid={(acimaDoTeto && cacheAlterado) || undefined}
            />
            <Button
              className="h-11 flex-1 sm:h-9 sm:flex-none"
              size="sm"
              variant={sujo ? "default" : "outline"}
              loading={assign.isPending}
              onClick={() =>
                assign.mutate(
                  { roleId: role.role_id, talent_id: talentId, cache_value: cache },
                  {
                    // O servidor rebaixa o cachê ao teto quando quem salva não é superadmin.
                    // Sem reespelhar o valor devolvido, o campo continuaria exibindo o número
                    // recusado — a tela diria uma coisa e o banco teria outra.
                    onSuccess: (atualizado) => {
                      const salvo = (atualizado.elenco ?? []).find(
                        (r) => r.role_id === role.role_id,
                      );
                      if (salvo) setCache(salvo.cache_value ?? 0);
                    },
                  },
                )
              }
            >
              {assign.isSuccess && !sujo ? "✓ Salvo" : "Salvar"}
            </Button>
          </div>
        </div>
      )}

      {canEdit && acimaDoTeto && (
        <p
          role="status"
          className={`mt-1.5 text-sm ${cacheAlterado ? "text-red" : "text-muted"}`}
        >
          {!cacheAlterado
            ? "Cachê autorizado acima do limite deste evento."
            : podeUltrapassar
              ? "Acima do limite deste evento. Como superadmin você pode salvar assim mesmo — fica registrado no log."
              : "Acima do limite deste evento. Ao salvar, o valor volta para o limite."}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <PaymentStatusSelect role={role} eventId={eventId} canEdit={canEdit} />
        {canEdit && role.talent && (
          <>
            <Button
              variant="ghost"
              size="sm"
              loading={invite.isPending}
              onClick={() => invite.mutate(role.role_id)}
            >
              {role.invite_status === "pending" ? "Reenviar convite" : "Convidar"}
            </Button>
            <CopyInviteButton role={role} data={data} />
          </>
        )}
        {role.talent?.whatsapp && (
          <Button asChild variant="ghost" size="sm">
            <a
              href={`https://wa.me/${role.talent.whatsapp}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              📱 WhatsApp
            </a>
          </Button>
        )}
        {canEdit && data.flags.is_superadmin && !role.talent && (
          <Button
            variant="ghost"
            size="sm"
            loading={role.dismissed ? restore.isPending : dismiss.isPending}
            onClick={() =>
              role.dismissed ? restore.mutate(role.role_id) : dismiss.mutate(role.role_id)
            }
          >
            {role.dismissed ? "Restaurar" : "Dispensar"}
          </Button>
        )}
        {canEdit && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto text-red"
            loading={remove.isPending}
            onClick={() => {
              const aviso =
                role.invite_status === "accepted"
                  ? " Atenção: a presença já foi confirmada."
                  : "";
              if (window.confirm(`Remover a vaga "${role.character_name}"?${aviso}`)) {
                remove.mutate(role.role_id);
              }
            }}
          >
            Remover vaga
          </Button>
        )}
      </div>

      {assign.isError && (
        <p className="mt-1 text-sm text-red">Não foi possível salvar. Tente novamente.</p>
      )}
      {remove.isError && <p className="mt-1 text-sm text-red">{remove.error?.message}</p>}
    </li>
  );
}

/** Formulário de adicionar cargo (personagem ou apoio, conforme `roleType`). */
function AddRoleForm({
  eventId,
  roleType,
  label,
}: {
  eventId: number;
  roleType: "character" | "extra";
  label: string;
}) {
  const add = useAddRole(eventId);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [talentId, setTalentId] = useState<number | null>(null);
  const [cache, setCache] = useState(0);

  if (!open) {
    return (
      <Button variant="outline" size="sm" className="mt-3" onClick={() => setOpen(true)}>
        + {label}
      </Button>
    );
  }

  const submit = () => {
    if (!name.trim()) return;
    add.mutate(
      {
        character_name: name.trim(),
        talent_id: talentId,
        cache_value: cache,
        role_type: roleType,
      },
      {
        onSuccess: () => {
          setName("");
          setTalentId(null);
          setCache(0);
          setOpen(false);
        },
      },
    );
  };

  return (
    <div className="mt-3 space-y-2 rounded-md border border-line bg-surface-2/60 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          className={`${INPUT_CLASS} sm:min-w-40 sm:flex-1`}
          placeholder={roleType === "character" ? "Personagem" : "Função (ex.: Coordenador)"}
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label="Nome do cargo"
        />
        <TalentPicker
          className="sm:min-w-48 sm:flex-1"
          eventId={eventId}
          value={talentId}
          onChange={setTalentId}
          ariaLabel="Talento do novo cargo"
        />
      </div>
      <div className="flex items-center gap-2">
        <MoneyInput
          className="h-11 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={cache}
          onValueChange={setCache}
          aria-label="Cachê"
        />
        <Button
          className="h-11 flex-1 sm:h-9 sm:flex-none"
          size="sm"
          loading={add.isPending}
          disabled={!name.trim()}
          onClick={submit}
        >
          Adicionar
        </Button>
        <Button
          className="h-11 sm:h-9"
          variant="ghost"
          size="sm"
          onClick={() => setOpen(false)}
        >
          Cancelar
        </Button>
      </div>
      {add.isError && <p className="text-sm text-red">Não foi possível adicionar.</p>}
    </div>
  );
}

export interface CastingSectionProps {
  data: EventoDetalhe;
}

/**
 * Casting e equipe de apoio (feature 190). São duas listas com a mesma anatomia de card,
 * separadas por `role_type`: personagens do evento (`character`) e funções de suporte
 * (`extra` — coordenação, técnico de som, maquiagem).
 */
export function CastingSection({ data }: CastingSectionProps) {
  const canEdit = Boolean(data.flags.show_casting);
  const roles = data.elenco ?? [];
  const personagens = roles.filter((r) => r.role_type !== "extra");
  const apoio = roles.filter((r) => r.role_type === "extra");
  const comAlerta = roles.filter((r) => r.availability && r.availability.status !== "free");

  const renderList = (items: RoleItem[]) =>
    items.length === 0 ? (
      <Empty>Nenhum cargo cadastrado.</Empty>
    ) : (
      <ul className="space-y-2">
        {items.map((role) => (
          <RoleCard key={role.role_id} role={role} data={data} canEdit={canEdit} />
        ))}
      </ul>
    );

  return (
    <>
      <Panel
        title="Casting"
        actions={
          comAlerta.length > 0 ? (
            <Badge tone="gold" className="whitespace-nowrap">
              {comAlerta.length} com conflito de agenda
            </Badge>
          ) : null
        }
      >
        {renderList(personagens)}
        {canEdit && (
          <AddRoleForm
            eventId={data.event.id}
            roleType="character"
            label="Adicionar personagem"
          />
        )}
      </Panel>

      <Panel title="Equipe de apoio">
        {renderList(apoio)}
        {canEdit && (
          <AddRoleForm eventId={data.event.id} roleType="extra" label="Adicionar pessoa" />
        )}
      </Panel>
    </>
  );
}
