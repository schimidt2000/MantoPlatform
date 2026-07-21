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
  useTalents,
  type TalentoOption,
} from "../lib/casting";

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

function RoleReadRow({ role }: { role: RoleItem }) {
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <div>
        <div className="font-medium text-ink">{role.character_name}</div>
        <div className="text-sm text-muted">
          {role.talent ? role.talent.name : "— sem talento —"}
          {role.figurino_done && " · figurino ok"}
        </div>
      </div>
      {role.cache_value != null && (
        <span className="shrink-0 tabular-nums text-sm text-ink">{brl(role.cache_value)}</span>
      )}
    </li>
  );
}

function RoleAssignRow({
  role,
  eventId,
  talents,
}: {
  role: RoleItem;
  eventId: number;
  talents: TalentoOption[];
}) {
  const assign = useAssignRole(eventId);
  const remove = useDeleteRole(eventId);
  const [talentId, setTalentId] = useState<number | null>(role.talent?.id ?? null);
  const [cache, setCache] = useState<number>(role.cache_value ?? 0);

  return (
    <li className="py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-medium text-ink">{role.character_name}</span>
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
            />
          ) : (
            <RoleReadRow key={r.role_id} role={r} />
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
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
                {query.data.event.event_type}
              </span>
              {query.data.event.confirmed && (
                <span className="rounded-md bg-green-soft px-2 py-0.5 text-xs text-green">
                  Confirmado
                </span>
              )}
            </div>
          </header>

          <Kpi data={query.data} />
          <Elenco data={query.data} />
          <Venda data={query.data} />
          <Pagamentos data={query.data} />
          <Reembolsos data={query.data} />
          <Historico data={query.data} />
        </motion.div>
      )}
    </div>
  );
}
