import { useState, type ReactNode } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { useEvent, type EventoDetalhe, type RoleItem } from "../lib/agenda";
import {
  useAddRole,
  useAssignRole,
  useDeleteRole,
  useDismissRole,
  useRestoreRole,
  useSendInvite,
  useSetFigurinoDone,
  useTalents,
  type TalentoOption,
} from "../lib/casting";
import { useSaveLogistics, useToggleConfirm } from "../lib/eventOps";

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function makeupLocationLabel(loc: string | null): string {
  if (!loc) return "";
  if (loc === "manto") return "Manto Produções";
  if (loc === "local") return "Local do evento";
  return loc;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

/** Botão "marcar figurino" — visível a Figurino/superadmin, só se há talento e ainda não separado. */
function FigurinoButton({
  role,
  eventId,
  show,
}: {
  role: RoleItem;
  eventId: number;
  show: boolean;
}) {
  const figurino = useSetFigurinoDone(eventId);
  if (!show || !role.talent || role.figurino_done) return null;
  return (
    <Button
      variant="ghost"
      size="sm"
      loading={figurino.isPending}
      onClick={() => figurino.mutate(role.role_id)}
    >
      Marcar figurino
    </Button>
  );
}

function RoleReadRow({
  role,
  eventId,
  showFigurino,
}: {
  role: RoleItem;
  eventId: number;
  showFigurino: boolean;
}) {
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <div>
        <div className="font-medium text-ink">{role.character_name}</div>
        <div className="text-sm text-muted">
          {role.talent ? role.talent.name : "— sem talento —"}
          {role.figurino_done && " · figurino ok"}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <FigurinoButton role={role} eventId={eventId} show={showFigurino} />
        {role.cache_value != null && (
          <span className="tabular-nums text-sm text-ink">{brl(role.cache_value)}</span>
        )}
      </div>
    </li>
  );
}

function RoleAssignRow({
  role,
  eventId,
  talents,
  showFigurino,
  isSuperadmin,
}: {
  role: RoleItem;
  eventId: number;
  talents: TalentoOption[];
  showFigurino: boolean;
  isSuperadmin: boolean;
}) {
  const assign = useAssignRole(eventId);
  const remove = useDeleteRole(eventId);
  const invite = useSendInvite(eventId);
  const dismiss = useDismissRole(eventId);
  const restore = useRestoreRole(eventId);
  const [talentId, setTalentId] = useState<number | null>(role.talent?.id ?? null);
  const [cache, setCache] = useState<number>(role.cache_value ?? 0);

  return (
    <li className="py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-medium text-ink">
          {role.character_name}
          {role.dismissed && (
            <span className="ml-2 rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
              dispensado
            </span>
          )}
        </span>
        <div className="flex items-center gap-2">
          {role.invite_status && (
            <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
              {role.invite_status}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            loading={remove.isPending}
            onClick={() => {
              if (window.confirm(`Remover o cargo "${role.character_name}"?`)) {
                remove.mutate(role.role_id);
              }
            }}
            aria-label={`Remover ${role.character_name}`}
          >
            ✕
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={talentId ?? ""}
          onChange={(e) => setTalentId(e.target.value ? Number(e.target.value) : null)}
          aria-label="Talento"
        >
          <option value="">— sem talento —</option>
          {talents.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <MoneyInput
          className="h-11 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={cache}
          onValueChange={setCache}
          aria-label="Cachê"
        />
        <Button
          size="sm"
          loading={assign.isPending}
          onClick={() =>
            assign.mutate({ roleId: role.role_id, talent_id: talentId, cache_value: cache })
          }
        >
          Salvar
        </Button>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {role.talent && (
          <Button
            variant="ghost"
            size="sm"
            loading={invite.isPending}
            onClick={() => invite.mutate(role.role_id)}
          >
            Reenviar convite
          </Button>
        )}
        <FigurinoButton role={role} eventId={eventId} show={showFigurino} />
        {isSuperadmin && !role.talent && (
          role.dismissed ? (
            <Button
              variant="ghost"
              size="sm"
              loading={restore.isPending}
              onClick={() => restore.mutate(role.role_id)}
            >
              Restaurar
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              loading={dismiss.isPending}
              onClick={() => dismiss.mutate(role.role_id)}
            >
              Dispensar
            </Button>
          )
        )}
      </div>
      {assign.isError && (
        <p className="mt-1 text-sm text-red">Não foi possível salvar. Tente novamente.</p>
      )}
    </li>
  );
}

function AddRoleForm({ eventId, talents }: { eventId: number; talents: TalentoOption[] }) {
  const add = useAddRole(eventId);
  const [name, setName] = useState("");
  const [talentId, setTalentId] = useState<number | null>(null);
  const [cache, setCache] = useState<number>(0);

  const submit = () => {
    if (!name.trim()) return;
    add.mutate(
      { character_name: name.trim(), talent_id: talentId, cache_value: cache },
      {
        onSuccess: () => {
          setName("");
          setTalentId(null);
          setCache(0);
        },
      },
    );
  };

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="mb-2 text-sm font-medium text-muted">Adicionar cargo</div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Personagem / função"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label="Nome do personagem"
        />
        <select
          className="h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={talentId ?? ""}
          onChange={(e) => setTalentId(e.target.value ? Number(e.target.value) : null)}
          aria-label="Talento"
        >
          <option value="">— sem talento —</option>
          {talents.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <MoneyInput
          className="h-11 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={cache}
          onValueChange={setCache}
          aria-label="Cachê"
        />
        <Button size="sm" loading={add.isPending} disabled={!name.trim()} onClick={submit}>
          Adicionar
        </Button>
      </div>
      {add.isError && <p className="mt-1 text-sm text-red">Não foi possível adicionar.</p>}
    </div>
  );
}

function Elenco({ data }: { data: EventoDetalhe }) {
  const talentsQuery = useTalents();
  const showFigurino = Boolean(data.flags.show_figurino);
  const isSuperadmin = Boolean(data.flags.is_superadmin);
  const canEdit = Boolean(data.flags.show_casting) && Boolean(talentsQuery.data);
  const hasRoles = Boolean(data.elenco && data.elenco.length > 0);
  if (!hasRoles && !canEdit) return null;
  return (
    <Section title="Elenco">
      <ul className="divide-y divide-line">
        {(data.elenco ?? []).map((r) =>
          canEdit ? (
            <RoleAssignRow
              key={r.role_id}
              role={r}
              eventId={data.event.id}
              talents={talentsQuery.data!.items}
              showFigurino={showFigurino}
              isSuperadmin={isSuperadmin}
            />
          ) : (
            <RoleReadRow
              key={r.role_id}
              role={r}
              eventId={data.event.id}
              showFigurino={showFigurino}
            />
          ),
        )}
      </ul>
      {canEdit && <AddRoleForm eventId={data.event.id} talents={talentsQuery.data!.items} />}
    </Section>
  );
}

function Venda({ data }: { data: EventoDetalhe }) {
  if (!data.venda) return null;
  const v = data.venda;
  return (
    <Section title="Venda">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <dt className="text-muted">Valor</dt>
        <dd className="tabular-nums text-ink">{brl(v.sale_value)}</dd>
        {v.seller && (
          <>
            <dt className="text-muted">Vendedor</dt>
            <dd className="text-ink">{v.seller}</dd>
          </>
        )}
        {v.payment_method && (
          <>
            <dt className="text-muted">Pagamento</dt>
            <dd className="text-ink">{v.payment_method}</dd>
          </>
        )}
        {v.clients.length > 0 && (
          <>
            <dt className="text-muted">Cliente(s)</dt>
            <dd className="text-ink">
              {v.clients.map((c) => c.name).filter(Boolean).join(", ")}
            </dd>
          </>
        )}
      </dl>
    </Section>
  );
}

function Kpi({ data }: { data: EventoDetalhe }) {
  if (!data.kpi) return null;
  const k = data.kpi;
  const items: [string, string][] = [
    ["Venda", brl(k.sale_value)],
    ["Cachês", brl(k.cost)],
    ["Comissão", brl(k.commission)],
    ["Lucro", brl(k.lucro)],
  ];
  return (
    <Section title={`Financeiro${k.group_size > 1 ? ` (grupo de ${k.group_size})` : ""}`}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map(([label, value]) => (
          <div key={label}>
            <div className="text-xs text-muted">{label}</div>
            <div className="tabular-nums text-lg font-semibold text-ink">{value}</div>
          </div>
        ))}
      </div>
    </Section>
  );
}

function Pagamentos({ data }: { data: EventoDetalhe }) {
  if (!data.pagamentos) return null;
  const p = data.pagamentos;
  return (
    <Section title="Pagamentos">
      <p className="mb-2 text-sm text-muted">
        Recebido: <span className="tabular-nums text-ink">{brl(p.received_total)}</span>
      </p>
      {p.items.length === 0 ? (
        <p className="text-sm text-muted">Nenhum pagamento registrado.</p>
      ) : (
        <ul className="divide-y divide-line">
          {p.items.map((it) => (
            <li key={it.id} className="flex justify-between py-1.5 text-sm">
              <span className="text-muted">{formatDate(it.created_at)}</span>
              <span className="tabular-nums text-ink">{brl(it.amount)}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function Reembolsos({ data }: { data: EventoDetalhe }) {
  if (!data.reembolsos || data.reembolsos.items.length === 0) return null;
  const r = data.reembolsos;
  return (
    <Section title="Reembolsos">
      <p className="mb-2 text-sm text-muted">
        Pendente: <span className="tabular-nums text-ink">{brl(r.pendentes_total)}</span>
      </p>
      <ul className="divide-y divide-line">
        {r.items.map((it) => (
          <li key={it.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
            <span className="text-ink">
              {it.description}
              {it.is_collected && <span className="text-green"> · cobrado</span>}
            </span>
            <span className="tabular-nums text-ink">{brl(it.amount)}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

/** Toggle de confirmação do evento (feature 149). Comercial/SA vê o botão; os demais, só o badge. */
function ConfirmControl({ data }: { data: EventoDetalhe }) {
  const toggle = useToggleConfirm(data.event.id);
  const { confirmed, confirmed_by } = data.event;
  if (!data.flags.can_confirm) {
    return confirmed ? (
      <span className="rounded-md bg-green-soft px-2 py-0.5 text-xs text-green">Confirmado</span>
    ) : null;
  }
  return (
    <span className="inline-flex items-center gap-2">
      <Button
        variant={confirmed ? "outline" : "default"}
        size="sm"
        loading={toggle.isPending}
        onClick={() => toggle.mutate()}
      >
        {confirmed ? "✓ Confirmado — desfazer" : "Confirmar evento"}
      </Button>
      {confirmed && confirmed_by && <span className="text-xs text-muted">por {confirmed_by}</span>}
    </span>
  );
}

const LOGISTICS_INPUT =
  "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Editor de logística (maquiagem/saída/precisa-ensaio) para quem pode editar o evento. */
function LogisticaEdit({ data }: { data: EventoDetalhe }) {
  const save = useSaveLogistics(data.event.id);
  const ev = data.event;
  const initLoc = ev.makeup_location;
  const isPreset = initLoc === "manto" || initLoc === "local";
  const [makeupTime, setMakeupTime] = useState(ev.makeup_time ?? "");
  const [makeupSel, setMakeupSel] = useState<string>(isPreset ? initLoc! : initLoc ? "outro" : "manto");
  const [makeupCustom, setMakeupCustom] = useState(!isPreset && initLoc ? initLoc : "");
  const [departureTime, setDepartureTime] = useState(ev.departure_time ?? "");
  const [departureLocation, setDepartureLocation] = useState(ev.departure_location ?? "Manto Produções");
  const [needsRehearsal, setNeedsRehearsal] = useState(ev.needs_rehearsal);

  const submit = () =>
    save.mutate({
      makeup_time: makeupTime,
      makeup_location: makeupSel === "outro" ? makeupCustom.trim() : makeupSel,
      departure_time: departureTime,
      departure_location: departureLocation,
      needs_rehearsal: needsRehearsal,
    });

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Horário de maquiagem</span>
          <input
            type="time"
            className={LOGISTICS_INPUT}
            value={makeupTime}
            onChange={(e) => setMakeupTime(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Local de maquiagem</span>
          <select
            className={LOGISTICS_INPUT}
            value={makeupSel}
            onChange={(e) => setMakeupSel(e.target.value)}
          >
            <option value="manto">Manto Produções</option>
            <option value="local">Local do evento</option>
            <option value="outro">Outro endereço…</option>
          </select>
        </label>
      </div>
      {makeupSel === "outro" && (
        <input
          type="text"
          className={LOGISTICS_INPUT}
          placeholder="Endereço da maquiagem"
          value={makeupCustom}
          onChange={(e) => setMakeupCustom(e.target.value)}
          aria-label="Endereço da maquiagem"
        />
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Horário de saída</span>
          <input
            type="time"
            className={LOGISTICS_INPUT}
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm text-muted">Local de saída</span>
          <input
            type="text"
            className={LOGISTICS_INPUT}
            value={departureLocation}
            onChange={(e) => setDepartureLocation(e.target.value)}
          />
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={needsRehearsal}
          onChange={(e) => setNeedsRehearsal(e.target.checked)}
        />
        Precisa de ensaio
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" loading={save.isPending} onClick={submit}>
          Salvar logística
        </Button>
        {save.isSuccess && !save.isPending && (
          <span className="text-sm text-green">Logística salva.</span>
        )}
        {save.isError && <span className="text-sm text-red">Não foi possível salvar.</span>}
      </div>
    </div>
  );
}

/** Exibição de logística para quem não pode editar. */
function LogisticaRead({ data }: { data: EventoDetalhe }) {
  const ev = data.event;
  const maquiagem = [ev.makeup_time, makeupLocationLabel(ev.makeup_location)].filter(Boolean).join(" · ");
  const saida = [ev.departure_time, ev.departure_location].filter(Boolean).join(" · ");
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      <dt className="text-muted">Maquiagem</dt>
      <dd className="text-ink">{maquiagem || "—"}</dd>
      <dt className="text-muted">Saída</dt>
      <dd className="text-ink">{saida || "—"}</dd>
      <dt className="text-muted">Precisa ensaio</dt>
      <dd className="text-ink">{ev.needs_rehearsal ? "Sim" : "Não"}</dd>
    </dl>
  );
}

function Logistica({ data }: { data: EventoDetalhe }) {
  const ev = data.event;
  if (ev.is_ensaio) return null;
  const canEdit = Boolean(data.flags.can_edit_event);
  const hasAny = Boolean(
    ev.makeup_time || ev.makeup_location || ev.departure_time || ev.departure_location || ev.needs_rehearsal,
  );
  if (!canEdit && !hasAny) return null;
  return (
    <Section title="Logística">
      {canEdit ? <LogisticaEdit data={data} /> : <LogisticaRead data={data} />}
    </Section>
  );
}

function Historico({ data }: { data: EventoDetalhe }) {
  if (data.logs.length === 0) return null;
  return (
    <Section title="Histórico">
      <ul className="space-y-1.5 text-sm">
        {data.logs.slice(0, 20).map((log, i) => (
          <li key={i} className="text-muted">
            <span className="tabular-nums">{log.ts}</span> · {log.actor_name}: {log.message}
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function EventDetailPage() {
  const reduceMotion = useReducedMotion();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = useEvent(id);

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <div className="mb-4">
        <Button asChild variant="ghost" size="sm">
          <Link to="/agenda">‹ Agenda</Link>
        </Button>
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o evento.
        </div>
      )}

      {query.data && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="space-y-4"
        >
          <header>
            <h1 className="text-2xl font-semibold text-ink">{query.data.event.title}</h1>
            <p className="text-sm text-muted">
              {formatDate(query.data.event.start_at)}
              {query.data.event.location && ` · ${query.data.event.location}`}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
                {query.data.event.event_type}
              </span>
              <ConfirmControl data={query.data} />
            </div>
          </header>

          <Kpi data={query.data} />
          <Elenco data={query.data} />
          <Logistica data={query.data} />
          <Venda data={query.data} />
          <Pagamentos data={query.data} />
          <Reembolsos data={query.data} />
          <Historico data={query.data} />
        </motion.div>
      )}
    </div>
  );
}
