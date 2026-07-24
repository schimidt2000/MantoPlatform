import { useRef, useState, type ReactNode } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import { useEvent, type EventoDetalhe, type RoleItem } from "../lib/agenda";
import {
  useAddImageObservation,
  useAddObservation,
  useDeleteObservation,
} from "../lib/observations";
import {
  useAddContract,
  useAddInvoice,
  useAddPayment,
  useAddReimbursement,
  useCollectReimbursement,
  useDeleteContract,
  useDeletePayment,
  useDeleteReimbursement,
  useEditPayment,
  useToggleContractSigned,
} from "../lib/eventAttachments";
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
import {
  useDeleteEvent,
  useSaveLogistics,
  useSyncEvent,
  useToggleConfirm,
} from "../lib/eventOps";

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

/** Contratos do evento (feature 153) — anexar, e para SUPERADMIN, marcar assinado/excluir. */
function Contratos({ data }: { data: EventoDetalhe }) {
  if (!data.contratos) return null;
  const eventId = data.event.id;
  const isSuperadmin = Boolean(data.flags.is_superadmin);
  const add = useAddContract(eventId);
  const del = useDeleteContract(eventId);
  const toggle = useToggleContractSigned(eventId);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!file) return;
    add.mutate(
      { file },
      {
        onSuccess: () => {
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  return (
    <Section title="Contratos">
      {data.contratos.length === 0 ? (
        <p className="text-sm text-muted">Nenhum contrato anexado.</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.contratos.map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
              <a
                href={assetUrl(c.file_path)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue underline"
              >
                Abrir contrato
              </a>
              <span className="flex items-center gap-2">
                <span className={c.is_signed ? "text-green" : "text-muted"}>
                  {c.is_signed ? "Assinado" : "Pendente"}
                </span>
                {isSuperadmin && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={toggle.isPending}
                      onClick={() => toggle.mutate(c.id)}
                    >
                      {c.is_signed ? "Desmarcar" : "Marcar assinado"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={del.isPending}
                      onClick={() => {
                        if (window.confirm("Excluir este contrato?")) del.mutate(c.id);
                      }}
                      aria-label="Excluir contrato"
                    >
                      ✕
                    </Button>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 flex items-center gap-2 border-t border-line pt-4">
        <input
          ref={inputRef}
          type="file"
          className="text-sm text-ink"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label="Arquivo do contrato"
        />
        <Button size="sm" loading={add.isPending} disabled={!file} onClick={submit}>
          Adicionar
        </Button>
      </div>
      {add.isError && <p className="mt-1 text-sm text-red">Não foi possível anexar o contrato.</p>}
    </Section>
  );
}

/** Notas fiscais do evento (feature 153) — só adicionar (lista completa segue no formulário
 * de venda, Jinja). Visível a Comercial/Financeiro/Superadmin (mesmo gate do servidor). */
function NotasFiscais({ data }: { data: EventoDetalhe }) {
  if (!data.notas_fiscais) return null;
  const eventId = data.event.id;
  const add = useAddInvoice(eventId);
  const [amount, setAmount] = useState(0);
  const [issueDate, setIssueDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!amount && !issueDate && !file) return;
    add.mutate(
      { amount: amount || undefined, issue_date: issueDate || undefined, file: file ?? undefined },
      {
        onSuccess: () => {
          setAmount(0);
          setIssueDate("");
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  return (
    <Section title="Notas fiscais">
      {data.notas_fiscais.length === 0 ? (
        <p className="text-sm text-muted">Nenhuma nota fiscal anexada.</p>
      ) : (
        <ul className="divide-y divide-line">
          {data.notas_fiscais.map((inv) => (
            <li key={inv.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
              <span className="text-ink">
                {brl(inv.amount)}
                {inv.issue_date && ` · ${inv.issue_date}`}
              </span>
              <span className="flex items-center gap-2">
                <span className={inv.status === "emitida" ? "text-green" : "text-muted"}>
                  {inv.status === "emitida" ? "Emitida" : "A emitir"}
                </span>
                {inv.file && (
                  <a
                    href={assetUrl(inv.file)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue underline"
                  >
                    Abrir
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
        <MoneyInput
          value={amount}
          onValueChange={setAmount}
          className="h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="0,00"
          aria-label="Valor da nota"
        />
        <input
          type="date"
          className="h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={issueDate}
          onChange={(e) => setIssueDate(e.target.value)}
          aria-label="Data de emissão"
        />
        <input
          ref={inputRef}
          type="file"
          className="text-sm text-ink"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label="Arquivo da nota"
        />
        <Button
          size="sm"
          loading={add.isPending}
          disabled={!amount && !issueDate && !file}
          onClick={submit}
        >
          Adicionar
        </Button>
      </div>
      {add.isError && <p className="mt-1 text-sm text-red">Informe ao menos o valor, a data ou o arquivo.</p>}
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

/** Um pagamento — para SUPERADMIN, permite corrigir o valor ou excluir (feature 153). */
function PagamentoItem({
  item,
  eventId,
  isSuperadmin,
}: {
  item: NonNullable<EventoDetalhe["pagamentos"]>["items"][number];
  eventId: number;
  isSuperadmin: boolean;
}) {
  const edit = useEditPayment(eventId);
  const del = useDeletePayment(eventId);
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(item.amount ?? 0);

  if (editing) {
    return (
      <li className="flex items-center justify-between gap-2 py-1.5 text-sm">
        <span className="text-muted">{formatDate(item.created_at)}</span>
        <span className="flex items-center gap-2">
          <MoneyInput
            value={amount}
            onValueChange={setAmount}
            className="h-9 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            aria-label="Novo valor"
          />
          <Button
            size="sm"
            loading={edit.isPending}
            onClick={() =>
              edit.mutate(
                { paymentId: item.id, amount },
                { onSuccess: () => setEditing(false) },
              )
            }
          >
            Salvar
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            Cancelar
          </Button>
        </span>
      </li>
    );
  }

  return (
    <li className="flex items-center justify-between gap-3 py-1.5 text-sm">
      <span className="text-muted">{formatDate(item.created_at)}</span>
      <span className="flex items-center gap-2">
        <a
          href={assetUrl(item.file_path)}
          target="_blank"
          rel="noopener noreferrer"
          className="tabular-nums text-blue underline"
        >
          {brl(item.amount)}
        </a>
        {isSuperadmin && (
          <>
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
              Editar
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={del.isPending}
              onClick={() => {
                if (window.confirm("Excluir este comprovante de pagamento?")) del.mutate(item.id);
              }}
              aria-label="Excluir comprovante"
            >
              ✕
            </Button>
          </>
        )}
      </span>
    </li>
  );
}

/** Form para adicionar comprovante de pagamento (feature 153). */
function AddPaymentForm({ eventId }: { eventId: number }) {
  const add = useAddPayment(eventId);
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!amount || !file) return;
    add.mutate(
      { amount, file },
      {
        onSuccess: () => {
          setAmount(0);
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
      <MoneyInput
        value={amount}
        onValueChange={setAmount}
        className="h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="0,00"
        aria-label="Valor recebido"
      />
      <input
        ref={inputRef}
        type="file"
        className="text-sm text-ink"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        aria-label="Comprovante de pagamento"
      />
      <Button size="sm" loading={add.isPending} disabled={!amount || !file} onClick={submit}>
        Adicionar
      </Button>
      {add.isError && (
        <p className="w-full text-sm text-red">Informe o valor e anexe o comprovante.</p>
      )}
    </div>
  );
}

function Pagamentos({ data }: { data: EventoDetalhe }) {
  if (!data.pagamentos) return null;
  const p = data.pagamentos;
  const isSuperadmin = Boolean(data.flags.is_superadmin);
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
            <PagamentoItem key={it.id} item={it} eventId={data.event.id} isSuperadmin={isSuperadmin} />
          ))}
        </ul>
      )}
      <AddPaymentForm eventId={data.event.id} />
    </Section>
  );
}

/** Form para marcar um reembolso pendente como cobrado (feature 153) — some quando já cobrado. */
function CollectReembolsoForm({ reimbursementId, eventId }: { reimbursementId: number; eventId: number }) {
  const collect = useCollectReimbursement(eventId);
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!amount || !file) return;
    collect.mutate(
      { reimbursementId, collected_amount: amount, file },
      {
        onSuccess: () => {
          setAmount(0);
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  return (
    <div className="mt-1 flex flex-wrap items-center gap-2">
      <MoneyInput
        value={amount}
        onValueChange={setAmount}
        className="h-9 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="0,00"
        aria-label="Valor recebido"
      />
      <input
        ref={inputRef}
        type="file"
        className="text-sm text-ink"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        aria-label="Comprovante de recebimento"
      />
      <Button size="sm" loading={collect.isPending} disabled={!amount || !file} onClick={submit}>
        Marcar cobrado
      </Button>
      {collect.isError && <p className="w-full text-sm text-red">Informe o valor e anexe o comprovante.</p>}
    </div>
  );
}

/** Um reembolso — link do comprovante do gasto, form de cobrar quando pendente, excluir (SUPERADMIN). */
function ReembolsoItem({
  item,
  eventId,
  isSuperadmin,
}: {
  item: NonNullable<EventoDetalhe["reembolsos"]>["items"][number];
  eventId: number;
  isSuperadmin: boolean;
}) {
  const del = useDeleteReimbursement(eventId);
  return (
    <li className="py-1.5 text-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="text-ink">
          {item.description}
          {item.invoice_file_path && (
            <a
              href={assetUrl(item.invoice_file_path)}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 text-blue underline"
            >
              Nota do gasto
            </a>
          )}
          {item.is_collected && <span className="text-green"> · cobrado</span>}
        </span>
        <span className="flex items-center gap-2">
          <span className="tabular-nums text-ink">{brl(item.amount)}</span>
          {isSuperadmin && (
            <Button
              variant="ghost"
              size="sm"
              loading={del.isPending}
              onClick={() => {
                if (window.confirm("Excluir este reembolso?")) del.mutate(item.id);
              }}
              aria-label="Excluir reembolso"
            >
              ✕
            </Button>
          )}
        </span>
      </div>
      {item.is_collected && item.receipt_file_path ? (
        <a
          href={assetUrl(item.receipt_file_path)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue underline"
        >
          Comprovante de recebimento ({brl(item.collected_amount)})
        </a>
      ) : !item.is_collected ? (
        <CollectReembolsoForm reimbursementId={item.id} eventId={eventId} />
      ) : null}
    </li>
  );
}

/** Form para registrar um novo reembolso (feature 153). */
function AddReembolsoForm({ eventId }: { eventId: number }) {
  const add = useAddReimbursement(eventId);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!description.trim() || !amount) return;
    add.mutate(
      { description: description.trim(), amount, file: file ?? undefined },
      {
        onSuccess: () => {
          setDescription("");
          setAmount(0);
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
      <input
        className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="Descrição do gasto"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        aria-label="Descrição do reembolso"
      />
      <MoneyInput
        value={amount}
        onValueChange={setAmount}
        className="h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="0,00"
        aria-label="Valor a cobrar"
      />
      <input
        ref={inputRef}
        type="file"
        className="text-sm text-ink"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        aria-label="Nota fiscal do gasto (opcional)"
      />
      <Button
        size="sm"
        loading={add.isPending}
        disabled={!description.trim() || !amount}
        onClick={submit}
      >
        Registrar reembolso
      </Button>
      {add.isError && (
        <p className="w-full text-sm text-red">Informe a descrição e o valor do reembolso.</p>
      )}
    </div>
  );
}

function Reembolsos({ data }: { data: EventoDetalhe }) {
  if (!data.reembolsos) return null;
  const r = data.reembolsos;
  const isSuperadmin = Boolean(data.flags.is_superadmin);
  return (
    <Section title="Reembolsos">
      <p className="mb-2 text-sm text-muted">
        Pendente: <span className="tabular-nums text-ink">{brl(r.pendentes_total)}</span>
      </p>
      {r.items.length === 0 ? (
        <p className="text-sm text-muted">Nenhum reembolso registrado.</p>
      ) : (
        <ul className="divide-y divide-line">
          {r.items.map((it) => (
            <ReembolsoItem key={it.id} item={it} eventId={data.event.id} isSuperadmin={isSuperadmin} />
          ))}
        </ul>
      )}
      <AddReembolsoForm eventId={data.event.id} />
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

type ObservationT = NonNullable<EventoDetalhe["observations"]>[number];

/** Uma observação (texto/link/imagem) com botão de remover. Remoção sem gate de papel. */
function ObservationItem({ obs, eventId }: { obs: ObservationT; eventId: number }) {
  const del = useDeleteObservation(eventId);
  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0 flex-1">
        {obs.label && <div className="text-xs text-muted">{obs.label}</div>}
        {obs.obs_type === "image" ? (
          obs.image_url ? (
            <img
              src={assetUrl(obs.image_url)}
              alt={obs.label ?? "Observação"}
              className="mt-1 max-w-full rounded-md"
            />
          ) : null
        ) : obs.obs_type === "link" ? (
          <a
            href={obs.content ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="break-words text-sm text-blue underline"
          >
            {obs.content}
          </a>
        ) : (
          <p className="whitespace-pre-wrap break-words text-sm text-ink">{obs.content}</p>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        loading={del.isPending}
        onClick={() => {
          if (window.confirm("Remover esta observação?")) del.mutate(obs.id);
        }}
        aria-label="Remover observação"
      >
        ✕
      </Button>
    </li>
  );
}

/** Form para adicionar observação de texto/link/imagem (imagem via multipart, feature 153). */
function AddObservationForm({ eventId }: { eventId: number }) {
  const add = useAddObservation(eventId);
  const addImage = useAddImageObservation(eventId);
  const [obsType, setObsType] = useState<"text" | "link" | "image">("text");
  const [content, setContent] = useState("");
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isImage = obsType === "image";
  const pending = isImage ? addImage.isPending : add.isPending;
  const isError = isImage ? addImage.isError : add.isError;
  const canSubmit = isImage ? Boolean(file) : Boolean(content.trim());

  const submit = () => {
    if (isImage) {
      if (!file) return;
      addImage.mutate(
        { file, label: label.trim() || undefined },
        {
          onSuccess: () => {
            setFile(null);
            setLabel("");
            if (inputRef.current) inputRef.current.value = "";
          },
        },
      );
      return;
    }
    if (!content.trim()) return;
    add.mutate(
      { obs_type: obsType, content: content.trim(), label: label.trim() || undefined },
      { onSuccess: () => { setContent(""); setLabel(""); } },
    );
  };

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="mb-2 text-sm font-medium text-muted">Nova observação</div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={obsType}
          onChange={(e) => setObsType(e.target.value as "text" | "link" | "image")}
          aria-label="Tipo de observação"
        >
          <option value="text">Texto</option>
          <option value="link">Link</option>
          <option value="image">Imagem</option>
        </select>
        {isImage ? (
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="text-sm text-ink"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            aria-label="Arquivo da imagem"
          />
        ) : (
          <input
            className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
            placeholder={obsType === "link" ? "https://…" : "Escreva a observação"}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            aria-label="Conteúdo"
          />
        )}
        <input
          className="h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Rótulo (opcional)"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          aria-label="Rótulo"
        />
        <Button size="sm" loading={pending} disabled={!canSubmit} onClick={submit}>
          Adicionar
        </Button>
      </div>
      {isError && <p className="mt-1 text-sm text-red">Não foi possível adicionar.</p>}
    </div>
  );
}

function Observacoes({ data }: { data: EventoDetalhe }) {
  if (!data.observations) return null; // ausente em eventos ENSAIO
  const obs = data.observations;
  return (
    <Section title="Observações">
      {obs.length === 0 ? (
        <p className="text-sm text-muted">Nenhuma observação.</p>
      ) : (
        <ul className="divide-y divide-line">
          {obs.map((o) => (
            <ObservationItem key={o.id} obs={o} eventId={data.event.id} />
          ))}
        </ul>
      )}
      <AddObservationForm eventId={data.event.id} />
    </Section>
  );
}

/** Ações de nível-evento: sincronizar (qualquer autenticado) e excluir (só can_delete). */
function EventActions({ data }: { data: EventoDetalhe }) {
  const navigate = useNavigate();
  const sync = useSyncEvent(data.event.id);
  const del = useDeleteEvent(data.event.id);
  const canDelete = Boolean(data.flags.can_delete);

  return (
    <Section title="Ações">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          loading={sync.isPending}
          onClick={() => sync.mutate()}
        >
          Sincronizar com Google
        </Button>
        {sync.isSuccess && !sync.isPending && (
          <span className="text-sm text-green">Sincronizado.</span>
        )}
        {sync.isError && <span className="text-sm text-red">{sync.error?.message}</span>}
      </div>
      {canDelete && (
        <div className="mt-4 border-t border-line pt-4">
          <Button
            variant="outline"
            size="sm"
            className="text-red"
            loading={del.isPending}
            onClick={() => {
              if (
                window.confirm(
                  `Excluir o evento "${data.event.title}"? Esta ação não pode ser desfeita.`,
                )
              ) {
                del.mutate(undefined, { onSuccess: () => navigate("/agenda") });
              }
            }}
          >
            Excluir evento
          </Button>
          {del.isError && <p className="mt-1 text-sm text-red">{del.error?.message}</p>}
        </div>
      )}
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
          <PageHeader
            title={query.data.event.title}
            subtitle={
              formatDate(query.data.event.start_at) +
              (query.data.event.location ? ` · ${query.data.event.location}` : "")
            }
            actions={
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">
                  {query.data.event.event_type}
                </span>
                {query.data.flags.can_edit_core && (
                  <Button asChild variant="outline" size="sm">
                    <Link to={`/events/${query.data.event.id}/edit`}>Editar</Link>
                  </Button>
                )}
                <ConfirmControl data={query.data} />
              </div>
            }
          />

          <Kpi data={query.data} />
          <Elenco data={query.data} />
          <Logistica data={query.data} />
          <Venda data={query.data} />
          <Contratos data={query.data} />
          <NotasFiscais data={query.data} />
          <Pagamentos data={query.data} />
          <Reembolsos data={query.data} />
          <Observacoes data={query.data} />
          <Historico data={query.data} />
          <EventActions data={query.data} />
        </motion.div>
      )}
    </div>
  );
}
