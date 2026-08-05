import { useState, type ReactNode } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { hojeYmd } from "../lib/horaLocal";
import {
  useCreateRecorrente,
  useDeleteEntry,
  useDeleteRecorrente,
  useFillEntry,
  useGastosRecorrentes,
  usePayEntry,
  useRecorrenteHistorico,
  useReopenEntry,
  useSkipEntry,
  useToggleRecorrente,
  useUpdateRecorrente,
  type CreateRecorrenteInput,
  type GastosRecorrentesResponse,
  type RecurringEntry,
  type RecurringExpenseItem,
  type RecurringFrequency,
  type RecurringType,
} from "../lib/gastos";

const LABEL = "mb-1 block text-[11px] font-bold uppercase tracking-wide text-muted";
const INPUT = "h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

const FREQUENCIES: RecurringFrequency[] = ["mensal", "semanal", "quinzenal", "anual"];
const WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

/** Tipos com formulário/seções de conta recorrente (o "programado" tem fluxo próprio). */
const CONTA_TYPES: Exclude<RecurringType, "programado">[] = [
  "variavel",
  "debito_automatico",
  "assinatura",
];

const SECTION_TITLES: Record<RecurringType, string> = {
  variavel: "💧 Contas Variáveis",
  debito_automatico: "🏦 Débito Automático",
  assinatura: "💳 Assinaturas (Cartão)",
  programado: "📆 Pagamentos Programados",
};

const SECTION_HINTS: Record<RecurringType, string> = {
  variavel: "Valor oscila mês a mês (água, luz, gás) — precisa ser preenchido quando a conta chega.",
  debito_automatico: "Valor fixo debitado direto em conta — lançamento do mês gerado sozinho.",
  assinatura: "Assinaturas de SaaS e serviços cobradas no cartão de crédito.",
  programado: "Parcelas com data e valor próprios, fora do ciclo automático.",
};

const ENTRY_BADGE: Record<RecurringEntry["status"], { label: string; className: string }> = {
  a_pagar: { label: "a pagar", className: "bg-red-soft text-red" },
  pago: { label: "pago", className: "bg-green-soft text-green" },
  registrado: { label: "registrado", className: "bg-blue-soft text-blue" },
  pulado: { label: "pulado", className: "bg-surface-2 text-muted" },
};

function brl(v: number | null | undefined): string {
  return v == null ? "—" : `R$ ${formatBRL(v)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR");
}

/** "2026-07" → "07/2026" (rótulo do mês de referência exibido nas colunas/seções). */
function monthLabel(monthRef: string): string {
  const [year, month] = monthRef.split("-");
  return `${month}/${year}`;
}

function currentMonthRef(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

// ══════════════════════════════════════════════════════════════════
//  Confirmação de ação destrutiva/irreversível (Princípio V)
// ══════════════════════════════════════════════════════════════════

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  destructive?: boolean;
  pending: boolean;
  error?: string | null;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
}

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = false,
  pending,
  error,
  onConfirm,
  onOpenChange,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="text-sm text-muted">{description}</div>
        {error && (
          <p className="mt-3 rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancelar
          </Button>
          <Button
            className={destructive ? "bg-red hover:bg-red/90" : undefined}
            loading={pending}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Formulário de criação
// ══════════════════════════════════════════════════════════════════

function NovaContaForm() {
  const create = useCreateRecorrente();
  const [name, setName] = useState("");
  const [expenseType, setExpenseType] = useState<RecurringType>("variavel");
  const [frequency, setFrequency] = useState<RecurringFrequency>("mensal");
  const [dueDay, setDueDay] = useState(10);
  const [weekday, setWeekday] = useState(0);
  const [refMode, setRefMode] = useState<"faixa" | "exato">("faixa");
  const [amount, setAmount] = useState(0);
  const [amountMin, setAmountMin] = useState(0);
  const [amountMax, setAmountMax] = useState(0);
  const [startDate, setStartDate] = useState(hojeYmd());
  const [endDate, setEndDate] = useState("");
  const [defaultPix, setDefaultPix] = useState("");
  const [cardName, setCardName] = useState("");
  const [notes, setNotes] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const isVariavel = expenseType === "variavel";

  const handleSubmit = () => {
    setFieldErrors({});
    setFormError(null);
    const payload: CreateRecorrenteInput = {
      name,
      expense_type: expenseType,
      frequency,
      weekday: frequency === "semanal" ? weekday : undefined,
      due_day: frequency !== "semanal" ? dueDay : undefined,
      // Variável com "valor exato" também usa `amount`; com "faixa", min/max.
      amount: !isVariavel || refMode === "exato" ? amount : undefined,
      ref_mode: isVariavel ? refMode : "exato",
      amount_min: isVariavel && refMode === "faixa" ? amountMin : undefined,
      amount_max: isVariavel && refMode === "faixa" ? amountMax : undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      default_pix: defaultPix || undefined,
      card_name: expenseType === "assinatura" ? cardName || undefined : undefined,
      notes: notes || undefined,
    };
    create.mutate(payload, {
      onSuccess: () => {
        setName("");
        setAmount(0);
        setAmountMin(0);
        setAmountMax(0);
        setDefaultPix("");
        setCardName("");
        setNotes("");
      },
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) {
          setFieldErrors(err.fields);
        }
        setFormError(err instanceof Error ? err.message : "Não foi possível cadastrar a conta.");
      },
    });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Nova conta recorrente</CardTitle>
        <p className="text-xs text-muted">
          Contas fixas da empresa: variáveis (luz/água/gás), débito automático e assinaturas.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2">
            <label className={LABEL} htmlFor="conta-nome">
              Nome*
            </label>
            <input
              id="conta-nome"
              className={INPUT}
              value={name}
              placeholder="Conta de Luz"
              onChange={(e) => setName(e.target.value)}
            />
            {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
          </div>
          <div>
            <label className={LABEL} htmlFor="conta-tipo">
              Tipo*
            </label>
            <select
              id="conta-tipo"
              className={INPUT}
              value={expenseType}
              onChange={(e) => setExpenseType(e.target.value as RecurringType)}
            >
              <option value="variavel">Conta variável</option>
              <option value="debito_automatico">Débito automático</option>
              <option value="assinatura">Assinatura (cartão)</option>
            </select>
          </div>
          <div>
            <label className={LABEL} htmlFor="conta-freq">
              Frequência*
            </label>
            <select
              id="conta-freq"
              className={INPUT}
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {frequency === "semanal" ? (
            <div>
              <label className={LABEL} htmlFor="conta-weekday">
                Dia da semana*
              </label>
              <select
                id="conta-weekday"
                className={INPUT}
                value={weekday}
                onChange={(e) => setWeekday(Number(e.target.value))}
              >
                {WEEKDAYS.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className={LABEL} htmlFor="conta-dia">
                Dia do vencimento (1–31)*
              </label>
              <input
                id="conta-dia"
                type="number"
                min={1}
                max={31}
                className={INPUT}
                value={dueDay}
                onChange={(e) => setDueDay(Number(e.target.value))}
              />
              {fieldErrors.due_day && (
                <p className="mt-1 text-xs text-red">{fieldErrors.due_day}</p>
              )}
            </div>
          )}

          <div>
            <label className={LABEL} htmlFor="conta-inicio">
              Início*
            </label>
            <input
              id="conta-inicio"
              type="date"
              className={INPUT}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="conta-fim">
              Fim (vazio = eterna)
            </label>
            <input
              id="conta-fim"
              type="date"
              className={INPUT}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          {isVariavel ? (
            <>
              <div>
                <span className={LABEL}>Referência</span>
                <div className="flex h-9 items-center gap-3 text-xs text-ink">
                  <label className="flex items-center gap-1">
                    <input
                      type="radio"
                      name="ref_mode"
                      checked={refMode === "faixa"}
                      onChange={() => setRefMode("faixa")}
                    />
                    Faixa
                  </label>
                  <label className="flex items-center gap-1">
                    <input
                      type="radio"
                      name="ref_mode"
                      checked={refMode === "exato"}
                      onChange={() => setRefMode("exato")}
                    />
                    Valor exato
                  </label>
                </div>
              </div>
              {refMode === "faixa" ? (
                <div className="sm:col-span-2">
                  <span className={LABEL}>Faixa esperada (R$)</span>
                  <div className="flex items-center gap-2">
                    <MoneyInput
                      className={INPUT}
                      value={amountMin}
                      onValueChange={setAmountMin}
                      aria-label="Valor mínimo esperado"
                    />
                    <span className="text-muted">–</span>
                    <MoneyInput
                      className={INPUT}
                      value={amountMax}
                      onValueChange={setAmountMax}
                      aria-label="Valor máximo esperado"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className={LABEL} htmlFor="conta-valor-exato">
                    Valor esperado (R$)
                  </label>
                  <MoneyInput
                    id="conta-valor-exato"
                    className={INPUT}
                    value={amount}
                    onValueChange={setAmount}
                  />
                </div>
              )}
            </>
          ) : (
            <div>
              <label className={LABEL} htmlFor="conta-valor">
                Valor fixo (R$)*
              </label>
              <MoneyInput
                id="conta-valor"
                className={INPUT}
                value={amount}
                onValueChange={setAmount}
              />
              {fieldErrors.amount && <p className="mt-1 text-xs text-red">{fieldErrors.amount}</p>}
            </div>
          )}

          {expenseType === "assinatura" && (
            <div>
              <label className={LABEL} htmlFor="conta-cartao">
                Cartão
              </label>
              <input
                id="conta-cartao"
                className={INPUT}
                value={cardName}
                placeholder="Inter Prime"
                onChange={(e) => setCardName(e.target.value)}
              />
            </div>
          )}

          <div>
            <label className={LABEL} htmlFor="conta-pix">
              PIX padrão
            </label>
            <input
              id="conta-pix"
              className={INPUT}
              value={defaultPix}
              placeholder="opcional"
              onChange={(e) => setDefaultPix(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className={LABEL} htmlFor="conta-notas">
              Observações
            </label>
            <input
              id="conta-notas"
              className={INPUT}
              value={notes}
              placeholder="opcional"
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        {formError && (
          <p className="rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            {formError}
          </p>
        )}
        <div className="flex items-center gap-3">
          <Button loading={create.isPending} onClick={handleSubmit}>
            Cadastrar conta
          </Button>
          <span aria-live="polite" className="text-xs text-green">
            {create.isSuccess ? "Conta cadastrada ✓" : ""}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Dialogs de linha: preencher, editar, histórico
// ══════════════════════════════════════════════════════════════════

interface PreencherDialogProps {
  conta: RecurringExpenseItem;
  monthRef: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function PreencherDialog({ conta, monthRef, open, onOpenChange }: PreencherDialogProps) {
  const fill = useFillEntry();
  const [amount, setAmount] = useState(conta.entry?.amount ?? conta.amount ?? 0);
  const [pix, setPix] = useState(conta.entry?.pix ?? conta.default_pix ?? "");
  const [dueDate, setDueDate] = useState(conta.entry?.due_date ?? "");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = () => {
    setError(null);
    if (amount <= 0) {
      setError("Informe o valor exato da conta (ex.: 512,30).");
      return;
    }
    fill.mutate(
      {
        contaId: conta.id,
        amount,
        pix: pix || undefined,
        due_date: dueDate || undefined,
        month_ref: monthRef,
      },
      {
        onSuccess: () => onOpenChange(false),
        onError: (err) =>
          setError(err instanceof Error ? err.message : "Não foi possível salvar o lançamento."),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>Preencher — {conta.name}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted">
          Valor real da conta em {monthLabel(monthRef)}
          {conta.expected_label ? ` · ${conta.expected_label}` : ""}. Ao salvar, o lançamento entra
          na planilha de pagamentos e no DRE do mês.
        </p>
        <div className="mt-4 space-y-3">
          <div>
            <label className={LABEL} htmlFor="fill-amount">
              Valor da conta (R$)*
            </label>
            <MoneyInput
              id="fill-amount"
              className={INPUT}
              value={amount}
              onValueChange={setAmount}
              autoFocus
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="fill-pix">
              Chave PIX (opcional)
            </label>
            <input
              id="fill-pix"
              className={INPUT}
              value={pix}
              onChange={(e) => setPix(e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="fill-due">
              Vencimento (opcional)
            </label>
            <input
              id="fill-due"
              type="date"
              className={INPUT}
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
        </div>
        {error && (
          <p className="mt-3 rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={fill.isPending}>
            Cancelar
          </Button>
          <Button loading={fill.isPending} onClick={handleSubmit}>
            Salvar lançamento
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface EditarDialogProps {
  conta: RecurringExpenseItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditarDialog({ conta, open, onOpenChange }: EditarDialogProps) {
  const update = useUpdateRecorrente();
  const [name, setName] = useState(conta.name);
  const [dueDay, setDueDay] = useState(conta.due_day);
  const [weekday, setWeekday] = useState(conta.weekday ?? 0);
  const [frequency, setFrequency] = useState<RecurringFrequency>(conta.frequency);
  const [amount, setAmount] = useState(conta.amount ?? 0);
  const [amountMin, setAmountMin] = useState(conta.amount_min ?? 0);
  const [amountMax, setAmountMax] = useState(conta.amount_max ?? 0);
  const [defaultPix, setDefaultPix] = useState(conta.default_pix ?? "");
  const [cardName, setCardName] = useState(conta.card_name ?? "");
  const [notes, setNotes] = useState(conta.notes ?? "");
  const [endDate, setEndDate] = useState(conta.end_date ?? "");
  const [error, setError] = useState<string | null>(null);

  const isVariavel = conta.expense_type === "variavel";
  const useFaixa = isVariavel && conta.amount == null;

  const handleSubmit = () => {
    setError(null);
    update.mutate(
      {
        id: conta.id,
        name,
        expense_type: conta.expense_type,
        frequency,
        weekday: frequency === "semanal" ? weekday : undefined,
        due_day: frequency !== "semanal" ? dueDay : undefined,
        amount: !isVariavel || !useFaixa ? amount : undefined,
        ref_mode: useFaixa ? "faixa" : "exato",
        amount_min: useFaixa ? amountMin : undefined,
        amount_max: useFaixa ? amountMax : undefined,
        start_date: conta.start_date,
        end_date: endDate || undefined,
        default_pix: defaultPix || undefined,
        card_name: conta.expense_type === "assinatura" ? cardName || undefined : undefined,
        notes: notes || undefined,
      },
      {
        onSuccess: () => onOpenChange(false),
        onError: (err) =>
          setError(err instanceof Error ? err.message : "Não foi possível salvar a conta."),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open}>
        <DialogHeader>
          <DialogTitle>Editar conta</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted">
          Lançamentos já criados não mudam — a edição vale para os próximos meses.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className={LABEL} htmlFor="edit-nome">
              Nome
            </label>
            <input
              id="edit-nome"
              className={INPUT}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="edit-freq">
              Frequência
            </label>
            <select
              id="edit-freq"
              className={INPUT}
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </option>
              ))}
            </select>
          </div>
          {frequency === "semanal" ? (
            <div>
              <label className={LABEL} htmlFor="edit-weekday">
                Dia da semana
              </label>
              <select
                id="edit-weekday"
                className={INPUT}
                value={weekday}
                onChange={(e) => setWeekday(Number(e.target.value))}
              >
                {WEEKDAYS.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className={LABEL} htmlFor="edit-dia">
                Dia do vencimento
              </label>
              <input
                id="edit-dia"
                type="number"
                min={1}
                max={31}
                className={INPUT}
                value={dueDay}
                onChange={(e) => setDueDay(Number(e.target.value))}
              />
            </div>
          )}
          {useFaixa ? (
            <div className="sm:col-span-2">
              <span className={LABEL}>Faixa esperada (R$)</span>
              <div className="flex items-center gap-2">
                <MoneyInput
                  className={INPUT}
                  value={amountMin}
                  onValueChange={setAmountMin}
                  aria-label="Valor mínimo esperado"
                />
                <span className="text-muted">–</span>
                <MoneyInput
                  className={INPUT}
                  value={amountMax}
                  onValueChange={setAmountMax}
                  aria-label="Valor máximo esperado"
                />
              </div>
            </div>
          ) : (
            <div>
              <label className={LABEL} htmlFor="edit-valor">
                Valor (R$)
              </label>
              <MoneyInput
                id="edit-valor"
                className={INPUT}
                value={amount}
                onValueChange={setAmount}
              />
            </div>
          )}
          {conta.expense_type === "assinatura" && (
            <div>
              <label className={LABEL} htmlFor="edit-cartao">
                Cartão
              </label>
              <input
                id="edit-cartao"
                className={INPUT}
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
              />
            </div>
          )}
          <div>
            <label className={LABEL} htmlFor="edit-fim">
              Fim (vazio = eterna)
            </label>
            <input
              id="edit-fim"
              type="date"
              className={INPUT}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="edit-pix">
              PIX padrão
            </label>
            <input
              id="edit-pix"
              className={INPUT}
              value={defaultPix}
              onChange={(e) => setDefaultPix(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className={LABEL} htmlFor="edit-notas">
              Observações
            </label>
            <input
              id="edit-notas"
              className={INPUT}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>
        {error && (
          <p className="mt-3 rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={update.isPending}>
            Cancelar
          </Button>
          <Button loading={update.isPending} onClick={handleSubmit}>
            Salvar alterações
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface HistoricoDialogProps {
  conta: RecurringExpenseItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function HistoricoDialog({ conta, open, onOpenChange }: HistoricoDialogProps) {
  const query = useRecorrenteHistorico(open ? conta.id : null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Histórico — {conta.name}</DialogTitle>
        </DialogHeader>
        {query.isLoading && <Skeleton className="h-32 w-full" />}
        {query.isError && (
          <p className="rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            Não foi possível carregar o histórico.
          </p>
        )}
        {query.data &&
          (query.data.entries.length === 0 ? (
            <p className="text-sm text-muted">Nenhum lançamento registrado ainda.</p>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] font-bold uppercase text-muted">
                    <th className="py-1.5 pr-2">Mês</th>
                    <th className="py-1.5 pr-2">Vencimento</th>
                    <th className="py-1.5 pr-2 text-right">Valor</th>
                    <th className="py-1.5">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.entries.map((e) => (
                    <tr key={e.id} className="border-b border-line last:border-0">
                      <td className="py-1.5 pr-2 text-ink">{monthLabel(e.month_ref)}</td>
                      <td className="py-1.5 pr-2 text-muted">{formatDate(e.due_date)}</td>
                      <td className="py-1.5 pr-2 text-right tabular-nums text-ink">
                        {brl(e.amount)}
                      </td>
                      <td className="py-1.5">
                        <span
                          className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${ENTRY_BADGE[e.status].className}`}
                        >
                          {ENTRY_BADGE[e.status].label}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Célula de status do mês + linha da tabela
// ══════════════════════════════════════════════════════════════════

function StatusMesCell({ conta }: { conta: RecurringExpenseItem }) {
  const entry = conta.entry;

  if (!conta.is_active) return <span className="text-muted">—</span>;
  if (conta.occurrences === 0 && !entry) {
    return (
      <span className="text-xs text-muted" title="Fora da vigência ou do ciclo neste mês">
        fora do ciclo
      </span>
    );
  }
  if (!entry) {
    return conta.expense_type === "variavel" ? (
      <span className="rounded-md bg-gold-soft px-1.5 py-0.5 text-[10px] font-bold text-gold">
        aguardando valor
      </span>
    ) : (
      <span className="text-muted">—</span>
    );
  }

  const badge = ENTRY_BADGE[entry.status];
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${badge.className}`}>
        {badge.label}
      </span>
      {entry.status !== "pulado" && (
        <span className="whitespace-nowrap tabular-nums text-ink">{brl(entry.amount)}</span>
      )}
      {entry.out_of_range && (
        <span className="font-bold text-red" title="Valor fora da faixa esperada">
          ⚠
        </span>
      )}
      {entry.due_date && entry.status === "a_pagar" && (
        <span className="w-full text-[11px] text-muted">vence {formatDate(entry.due_date)}</span>
      )}
    </div>
  );
}

interface ContaRowProps {
  conta: RecurringExpenseItem;
  monthRef: string;
  isCurrentMonth: boolean;
  showCard: boolean;
}

/** Botões da coluna de ações: compactos para a densidade da planilha clássica. */
const ROW_BTN = "h-7 px-2 text-[11px]";

function ContaRow({ conta, monthRef, isCurrentMonth, showCard }: ContaRowProps) {
  const skip = useSkipEntry();
  const pay = usePayEntry();
  const reopen = useReopenEntry();
  const toggle = useToggleRecorrente();
  const del = useDeleteRecorrente();

  const [dialog, setDialog] = useState<"preencher" | "editar" | "historico" | null>(null);
  const [confirm, setConfirm] = useState<"pular" | "reabrir" | "toggle" | "excluir" | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const entry = conta.entry;
  const isVariavel = conta.expense_type === "variavel";
  const podePreencher =
    conta.is_active &&
    isVariavel &&
    isCurrentMonth &&
    (conta.occurrences ?? 0) > 0 &&
    (!entry || entry.status === "a_pagar" || entry.status === "pulado");
  const preenchimentoPendente = podePreencher && (!entry || entry.status === "pulado");

  const closeConfirm = () => {
    setConfirm(null);
    setConfirmError(null);
  };

  const onMutationError = (err: unknown) =>
    setConfirmError(err instanceof Error ? err.message : "Não foi possível concluir a ação.");

  return (
    <>
      <tr className={`border-b border-line last:border-0 ${conta.is_active ? "" : "opacity-60"}`}>
        <td className="px-3 py-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`font-semibold ${conta.is_active ? "text-ink" : "text-muted line-through"}`}>
              {conta.name}
            </span>
            {!conta.is_active && (
              <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-bold text-muted">
                inativa
              </span>
            )}
          </div>
          {conta.notes && <div className="text-[11px] text-muted">{conta.notes}</div>}
        </td>
        <td className="whitespace-nowrap px-3 py-2 text-muted">{conta.dia_label}</td>
        <td className="whitespace-nowrap px-3 py-2">
          <span className="text-ink">
            {conta.frequency.charAt(0).toUpperCase() + conta.frequency.slice(1)}
          </span>
          <div className="text-[11px] text-muted">{conta.vigencia_label}</div>
        </td>
        <td className="whitespace-nowrap px-3 py-2 text-ink">
          {isVariavel ? (conta.expected_label ?? "—") : brl(conta.amount)}
        </td>
        {showCard && (
          <td className="whitespace-nowrap px-3 py-2 text-ink">{conta.card_name || "—"}</td>
        )}
        <td className="px-3 py-2">
          <StatusMesCell conta={conta} />
        </td>
        <td className="px-3 py-2">
          <div className="flex flex-wrap justify-end gap-1">
            {podePreencher && (
              <Button
                size="sm"
                className={ROW_BTN}
                variant={preenchimentoPendente ? "default" : "outline"}
                onClick={() => setDialog("preencher")}
              >
                Preencher
              </Button>
            )}
            {conta.is_active && isVariavel && isCurrentMonth && !entry && (
              <Button size="sm" variant="ghost" className={ROW_BTN} onClick={() => setConfirm("pular")}>
                Pular mês
              </Button>
            )}
            {entry?.status === "a_pagar" && (
              <Button
                size="sm"
                variant="outline"
                className={ROW_BTN}
                loading={pay.isPending}
                onClick={() => pay.mutate(entry.id)}
              >
                Pagar
              </Button>
            )}
            {(entry?.status === "pago" || entry?.status === "pulado") && (
              <Button size="sm" variant="ghost" className={ROW_BTN} onClick={() => setConfirm("reabrir")}>
                Reabrir
              </Button>
            )}
            <Button size="sm" variant="ghost" className={ROW_BTN} onClick={() => setDialog("historico")}>
              Histórico
            </Button>
            <Button size="sm" variant="ghost" className={ROW_BTN} onClick={() => setDialog("editar")}>
              Editar
            </Button>
            <Button size="sm" variant="ghost" className={ROW_BTN} onClick={() => setConfirm("toggle")}>
              {conta.is_active ? "Desativar" : "Reativar"}
            </Button>
            {!conta.has_entries && (
              <Button
                size="sm"
                variant="ghost"
                className={`${ROW_BTN} text-red`}
                onClick={() => setConfirm("excluir")}
              >
                Excluir
              </Button>
            )}
          </div>
          <span aria-live="polite" className="sr-only">
            {pay.isPending ? "Marcando como pago…" : ""}
          </span>
        </td>
      </tr>

      {dialog === "preencher" && (
        <PreencherDialog
          conta={conta}
          monthRef={monthRef}
          open
          onOpenChange={(o) => !o && setDialog(null)}
        />
      )}
      {dialog === "editar" && (
        <EditarDialog conta={conta} open onOpenChange={(o) => !o && setDialog(null)} />
      )}
      {dialog === "historico" && (
        <HistoricoDialog conta={conta} open onOpenChange={(o) => !o && setDialog(null)} />
      )}

      <ConfirmDialog
        open={confirm === "pular"}
        title="Pular o mês"
        description={`Marcar "${conta.name}" como pulada em ${monthLabel(monthRef)} (a conta não veio)?`}
        confirmLabel="Pular mês"
        pending={skip.isPending}
        error={confirmError}
        onOpenChange={(o) => !o && closeConfirm()}
        onConfirm={() =>
          skip.mutate(
            { contaId: conta.id, month_ref: monthRef },
            { onSuccess: closeConfirm, onError: onMutationError },
          )
        }
      />
      <ConfirmDialog
        open={confirm === "reabrir"}
        title="Reabrir lançamento"
        description={`Reabrir o lançamento de "${conta.name}" em ${monthLabel(monthRef)}? Um lançamento pulado é removido; um pago volta para "a pagar".`}
        confirmLabel="Reabrir"
        pending={reopen.isPending}
        error={confirmError}
        onOpenChange={(o) => !o && closeConfirm()}
        onConfirm={() =>
          entry && reopen.mutate(entry.id, { onSuccess: closeConfirm, onError: onMutationError })
        }
      />
      <ConfirmDialog
        open={confirm === "toggle"}
        title={conta.is_active ? "Desativar conta" : "Reativar conta"}
        description={
          conta.is_active
            ? `Desativar "${conta.name}"? Ela para de gerar alertas e lançamentos novos.`
            : `Reativar "${conta.name}"? Ela volta a gerar lançamentos no ciclo.`
        }
        confirmLabel={conta.is_active ? "Desativar" : "Reativar"}
        pending={toggle.isPending}
        error={confirmError}
        onOpenChange={(o) => !o && closeConfirm()}
        onConfirm={() =>
          toggle.mutate(conta.id, { onSuccess: closeConfirm, onError: onMutationError })
        }
      />
      <ConfirmDialog
        open={confirm === "excluir"}
        title="Excluir conta"
        description={`Excluir "${conta.name}"? Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir"
        destructive
        pending={del.isPending}
        error={confirmError}
        onOpenChange={(o) => !o && closeConfirm()}
        onConfirm={() => del.mutate(conta.id, { onSuccess: closeConfirm, onError: onMutationError })}
      />
    </>
  );
}

interface ContaSectionProps {
  type: Exclude<RecurringType, "programado">;
  contas: RecurringExpenseItem[];
  monthRef: string;
  isCurrentMonth: boolean;
  soma: number;
}

function ContaSection({ type, contas, monthRef, isCurrentMonth, soma }: ContaSectionProps) {
  const showCard = type === "assinatura";
  const refColumn = type === "variavel" ? "Faixa esperada" : "Valor";

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 pb-2">
        <div>
          <CardTitle className="text-base">{SECTION_TITLES[type]}</CardTitle>
          <p className="text-xs text-muted">{SECTION_HINTS[type]}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[11px] uppercase text-muted">Estimativa</p>
          <p className="font-bold tabular-nums text-ink">
            {brl(soma)}
            <span className="text-[11px] font-normal text-muted">
              /mês{type === "variavel" ? " (teto)" : ""}
            </span>
          </p>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {contas.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-muted">Nenhuma conta cadastrada neste grupo.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-[13px]">
              <thead>
                <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
                  <th className="px-3 py-2">Conta</th>
                  <th className="px-3 py-2">Vencimento</th>
                  <th className="px-3 py-2">Frequência</th>
                  <th className="px-3 py-2">{refColumn}</th>
                  {showCard && <th className="px-3 py-2">Cartão</th>}
                  <th className="px-3 py-2">Mês {monthLabel(monthRef)}</th>
                  <th className="px-3 py-2 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {contas.map((c) => (
                  <ContaRow
                    key={c.id}
                    conta={c}
                    monthRef={monthRef}
                    isCurrentMonth={isCurrentMonth}
                    showCard={showCard}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Pagamentos programados (parcelas explícitas — feature 121)
// ══════════════════════════════════════════════════════════════════

function ProgramadoSection({ contas, total }: { contas: RecurringExpenseItem[]; total: number }) {
  const pay = usePayEntry();
  const reopen = useReopenEntry();
  const deleteEntry = useDeleteEntry();
  const [toDelete, setToDelete] = useState<RecurringEntry | null>(null);

  if (contas.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 pb-2">
        <div>
          <CardTitle className="text-base">{SECTION_TITLES.programado}</CardTitle>
          <p className="text-xs text-muted">{SECTION_HINTS.programado}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[11px] uppercase text-muted">A pagar</p>
          <p className="font-bold tabular-nums text-ink">{brl(total)}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {contas.map((c) => (
          <div key={c.id} className={`rounded-md border border-line p-3 ${c.is_active ? "" : "opacity-60"}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-semibold text-ink">{c.name}</span>
              <span className="text-xs text-muted">{c.parcelas_summary}</span>
            </div>
            {c.notes && <p className="text-[11px] text-muted">{c.notes}</p>}
            <table className="mt-2 w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-line text-left text-[10px] font-bold uppercase text-muted">
                  <th className="py-1 pr-2">Data</th>
                  <th className="py-1 pr-2 text-right">Valor</th>
                  <th className="py-1 pr-2">Situação</th>
                  <th className="py-1 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {(c.entries ?? []).map((e) => (
                  <tr key={e.id} className="border-b border-line last:border-0">
                    <td className="py-1.5 pr-2 text-ink">
                      {e.due_date ? formatDate(e.due_date) : monthLabel(e.month_ref)}
                    </td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-ink">{brl(e.amount)}</td>
                    <td className="py-1.5 pr-2">
                      <span
                        className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${ENTRY_BADGE[e.status].className}`}
                      >
                        {ENTRY_BADGE[e.status].label}
                      </span>
                    </td>
                    <td className="py-1.5 text-right">
                      <div className="flex justify-end gap-1">
                        {e.status === "a_pagar" ? (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              loading={pay.isPending}
                              onClick={() => pay.mutate(e.id)}
                            >
                              Pagar
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red"
                              onClick={() => setToDelete(e)}
                            >
                              Excluir parcela
                            </Button>
                          </>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={reopen.isPending}
                            onClick={() => reopen.mutate(e.id)}
                          >
                            Reabrir
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </CardContent>

      <ConfirmDialog
        open={toDelete !== null}
        title="Excluir parcela"
        description={`Excluir a parcela de ${brl(toDelete?.amount ?? null)}? Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir parcela"
        destructive
        pending={deleteEntry.isPending}
        onOpenChange={(o) => !o && setToDelete(null)}
        onConfirm={() =>
          toDelete && deleteEntry.mutate(toDelete.id, { onSuccess: () => setToDelete(null) })
        }
      />
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Página
// ══════════════════════════════════════════════════════════════════

function ResumoCards({ data }: { data: GastosRecorrentesResponse }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {CONTA_TYPES.map((t) => (
        <Card key={t} className="p-4">
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted">
            {data.type_labels[t]}
          </p>
          <p className="mt-1 text-xl font-extrabold tabular-nums text-ink">
            {brl(data.somas[t])}
            <span className="ml-1 text-[11px] font-normal text-muted">
              /mês{t === "variavel" ? " (teto)" : ""}
            </span>
          </p>
        </Card>
      ))}
      <Card className="p-4">
        <p className="text-[11px] font-bold uppercase tracking-wide text-muted">
          Pagamentos programados
        </p>
        <p className="mt-1 text-xl font-extrabold tabular-nums text-ink">
          {brl(data.programado_pendente_total)}
          <span className="ml-1 text-[11px] font-normal text-muted">a pagar</span>
        </p>
      </Card>
    </div>
  );
}

export function GastosRecorrentesPage() {
  const [monthRef, setMonthRef] = useState(currentMonthRef());
  const query = useGastosRecorrentes(monthRef);
  const data = query.data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Gastos Recorrentes"
        subtitle="Contas variáveis, débitos automáticos e assinaturas da empresa"
        className="mb-0"
      />

      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="month"
          value={monthRef}
          onChange={(e) => setMonthRef(e.target.value || currentMonthRef())}
          className="h-9 w-40"
          aria-label="Mês de referência"
        />
        {data && !data.is_current_month && (
          <Button size="sm" variant="outline" onClick={() => setMonthRef(currentMonthRef())}>
            Voltar ao mês atual
          </Button>
        )}
      </div>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as contas recorrentes.
        </div>
      )}

      {data && (
        <>
          <ResumoCards data={data} />

          {data.alerts.length > 0 && (
            <div className="rounded-md bg-gold-soft px-4 py-3 text-sm text-gold" role="status">
              {data.alerts.length} conta(s) precisam de atenção este mês:{" "}
              {data.alerts.map((a) => a.name).join(", ")}.
            </div>
          )}

          <NovaContaForm />

          {CONTA_TYPES.map((t) => (
            <ContaSection
              key={t}
              type={t}
              contas={data.grupos[t] ?? []}
              monthRef={data.month_ref}
              isCurrentMonth={data.is_current_month}
              soma={data.somas[t] ?? 0}
            />
          ))}

          <ProgramadoSection
            contas={data.grupos.programado ?? []}
            total={data.programado_pendente_total}
          />
        </>
      )}
    </div>
  );
}
