import { useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import {
  useCreateRecorrente,
  useDeleteEntry,
  useDeleteRecorrente,
  useFillEntry,
  useGastosRecorrentes,
  usePayEntry,
  useReopenEntry,
  useSkipEntry,
  useToggleRecorrente,
  type RecurringExpenseItem,
  type RecurringFrequency,
  type RecurringType,
} from "../lib/gastos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function brl(v: number | null): string {
  return v == null ? "—" : `R$ ${formatBRL(v)}`;
}

function NovaContaForm() {
  const create = useCreateRecorrente();
  const [name, setName] = useState("");
  const [expenseType, setExpenseType] = useState<RecurringType>("variavel");
  const [frequency, setFrequency] = useState<RecurringFrequency>("mensal");
  const [dueDay, setDueDay] = useState(10);
  const [weekday, setWeekday] = useState(0);
  const [amount, setAmount] = useState(0);
  const [defaultPix, setDefaultPix] = useState("");
  const [cardName, setCardName] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    setFieldErrors({});
    create.mutate(
      {
        name,
        expense_type: expenseType,
        frequency,
        weekday: frequency === "semanal" ? weekday : undefined,
        due_day: frequency !== "semanal" ? dueDay : undefined,
        amount: expenseType !== "variavel" ? amount : undefined,
        ref_mode: "faixa",
        default_pix: defaultPix || undefined,
        card_name: expenseType === "assinatura" ? cardName || undefined : undefined,
      },
      {
        onSuccess: () => {
          setName("");
          setAmount(0);
          setDefaultPix("");
          setCardName("");
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
        <CardTitle>Cadastrar conta recorrente</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className={LABEL}>Nome</label>
          <input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} />
          {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Tipo</label>
            <select
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
            <label className={LABEL}>Frequência</label>
            <select
              className={INPUT}
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
            >
              <option value="mensal">Mensal</option>
              <option value="semanal">Semanal</option>
              <option value="quinzenal">Quinzenal</option>
              <option value="anual">Anual</option>
            </select>
          </div>
        </div>
        {frequency === "semanal" ? (
          <div>
            <label className={LABEL}>Dia da semana</label>
            <select className={INPUT} value={weekday} onChange={(e) => setWeekday(Number(e.target.value))}>
              {["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"].map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label className={LABEL}>Dia do vencimento (1–31)</label>
            <input
              type="number"
              min={1}
              max={31}
              className={INPUT}
              value={dueDay}
              onChange={(e) => setDueDay(Number(e.target.value))}
            />
            {fieldErrors.due_day && <p className="mt-1 text-xs text-red">{fieldErrors.due_day}</p>}
          </div>
        )}
        {expenseType !== "variavel" && (
          <div>
            <label className={LABEL}>Valor fixo</label>
            <MoneyInput className={INPUT} value={amount} onValueChange={setAmount} />
            {fieldErrors.amount && <p className="mt-1 text-xs text-red">{fieldErrors.amount}</p>}
          </div>
        )}
        {expenseType === "assinatura" && (
          <div>
            <label className={LABEL}>Cartão</label>
            <input className={INPUT} value={cardName} onChange={(e) => setCardName(e.target.value)} />
          </div>
        )}
        <div>
          <label className={LABEL}>PIX padrão (opcional)</label>
          <input className={INPUT} value={defaultPix} onChange={(e) => setDefaultPix(e.target.value)} />
        </div>
        <Button loading={create.isPending} onClick={handleSubmit}>
          Cadastrar conta
        </Button>
      </CardContent>
    </Card>
  );
}

function EntryActions({ conta, monthRef }: { conta: RecurringExpenseItem; monthRef: string }) {
  const fill = useFillEntry();
  const skip = useSkipEntry();
  const pay = usePayEntry();
  const reopen = useReopenEntry();
  const deleteEntry = useDeleteEntry();
  const [amount, setAmount] = useState(conta.amount ?? 0);

  const entry = conta.entry;

  if (conta.expense_type === "variavel") {
    if (!entry || entry.status === "pulado") {
      return (
        <div className="mt-2 flex items-center gap-2">
          <MoneyInput
            className="h-8 w-32 rounded-md border border-line bg-panel px-2 text-xs"
            value={amount}
            onValueChange={setAmount}
          />
          <Button
            size="sm"
            loading={fill.isPending}
            onClick={() => fill.mutate({ contaId: conta.id, amount, month_ref: monthRef })}
          >
            Preencher
          </Button>
          <Button
            size="sm"
            variant="ghost"
            loading={skip.isPending}
            onClick={() => skip.mutate({ contaId: conta.id, month_ref: monthRef })}
          >
            Pular mês
          </Button>
        </div>
      );
    }
    if (entry.status === "a_pagar") {
      return (
        <div className="mt-2 flex gap-2">
          <Button size="sm" loading={pay.isPending} onClick={() => pay.mutate(entry.id)}>
            Marcar como pago
          </Button>
        </div>
      );
    }
    if (entry.status === "pago") {
      return (
        <div className="mt-2">
          <Button size="sm" variant="ghost" loading={reopen.isPending} onClick={() => reopen.mutate(entry.id)}>
            Reabrir
          </Button>
        </div>
      );
    }
  }

  if (conta.expense_type === "programado" && entry) {
    if (entry.status === "a_pagar") {
      return (
        <div className="mt-2 flex gap-2">
          <Button size="sm" loading={pay.isPending} onClick={() => pay.mutate(entry.id)}>
            Marcar como pago
          </Button>
          <Button
            size="sm"
            variant="ghost"
            loading={deleteEntry.isPending}
            onClick={() => {
              if (window.confirm("Excluir esta parcela?")) deleteEntry.mutate(entry.id);
            }}
          >
            Excluir parcela
          </Button>
        </div>
      );
    }
    if (entry.status === "pago") {
      return (
        <div className="mt-2">
          <Button size="sm" variant="ghost" loading={reopen.isPending} onClick={() => reopen.mutate(entry.id)}>
            Reabrir
          </Button>
        </div>
      );
    }
  }

  return null;
}

function ContaCard({ conta, monthRef }: { conta: RecurringExpenseItem; monthRef: string }) {
  const toggle = useToggleRecorrente();
  const del = useDeleteRecorrente();

  return (
    <Card>
      <CardContent className="space-y-1 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className={`font-medium ${conta.is_active ? "text-ink" : "text-muted line-through"}`}>
              {conta.name}
            </p>
            <p className="text-xs text-muted">
              {conta.frequency} · vencimento dia {conta.due_day}
            </p>
          </div>
          <p className="font-medium tabular-nums text-ink">
            {brl(conta.entry?.amount ?? conta.amount ?? conta.amount_max)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" variant="ghost" loading={toggle.isPending} onClick={() => toggle.mutate(conta.id)}>
            {conta.is_active ? "Desativar" : "Reativar"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            loading={del.isPending}
            onClick={() => {
              if (window.confirm(`Excluir "${conta.name}"?`)) del.mutate(conta.id);
            }}
          >
            Excluir
          </Button>
        </div>
        <EntryActions conta={conta} monthRef={monthRef} />
      </CardContent>
    </Card>
  );
}

export function GastosRecorrentesPage() {
  const query = useGastosRecorrentes();

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Gastos Recorrentes"
        subtitle="Contas variáveis, débitos automáticos e assinaturas"
        className="mb-0"
      />

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as contas recorrentes.
        </div>
      )}

      {query.data && (
        <>
          <NovaContaForm />

          {query.data.alerts.length > 0 && (
            <div className="rounded-md bg-amber-soft px-4 py-3 text-sm text-amber">
              {query.data.alerts.length} conta(s) precisam de atenção este mês.
            </div>
          )}

          {(Object.keys(query.data.grupos) as RecurringType[]).map((type) => {
            const items = query.data!.grupos[type];
            if (!items || items.length === 0) return null;
            return (
              <div key={type} className="space-y-2">
                <h3 className="text-sm font-medium text-muted">{query.data!.type_labels[type]}</h3>
                {items.map((c) => (
                  <ContaCard key={c.id} conta={c} monthRef={query.data!.month_ref} />
                ))}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
