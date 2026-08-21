import { useEffect, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, DenseCard, FileUpload, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { Modal } from "../components/Modal";
import { hojeYmd } from "../lib/horaLocal";
import {
  useApproveGasto,
  useCreateGasto,
  useDeleteGasto,
  useGastosEventos,
  useGastosExtras,
  useGastosFuncionarios,
  useLinkGastoEvento,
  useRejectGasto,
  useUpdateGasto,
  type GastoExtra,
  type GastosTotals,
  type GastoMarketingBatch,
} from "../lib/gastos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const TH = "px-3 py-2";
const TD = "px-3 py-2 align-top";

type DisplayStatus = "pendente" | "aprovado" | "aprovado_com_edicoes" | "rejeitado";

function displayStatus(expense: GastoExtra): DisplayStatus {
  if (expense.status === "aprovado" && expense.approved_with_edits) return "aprovado_com_edicoes";
  return expense.status;
}

const STATUS_LABEL: Record<DisplayStatus, string> = {
  pendente: "Pendente",
  aprovado: "Aprovado",
  aprovado_com_edicoes: "Aprovado c/ edições",
  rejeitado: "Rejeitado",
};

const STATUS_CLASS: Record<DisplayStatus, string> = {
  // `bg-amber-soft`/`text-amber` NÃO EXISTEM na paleta (o design system usa `gold` no lugar de
  // `amber`): o Tailwind nunca gerou essas duas classes, então o badge "Pendente" vinha sem
  // fundo e herdando a cor do texto ao redor. `gold-soft`/`gold-ink` é o par real.
  pendente: "bg-gold-soft text-gold-ink",
  aprovado: "bg-green-soft text-green",
  aprovado_com_edicoes: "bg-blue-soft text-blue",
  rejeitado: "bg-red-soft text-red",
};

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function StatusBadge({ expense }: { expense: GastoExtra }) {
  const status = displayStatus(expense);
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs whitespace-nowrap ${STATUS_CLASS[status]}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <DenseCard stats={[{ label, value }]}>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </DenseCard>
  );
}

function KpiGrid({ totals }: { totals: GastosTotals }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard label="Todos" value={brl(totals.todos.total)} sub={`${totals.todos.count} gasto(s)`} />
      <KpiCard label="Pendentes" value={brl(totals.pendente.total)} sub={`${totals.pendente.count} gasto(s)`} />
      <KpiCard label="Aprovados" value={brl(totals.aprovado.total)} sub={`${totals.aprovado.count} gasto(s)`} />
      <KpiCard label="Rejeitados" value={brl(totals.rejeitado.total)} sub={`${totals.rejeitado.count} gasto(s)`} />
    </div>
  );
}

function EventoVincular({ expense }: { expense: GastoExtra }) {
  const [date, setDate] = useState(expense.expense_date);
  const eventos = useGastosEventos(date);
  const link = useLinkGastoEvento();

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <input
        type="date"
        className="h-8 rounded-md border border-line bg-panel px-2"
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
      <select
        className="h-8 rounded-md border border-line bg-panel px-2"
        value={expense.event_id ?? ""}
        onChange={(e) => link.mutate({ id: expense.id, event_id: e.target.value ? Number(e.target.value) : null })}
        disabled={link.isPending}
      >
        <option value="">Sem evento vinculado</option>
        {eventos.data?.events.map((ev) => (
          <option key={ev.id} value={ev.id}>
            {ev.label}
          </option>
        ))}
      </select>
    </div>
  );
}

interface GastoFormValues {
  description: string;
  category: string;
  amount: number;
  expenseDate: string;
  notes: string;
  disbursementType: "" | "reembolso" | "fornecedor";
  reimburseUserId: number | "";
  supplierName: string;
  supplierPix: string;
  eventDate: string;
  eventId: number | "";
}

function emptyForm(categories: string[]): GastoFormValues {
  return {
    description: "",
    category: categories[0] ?? "Outros",
    amount: 0,
    expenseDate: hojeYmd(),
    notes: "",
    disbursementType: "",
    reimburseUserId: "",
    supplierName: "",
    supplierPix: "",
    eventDate: hojeYmd(),
    eventId: "",
  };
}

function formFromExpense(expense: GastoExtra): GastoFormValues {
  return {
    description: expense.description,
    category: expense.category,
    amount: expense.amount,
    expenseDate: expense.expense_date,
    notes: expense.notes,
    disbursementType: (expense.disbursement_type ?? "") as "" | "reembolso" | "fornecedor",
    reimburseUserId: "",
    supplierName: expense.disbursement_type === "fornecedor" ? expense.payee_name : "",
    supplierPix: expense.disbursement_type === "fornecedor" ? expense.payee_pix : "",
    eventDate: expense.expense_date,
    eventId: expense.event_id ?? "",
  };
}

function DesembolsoFields({
  values,
  onChange,
  fieldErrors,
}: {
  values: GastoFormValues;
  onChange: (patch: Partial<GastoFormValues>) => void;
  fieldErrors: Record<string, string>;
}) {
  const funcionarios = useGastosFuncionarios();

  return (
    <div className="space-y-3">
      <div>
        <label className={LABEL}>Como será pago?</label>
        <div className="space-y-1.5 text-sm text-ink">
          {(
            [
              ["reembolso", "Reembolso a funcionário"],
              ["fornecedor", "Pagamento a fornecedor"],
              ["", "Sem desembolso definido"],
            ] as const
          ).map(([value, label]) => (
            <label key={value || "nenhum"} className="flex items-center gap-2">
              <input
                type="radio"
                name="disbursement_type"
                checked={values.disbursementType === value}
                onChange={() => onChange({ disbursementType: value })}
              />
              {label}
            </label>
          ))}
        </div>
      </div>
      {values.disbursementType === "reembolso" && (
        <div>
          <label className={LABEL}>Funcionário</label>
          <select
            className={INPUT}
            value={values.reimburseUserId}
            onChange={(e) => onChange({ reimburseUserId: e.target.value ? Number(e.target.value) : "" })}
          >
            <option value="">Selecione…</option>
            {funcionarios.data?.funcionarios.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          {fieldErrors.reimburse_user_id && (
            <p className="mt-1 text-xs text-red">{fieldErrors.reimburse_user_id}</p>
          )}
        </div>
      )}
      {values.disbursementType === "fornecedor" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Nome do fornecedor</label>
            <input
              className={INPUT}
              value={values.supplierName}
              onChange={(e) => onChange({ supplierName: e.target.value })}
            />
            {fieldErrors.supplier_name && <p className="mt-1 text-xs text-red">{fieldErrors.supplier_name}</p>}
          </div>
          <div>
            <label className={LABEL}>Chave PIX (opcional)</label>
            <input
              className={INPUT}
              value={values.supplierPix}
              onChange={(e) => onChange({ supplierPix: e.target.value })}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function EventoFields({
  values,
  onChange,
}: {
  values: GastoFormValues;
  onChange: (patch: Partial<GastoFormValues>) => void;
}) {
  const eventos = useGastosEventos(values.eventDate);
  return (
    <div>
      <label className={LABEL}>Vincular a um evento (opcional)</label>
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="date"
          className={INPUT}
          value={values.eventDate}
          onChange={(e) => onChange({ eventDate: e.target.value })}
        />
        <select
          className={INPUT}
          value={values.eventId}
          onChange={(e) => onChange({ eventId: e.target.value ? Number(e.target.value) : "" })}
        >
          <option value="">Sem evento vinculado</option>
          {eventos.data?.events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function GastoFormModal({
  mode,
  expense,
  categories,
  open,
  onClose,
}: {
  mode: "create" | "edit";
  expense: GastoExtra | null;
  categories: string[];
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateGasto();
  const update = useUpdateGasto();
  const [values, setValues] = useState<GastoFormValues>(() => emptyForm(categories));
  const [receipt, setReceipt] = useState<File | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    setFieldErrors({});
    setReceipt(null);
    setValues(mode === "edit" && expense ? formFromExpense(expense) : emptyForm(categories));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, mode, expense?.id]);

  const patch = (p: Partial<GastoFormValues>) => setValues((v) => ({ ...v, ...p }));

  const buildPayload = () => ({
    description: values.description,
    category: values.category,
    amount: values.amount,
    expense_date: values.expenseDate,
    disbursement_type: values.disbursementType,
    reimburse_user_id: values.reimburseUserId === "" ? undefined : values.reimburseUserId,
    supplier_name: values.disbursementType === "fornecedor" ? values.supplierName : undefined,
    supplier_pix: values.disbursementType === "fornecedor" ? values.supplierPix : undefined,
    event_id: values.eventId === "" ? undefined : values.eventId,
  });

  const handleCreate = () => {
    if (!receipt) {
      setFieldErrors({ receipt: "Anexe a Nota Fiscal." });
      return;
    }
    setFieldErrors({});
    create.mutate(
      { ...buildPayload(), notes: values.notes, receipt },
      {
        onSuccess: onClose,
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      },
    );
  };

  const handleSave = (aprovar: boolean) => {
    if (!expense) return;
    setFieldErrors({});
    update.mutate(
      { id: expense.id, ...buildPayload(), aprovar },
      {
        onSuccess: onClose,
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      },
    );
  };

  const busy = create.isPending || update.isPending;
  const genericError =
    (create.isError || update.isError) && !Object.keys(fieldErrors).length
      ? "Não foi possível salvar o gasto."
      : null;

  return (
    <Modal open={open} onClose={onClose} title={mode === "create" ? "Novo gasto" : "Editar gasto"}>
      <div className="space-y-3">
        <div>
          <label className={LABEL}>Descrição</label>
          <input
            className={INPUT}
            value={values.description}
            onChange={(e) => patch({ description: e.target.value })}
          />
          {fieldErrors.description && <p className="mt-1 text-xs text-red">{fieldErrors.description}</p>}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Categoria</label>
            <select className={INPUT} value={values.category} onChange={(e) => patch({ category: e.target.value })}>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={LABEL}>Valor (R$)</label>
            <MoneyInput className={INPUT} value={values.amount} onValueChange={(amount) => patch({ amount })} />
            {fieldErrors.amount && <p className="mt-1 text-xs text-red">{fieldErrors.amount}</p>}
          </div>
        </div>
        <div>
          <label className={LABEL}>Data do gasto</label>
          <input
            type="date"
            className={INPUT}
            value={values.expenseDate}
            onChange={(e) => patch({ expenseDate: e.target.value })}
          />
        </div>
        <DesembolsoFields values={values} onChange={patch} fieldErrors={fieldErrors} />
        <EventoFields values={values} onChange={patch} />
        {mode === "create" && (
          <>
            <div>
              <label className={LABEL}>Observações (opcional)</label>
              <textarea
                className={INPUT}
                rows={2}
                value={values.notes}
                onChange={(e) => patch({ notes: e.target.value })}
              />
            </div>
            <FileUpload
              label="Nota Fiscal (foto ou PDF)"
              accept="image/*,application/pdf"
              maxSizeBytes={10 * 1024 * 1024}
              required
              error={fieldErrors.receipt}
              onChange={setReceipt}
            />
          </>
        )}
        {genericError && <p className="text-sm text-red">{genericError}</p>}
        <div className="flex flex-wrap gap-2 pt-1">
          {mode === "create" ? (
            <Button loading={create.isPending} onClick={handleCreate}>
              Registrar gasto
            </Button>
          ) : (
            <>
              {expense?.status !== "rejeitado" && (
                <Button loading={update.isPending} disabled={busy} onClick={() => handleSave(false)}>
                  Salvar
                </Button>
              )}
              {expense?.status !== "aprovado" && (
                <Button
                  variant="outline"
                  loading={update.isPending}
                  disabled={busy}
                  onClick={() => handleSave(true)}
                >
                  Salvar e Aprovar
                </Button>
              )}
            </>
          )}
          <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/**
 * Detalhe do gasto gerado pelo auditor de marketing (feature 256): quanto cada campanha pesou
 * no mês e se o lote já congelou (gasto aprovado/rejeitado — diferenças viram achado no
 * relatório, nunca alteração silenciosa).
 */
function MarketingBatchDetail({ batch }: { batch: GastoMarketingBatch }) {
  const [ano, mes] = batch.month_ref.split("-");
  return (
    <div className="mt-2 rounded-md border border-line bg-surface px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
        Gerado pelo auditor de marketing — {batch.platform} {mes}/{ano}
        <span className={`rounded-full px-2 py-0.5 text-[11px] ${batch.frozen ? "bg-surface-2 text-muted" : "bg-gold-soft text-gold-ink"}`}>
          {batch.frozen ? "congelado" : "atualiza até aprovar"}
        </span>
      </div>
      <ul className="mt-1 space-y-0.5">
        {batch.lines.map((line) => (
          <li key={line.campaign_name} className="flex justify-between gap-3">
            <span className="truncate text-muted">{line.campaign_name}</span>
            <span className="whitespace-nowrap tabular-nums text-ink">{brl(Number(line.amount))}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-muted">
        Reportado pelas plataformas: {brl(Number(batch.reported_total))}
        {batch.run_id && ` · rodada ${batch.run_id}`}
      </p>
    </div>
  );
}

function GastoRow({
  expense,
  canManage,
  onEdit,
}: {
  expense: GastoExtra;
  canManage: boolean;
  onEdit: (expense: GastoExtra) => void;
}) {
  const approve = useApproveGasto();
  const reject = useRejectGasto();
  const del = useDeleteGasto();
  const [showLink, setShowLink] = useState(false);

  const canDelete = canManage || (expense.status === "pendente");

  const handleReject = () => {
    const motivo = window.prompt("Motivo da rejeição (opcional):") ?? "";
    reject.mutate({ id: expense.id, motivo });
  };

  const handleDelete = () => {
    if (!window.confirm(`Excluir o gasto "${expense.description}"?`)) return;
    del.mutate(expense.id);
  };

  return (
    <>
      <tr className="border-b border-line align-top text-sm">
        <td className={`${TD} whitespace-nowrap`}>{formatDate(expense.expense_date)}</td>
        <td className={TD}>
          {expense.description}
          {expense.notes && <p className="text-xs text-muted">{expense.notes}</p>}
          {expense.marketing_batch && <MarketingBatchDetail batch={expense.marketing_batch} />}
        </td>
        <td className={TD}>{expense.category}</td>
        <td className={`${TD} whitespace-nowrap text-right tabular-nums`}>{brl(expense.amount)}</td>
        <td className={TD}>
          <StatusBadge expense={expense} />
        </td>
        <td className={TD}>
          {expense.disbursement_type ? (
            <>
              {expense.payee_name}
              <span className="ml-1 text-xs text-muted">
                ({expense.disbursement_type === "reembolso" ? "reembolso" : "fornecedor"})
              </span>
            </>
          ) : (
            <span className="text-muted">—</span>
          )}
        </td>
        <td className={TD}>{expense.event_title ?? <span className="text-muted">—</span>}</td>
        {canManage && <td className={TD}>{expense.created_by_name ?? "—"}</td>}
        <td className={TD}>
          {expense.receipt_url ? (
            <a
              href={expense.receipt_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-accent hover:underline"
            >
              Ver
            </a>
          ) : (
            <span className="text-muted">—</span>
          )}
        </td>
        <td className={`${TD} whitespace-nowrap`}>
          <div className="flex flex-wrap gap-2">
            {canManage && expense.status === "pendente" && (
              <>
                <Button size="sm" loading={approve.isPending} onClick={() => approve.mutate(expense.id)}>
                  Aprovar
                </Button>
                <Button size="sm" variant="ghost" loading={reject.isPending} onClick={handleReject}>
                  Rejeitar
                </Button>
              </>
            )}
            {canManage && (
              <>
                <Button size="sm" variant="ghost" onClick={() => onEdit(expense)}>
                  Editar
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowLink((v) => !v)}>
                  Vincular evento
                </Button>
              </>
            )}
            {canDelete && (
              <Button size="sm" variant="ghost" loading={del.isPending} onClick={handleDelete}>
                Excluir
              </Button>
            )}
          </div>
        </td>
      </tr>
      {showLink && (
        <tr className="border-b border-line bg-surface-2/50">
          <td colSpan={canManage ? 10 : 9} className="px-3 py-2">
            <EventoVincular expense={expense} />
          </td>
        </tr>
      )}
    </>
  );
}

function GastosTable({
  expenses,
  canManage,
  onEdit,
}: {
  expenses: GastoExtra[];
  canManage: boolean;
  onEdit: (expense: GastoExtra) => void;
}) {
  return (
    <Card>
      <CardContent className="p-0">
        {expenses.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted">Nenhum gasto registrado ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs font-medium uppercase text-muted">
                  <th className={TH}>Data</th>
                  <th className={TH}>Descrição</th>
                  <th className={TH}>Categoria</th>
                  <th className={`${TH} text-right`}>Valor</th>
                  <th className={TH}>Status</th>
                  <th className={TH}>Desembolso</th>
                  <th className={TH}>Evento</th>
                  {canManage && <th className={TH}>Autor</th>}
                  <th className={TH}>Nota Fiscal</th>
                  <th className={TH}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((e) => (
                  <GastoRow key={e.id} expense={e} canManage={canManage} onEdit={onEdit} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function GastosExtrasPage() {
  const query = useGastosExtras();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<GastoExtra | null>(null);

  const canManage = query.data?.can_manage ?? false;

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (expense: GastoExtra) => {
    setEditing(expense);
    setModalOpen(true);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Gastos Extras"
        subtitle={canManage ? "Gestão de gastos avulsos da empresa" : "Registre e acompanhe seus gastos avulsos"}
        actions={<Button onClick={openCreate}>+ Novo gasto</Button>}
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os gastos.
        </div>
      )}

      {query.data && (
        <>
          {canManage && query.data.totals && <KpiGrid totals={query.data.totals} />}
          <GastosTable expenses={query.data.expenses} canManage={canManage} onEdit={openEdit} />
        </>
      )}

      <GastoFormModal
        mode={editing ? "edit" : "create"}
        expense={editing}
        categories={query.data?.categories ?? []}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
