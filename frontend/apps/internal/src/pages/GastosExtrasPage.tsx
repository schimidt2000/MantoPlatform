import { useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, FileUpload, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import {
  useApproveGasto,
  useCreateGasto,
  useDeleteGasto,
  useGastosExtras,
  useGastosEventos,
  useLinkGastoEvento,
  useRejectGasto,
  type ExpenseStatus,
  type GastoExtra,
} from "../lib/gastos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

const STATUS_LABEL: Record<ExpenseStatus, string> = {
  pendente: "Pendente",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};

const STATUS_CLASS: Record<ExpenseStatus, string> = {
  pendente: "bg-amber-soft text-amber",
  aprovado: "bg-green-soft text-green",
  rejeitado: "bg-red-soft text-red",
};

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function NovoGastoForm({ categories }: { categories: string[] }) {
  const create = useCreateGasto();
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(categories[0] ?? "Outros");
  const [amount, setAmount] = useState(0);
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [disbursementType, setDisbursementType] = useState<"" | "reembolso" | "fornecedor">("");
  const [supplierName, setSupplierName] = useState("");
  const [supplierPix, setSupplierPix] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    if (!receipt) {
      setFieldErrors({ receipt: "Anexe a Nota Fiscal." });
      return;
    }
    setFieldErrors({});
    create.mutate(
      {
        description,
        category,
        amount,
        expense_date: expenseDate,
        notes,
        disbursement_type: disbursementType,
        supplier_name: disbursementType === "fornecedor" ? supplierName : undefined,
        supplier_pix: disbursementType === "fornecedor" ? supplierPix : undefined,
        receipt,
      },
      {
        onSuccess: () => {
          setDescription("");
          setAmount(0);
          setNotes("");
          setDisbursementType("");
          setSupplierName("");
          setSupplierPix("");
          setReceipt(null);
        },
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registrar gasto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className={LABEL}>Descrição</label>
          <input className={INPUT} value={description} onChange={(e) => setDescription(e.target.value)} />
          {fieldErrors.description && <p className="mt-1 text-xs text-red">{fieldErrors.description}</p>}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Categoria</label>
            <select className={INPUT} value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={LABEL}>Valor</label>
            <MoneyInput className={INPUT} value={amount} onValueChange={setAmount} />
            {fieldErrors.amount && <p className="mt-1 text-xs text-red">{fieldErrors.amount}</p>}
          </div>
        </div>
        <div>
          <label className={LABEL}>Data do gasto</label>
          <input
            type="date"
            className={INPUT}
            value={expenseDate}
            onChange={(e) => setExpenseDate(e.target.value)}
          />
        </div>
        <div>
          <label className={LABEL}>Desembolso (opcional)</label>
          <select
            className={INPUT}
            value={disbursementType}
            onChange={(e) => setDisbursementType(e.target.value as typeof disbursementType)}
          >
            <option value="">Sem desembolso definido</option>
            <option value="reembolso">Reembolso a funcionário</option>
            <option value="fornecedor">Pagamento a fornecedor</option>
          </select>
        </div>
        {disbursementType === "fornecedor" && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL}>Nome do fornecedor</label>
              <input className={INPUT} value={supplierName} onChange={(e) => setSupplierName(e.target.value)} />
              {fieldErrors.supplier_name && (
                <p className="mt-1 text-xs text-red">{fieldErrors.supplier_name}</p>
              )}
            </div>
            <div>
              <label className={LABEL}>Chave PIX (opcional)</label>
              <input className={INPUT} value={supplierPix} onChange={(e) => setSupplierPix(e.target.value)} />
            </div>
          </div>
        )}
        <div>
          <label className={LABEL}>Observações (opcional)</label>
          <textarea className={INPUT} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <FileUpload
          label="Nota Fiscal (foto ou PDF)"
          accept="image/*,application/pdf"
          maxSizeBytes={10 * 1024 * 1024}
          required
          error={fieldErrors.receipt}
          onChange={setReceipt}
        />
        <Button loading={create.isPending} onClick={handleSubmit}>
          Registrar gasto
        </Button>
        {create.isError && !Object.keys(fieldErrors).length && (
          <p className="text-sm text-red">Não foi possível registrar o gasto.</p>
        )}
      </CardContent>
    </Card>
  );
}

function EventoVincular({ expense }: { expense: GastoExtra }) {
  const [date, setDate] = useState(expense.expense_date);
  const eventos = useGastosEventos(date);
  const link = useLinkGastoEvento();

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
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

function GastoCard({ expense, isSuperadmin }: { expense: GastoExtra; isSuperadmin: boolean }) {
  const approve = useApproveGasto();
  const reject = useRejectGasto();
  const del = useDeleteGasto();
  const [showLink, setShowLink] = useState(false);

  const canDelete = isSuperadmin || expense.status === "pendente";

  const handleReject = () => {
    const motivo = window.prompt("Motivo da rejeição (opcional):") ?? "";
    reject.mutate({ id: expense.id, motivo });
  };

  const handleDelete = () => {
    if (!window.confirm(`Excluir o gasto "${expense.description}"?`)) return;
    del.mutate(expense.id);
  };

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-medium text-ink">{expense.description}</p>
            <p className="text-xs text-muted">
              {expense.category} · {formatDate(expense.expense_date)}
              {expense.created_by_name && ` · ${expense.created_by_name}`}
            </p>
          </div>
          <div className="text-right">
            <p className="font-medium tabular-nums text-ink">{brl(expense.amount)}</p>
            <span className={`rounded-md px-2 py-0.5 text-xs ${STATUS_CLASS[expense.status]}`}>
              {STATUS_LABEL[expense.status]}
            </span>
          </div>
        </div>
        {expense.notes && <p className="text-sm text-muted">{expense.notes}</p>}
        {expense.receipt_url && (
          <a
            href={expense.receipt_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-accent hover:underline"
          >
            Ver Nota Fiscal
          </a>
        )}
        <div className="flex flex-wrap gap-2 pt-1">
          {isSuperadmin && expense.status === "pendente" && (
            <>
              <Button size="sm" loading={approve.isPending} onClick={() => approve.mutate(expense.id)}>
                Aprovar
              </Button>
              <Button size="sm" variant="ghost" loading={reject.isPending} onClick={handleReject}>
                Rejeitar
              </Button>
            </>
          )}
          {isSuperadmin && (
            <Button size="sm" variant="ghost" onClick={() => setShowLink((v) => !v)}>
              Vincular evento
            </Button>
          )}
          {canDelete && (
            <Button size="sm" variant="ghost" loading={del.isPending} onClick={handleDelete}>
              Excluir
            </Button>
          )}
        </div>
        {showLink && <EventoVincular expense={expense} />}
      </CardContent>
    </Card>
  );
}

export function GastosExtrasPage() {
  const query = useGastosExtras();

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Gastos Extras"
        subtitle="Registre e acompanhe gastos avulsos da empresa"
        className="mb-0"
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
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
          <NovoGastoForm categories={query.data.categories} />
          {query.data.expenses.length === 0 && (
            <p className="text-sm text-muted">Nenhum gasto registrado ainda.</p>
          )}
          <div className="space-y-2">
            {query.data.expenses.map((e) => (
              <GastoCard key={e.id} expense={e} isSuperadmin={query.data.is_superadmin} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
