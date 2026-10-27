import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import {
  AccordionRow,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  FileUpload,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { MoneyInput } from "@manto/money";
import { Modal } from "../components/Modal";
import { CartaoFiltro } from "../components/CartaoFiltro";
import { ListaDeGastos } from "../components/Gastos/GastoItemViews";
import { GastosFiltros, type MudancaDeFiltro } from "../components/Gastos/GastosFiltros";
import { hojeYmd } from "../lib/horaLocal";
import { brl, searchTerms } from "../lib/pagamentos";
import {
  SITUACAO_LABELS_GRUPO,
  SITUACAO_ORDEM,
  SITUACAO_TONE,
  SITUACOES_A_VISTA,
  filtrarGastos,
  lerFiltrosDaUrl,
  searchIndexOfGasto,
  situacaoDe,
  useCreateGasto,
  useGastosEventos,
  useGastosExtras,
  useGastosFuncionarios,
  useUpdateGasto,
  type GastoExtra,
  type GastoSituacao,
} from "../lib/gastos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** As chaves de `fields` que o formulário mostra no próprio campo; as outras vão ao rodapé. */
const CAMPOS_COM_LUGAR = new Set([
  "description",
  "amount",
  "receipt",
  "supplier_name",
  "reimburse_user_id",
  "category",
  "expense_date",
  "event_id",
]);

interface GastoFormValues {
  description: string;
  category: string;
  amount: number;
  expenseDate: string;
  notes: string;
  /** `cliente` = devolução à cliente (feature 306): só vem do cancelamento, nunca se escolhe aqui. */
  disbursementType: "" | "reembolso" | "fornecedor" | "cliente";
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
    disbursementType: (expense.disbursement_type ?? "") as GastoFormValues["disbursementType"],
    reimburseUserId: "",
    // Feature 306: a devolução à cliente carrega e reenvia nome e PIX — antes o "Salvar" os apagava.
    supplierName:
      expense.disbursement_type === "fornecedor" || expense.disbursement_type === "cliente"
        ? expense.payee_name
        : "",
    supplierPix:
      expense.disbursement_type === "fornecedor" || expense.disbursement_type === "cliente"
        ? expense.payee_pix
        : "",
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

  // Feature 306: a devolução à cliente não troca de tipo; nome e PIX seguem editáveis.
  if (values.disbursementType === "cliente") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-ink">
          <span className={LABEL}>Como será pago?</span>
          Devolução à cliente
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Quem recebe</label>
            <input
              className={INPUT}
              value={values.supplierName}
              onChange={(e) => onChange({ supplierName: e.target.value })}
            />
            {fieldErrors.supplier_name && <p className="mt-1 text-xs text-red">{fieldErrors.supplier_name}</p>}
          </div>
          <div>
            <label className={LABEL}>Chave PIX</label>
            <input
              className={INPUT}
              value={values.supplierPix}
              onChange={(e) => onChange({ supplierPix: e.target.value })}
            />
          </div>
        </div>
      </div>
    );
  }

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
  travado = false,
  vinculoAtual = null,
}: {
  values: GastoFormValues;
  onChange: (patch: Partial<GastoFormValues>) => void;
  /** Feature 306: o vínculo da devolução de um cancelado não muda por aqui. */
  travado?: boolean;
  /** O evento já ligado ao gasto: a lista é a da data escolhida e pode não trazê-lo. */
  vinculoAtual?: { id: number; titulo: string } | null;
}) {
  const eventos = useGastosEventos(values.eventDate);
  // Sem isto, o evento ligado de outra data aparecia como "Sem evento vinculado" — e, na devolução
  // travada (306), num campo que nem se pode mudar.
  const faltaNaLista =
    vinculoAtual !== null &&
    values.eventId === vinculoAtual.id &&
    !(eventos.data?.events ?? []).some((ev) => ev.id === vinculoAtual.id);
  return (
    <div>
      <label className={LABEL}>Vincular a um evento (opcional)</label>
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="date"
          className={INPUT}
          value={values.eventDate}
          disabled={travado}
          onChange={(e) => onChange({ eventDate: e.target.value })}
        />
        <select
          className={INPUT}
          value={values.eventId}
          disabled={travado}
          onChange={(e) => onChange({ eventId: e.target.value ? Number(e.target.value) : "" })}
        >
          <option value="">Sem evento vinculado</option>
          {faltaNaLista && vinculoAtual && <option value={vinculoAtual.id}>{vinculoAtual.titulo}</option>}
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
    supplier_name:
      values.disbursementType === "fornecedor" || values.disbursementType === "cliente"
        ? values.supplierName
        : undefined,
    supplier_pix:
      values.disbursementType === "fornecedor" || values.disbursementType === "cliente"
        ? values.supplierPix
        : undefined,
    event_id: values.eventId === "" ? undefined : values.eventId,
  });

  const handleCreate = () => {
    if (!receipt) {
      setFieldErrors({ receipt: "Insira a nota fiscal." });
      return;
    }
    setFieldErrors({});
    create.mutate(
      {
        ...buildPayload(),
        // A devolução à cliente nunca nasce aqui (feature 306): o formulário de criação nem a oferece.
        disbursement_type: values.disbursementType === "cliente" ? "" : values.disbursementType,
        notes: values.notes,
        receipt,
      },
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
  const erroDoServidor = (create.error ?? update.error) as Error | null;
  // Toda recusa do servidor aparece: no campo que a tela tem, ou no rodapé quando a chave não tem
  // lugar (Constituição V — o 409 `devolucao_travada` vinha só com `fields` e sumia calado).
  const semLugar = Object.keys(fieldErrors).some((k) => !CAMPOS_COM_LUGAR.has(k));
  const genericError =
    (create.isError || update.isError) && (semLugar || !Object.keys(fieldErrors).length)
      ? erroDoServidor?.message || "Não foi possível salvar o gasto."
      : null;
  const eventoDaTrava =
    erroDoServidor instanceof ApiRequestError && erroDoServidor.details.codigo === "devolucao_travada"
      ? Number(erroDoServidor.details.event_id) || null
      : null;
  // Feature 306: a devolução de um evento cancelado — valor, data, categoria e vínculo só mudam pelo
  // "Alterar devolução" na tela do evento; nome, PIX e descrição ficam livres.
  const travado = mode === "edit" && Boolean(expense?.locked);

  return (
    <Modal open={open} onClose={onClose} title={mode === "create" ? "Novo gasto" : "Editar gasto"}>
      <div className="space-y-3">
        {travado && expense?.event_id && (
          <p className="rounded-md border border-gold/40 bg-gold-soft p-2 text-sm text-ink" role="note">
            Devolução de evento cancelado: valor, data, categoria e vínculo mudam só pelo “Alterar devolução”{" "}
            <Link to={`/events/${expense.event_id}?aba=comercial`} className="text-blue underline">
              na tela do evento
            </Link>
            .
          </p>
        )}
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
            <select
              className={INPUT}
              value={values.category}
              disabled={travado}
              onChange={(e) => patch({ category: e.target.value })}
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            {fieldErrors.category && (
              <p className="mt-1 text-xs text-red" role="alert">
                {fieldErrors.category}
              </p>
            )}
          </div>
          <div>
            <label className={LABEL}>Valor (R$)</label>
            <MoneyInput
              className={INPUT}
              value={values.amount}
              disabled={travado}
              onValueChange={(amount) => patch({ amount })}
            />
            {fieldErrors.amount && <p className="mt-1 text-xs text-red">{fieldErrors.amount}</p>}
          </div>
        </div>
        <div>
          <label className={LABEL}>Data do gasto</label>
          <input
            type="date"
            className={INPUT}
            value={values.expenseDate}
            disabled={travado}
            onChange={(e) => patch({ expenseDate: e.target.value })}
          />
          {fieldErrors.expense_date && (
            <p className="mt-1 text-xs text-red" role="alert">
              {fieldErrors.expense_date}
            </p>
          )}
        </div>
        <DesembolsoFields values={values} onChange={patch} fieldErrors={fieldErrors} />
        <EventoFields
          values={values}
          onChange={patch}
          travado={travado}
          vinculoAtual={
            mode === "edit" && expense?.event_id
              ? {
                  id: expense.event_id,
                  // Feature 312 (converge): a opção fixa leva a marca, como o select da linha.
                  titulo: `${expense.event_title ?? `Evento #${expense.event_id}`}${
                    expense.event_cancelled ? " (cancelado)" : ""
                  }`,
                }
              : null
          }
        />
        {fieldErrors.event_id && (
          <p className="-mt-1 text-xs text-red" role="alert">
            {fieldErrors.event_id}
            {eventoDaTrava && (
              <>
                {" "}
                <Link to={`/events/${eventoDaTrava}?aba=comercial`} className="text-blue underline">
                  Abrir o evento
                </Link>
              </>
            )}
          </p>
        )}
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
                  Salvar e aprovar
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

const UNIDADE_GASTO = ["gasto", "gastos"] as const;

function contagem(n: number): string {
  return `${n} ${n === 1 ? "gasto" : "gastos"}`;
}

function soma(lista: GastoExtra[]): number {
  return lista.reduce((acc, e) => acc + e.amount, 0);
}

interface ListaProps {
  canManage: boolean;
  onEdit: (expense: GastoExtra) => void;
}

/**
 * "Pagos" e "Rejeitados" na abertura (feature 314): recolhidos, com quantidade e total, abrindo com
 * um clique. O `AccordionRow` guarda o aberto/fechado e não desmonta quando a lista revalida depois
 * de uma ação, então o grupo que a pessoa abriu continua aberto (FR-014).
 */
function GrupoRecolhido({
  situacao,
  expenses,
  canManage,
  onEdit,
}: ListaProps & { situacao: GastoSituacao; expenses: GastoExtra[] }) {
  return (
    <AccordionRow
      // O respiro vai no botão (não no invólucro) para a área de toque ter ≥ 44px, não só o texto.
      className="[&>div:first-child>button]:px-4 [&>div:first-child>button]:py-3"
      contentClassName="p-0"
      summary={
        <span className="flex flex-wrap items-baseline gap-x-2 text-sm">
          <span className={`font-semibold ${SITUACAO_TONE[situacao].text}`}>{SITUACAO_LABELS_GRUPO[situacao]}</span>
          <span className="tabular-nums text-muted">
            {contagem(expenses.length)} · {brl(soma(expenses))}
          </span>
        </span>
      }
    >
      <ListaDeGastos expenses={expenses} canManage={canManage} onEdit={onEdit} />
    </AccordionRow>
  );
}

export function GastosExtrasPage() {
  const query = useGastosExtras();
  const [searchParams, setSearchParams] = useSearchParams();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<GastoExtra | null>(null);

  const canManage = query.data?.can_manage ?? false;
  const categorias = useMemo(() => query.data?.categories ?? [], [query.data]);
  const expenses = useMemo(() => query.data?.expenses ?? [], [query.data]);

  // Estado na URL (como Pagamentos, feature 267): recarregar ou mandar o link mantém o recorte.
  const filtros = lerFiltrosDaUrl(searchParams, categorias);
  function atualizarUrl(mudancas: Record<string, string | null>) {
    const proximo = new URLSearchParams(searchParams);
    for (const [chave, valor] of Object.entries(mudancas)) {
      if (valor) proximo.set(chave, valor);
      else proximo.delete(chave);
    }
    setSearchParams(proximo, { replace: true });
  }
  const mudarFiltro = (mudanca: MudancaDeFiltro) => atualizarUrl(mudanca);
  const limparFiltros = () =>
    atualizarUrl({ busca: null, categoria: null, desembolso: null, mes: null, situacao: null });
  /** Clique no cartão: alterna a situação; o cartão "Todos" (ou reclicar o ativo) limpa. */
  const escolherSituacao = (situacao: GastoSituacao | null) =>
    atualizarUrl({ situacao: situacao === null || filtros.situacao === situacao ? null : situacao });

  /** Índice de busca por gasto, montado uma vez por resposta da API (não por tecla). */
  const indice = useMemo(() => new Map(expenses.map((e) => [e.id, searchIndexOfGasto(e)])), [expenses]);
  const terms = useMemo(() => searchTerms(filtros.busca), [filtros.busca]);
  const { categoria, desembolso, mes } = filtros;
  // O recorte sem a situação: é ele que os cartões somam (FR-009).
  const recorte = useMemo(
    () => filtrarGastos(expenses, { busca: "", categoria, desembolso, mes, situacao: null }, terms, indice),
    [expenses, categoria, desembolso, mes, terms, indice],
  );
  const porSituacao = useMemo(() => {
    const grupos: Record<GastoSituacao, GastoExtra[]> = {
      aguardando_aprovacao: [],
      a_pagar: [],
      no_banco: [],
      pago: [],
      rejeitado: [],
    };
    recorte.forEach((e) => grupos[situacaoDe(e)].push(e));
    return grupos;
  }, [recorte]);
  const aVista = useMemo(() => recorte.filter((e) => SITUACOES_A_VISTA.has(situacaoDe(e))), [recorte]);

  const filtroAtivo = Boolean(filtros.busca || categoria || desembolso || mes || filtros.situacao);
  const emExibicao = filtros.situacao ? porSituacao[filtros.situacao] : recorte;

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (expense: GastoExtra) => {
    setEditing(expense);
    setModalOpen(true);
  };

  const listaProps: ListaProps = { canManage, onEdit: openEdit };

  return (
    // Feature 314: sem `mx-auto max-w-*` — a página ocupa a largura inteira ao lado do menu, a
    // pedido do dono (exceção ao padrão do docs/02 §Espaçamento). Os ramos de carregamento e de
    // erro estão dentro do mesmo invólucro, então a tela não "pula" quando os dados chegam.
    <div className="space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Gastos Extras"
        subtitle={canManage ? "Gestão de gastos avulsos da empresa" : "Registre e acompanhe seus gastos avulsos"}
        actions={<Button onClick={openCreate}>+ Novo gasto</Button>}
      />

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os gastos.
        </div>
      )}

      {query.data && expenses.length === 0 && (
        <Card>
          <CardContent className="p-6 text-center text-sm text-muted">Nenhum gasto registrado ainda.</CardContent>
        </Card>
      )}

      {query.data && expenses.length > 0 && (
        <>
          {/* "Todos" ocupa a linha inteira no celular; as cinco situações ficam embaixo. */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 xl:grid-cols-6">
            <CartaoFiltro
              label="Todos"
              value={soma(recorte)}
              count={recorte.length}
              tone={null}
              active={filtros.situacao === null}
              dimmed={false}
              unidade={UNIDADE_GASTO}
              className="col-span-2 sm:col-span-1"
              onClick={() => escolherSituacao(null)}
            />
            {SITUACAO_ORDEM.map((situacao) => (
              <CartaoFiltro
                key={situacao}
                label={SITUACAO_LABELS_GRUPO[situacao]}
                value={soma(porSituacao[situacao])}
                count={porSituacao[situacao].length}
                tone={SITUACAO_TONE[situacao]}
                active={filtros.situacao === situacao}
                dimmed={filtros.situacao !== null && filtros.situacao !== situacao}
                unidade={UNIDADE_GASTO}
                onClick={() => escolherSituacao(situacao)}
              />
            ))}
          </div>

          <GastosFiltros
            filtros={filtros}
            categorias={categorias}
            onChange={mudarFiltro}
            filtroAtivo={filtroAtivo}
            emExibicao={emExibicao.length}
            totalGastos={expenses.length}
            somaEmExibicao={soma(emExibicao)}
            onLimpar={limparFiltros}
          />

          <p aria-live="polite" className="sr-only">
            {filtroAtivo
              ? `${emExibicao.length} de ${contagem(expenses.length)} em exibição, ${brl(soma(emExibicao))}.`
              : "Nenhum filtro ativo."}
          </p>

          {emExibicao.length === 0 ? (
            <Card>
              <CardContent className="space-y-3 p-6 text-center text-sm text-muted">
                <p>Nenhum gasto encontrado.</p>
                <Button variant="outline" size="sm" onClick={limparFiltros}>
                  Limpar filtros
                </Button>
              </CardContent>
            </Card>
          ) : filtros.situacao ? (
            // Com uma situação escolhida, só ela, aberta — "Pagos" aparece direto, sem abrir grupo.
            <Card>
              <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 pb-2">
                <CardTitle className="text-base">
                  {SITUACAO_LABELS_GRUPO[filtros.situacao]} ({emExibicao.length})
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => escolherSituacao(null)}>
                  Limpar filtro · {SITUACAO_LABELS_GRUPO[filtros.situacao]} ✕
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <ListaDeGastos expenses={emExibicao} {...listaProps} />
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Aguardando aprovação ou pagamento ({aVista.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {aVista.length === 0 ? (
                    <p className="p-6 text-center text-sm text-muted">
                      Nenhum gasto aguardando aprovação ou pagamento.
                    </p>
                  ) : (
                    <ListaDeGastos expenses={aVista} {...listaProps} />
                  )}
                </CardContent>
              </Card>
              {(porSituacao.pago.length > 0 || porSituacao.rejeitado.length > 0) && (
                <Card className="overflow-hidden">
                  {porSituacao.pago.length > 0 && (
                    <GrupoRecolhido situacao="pago" expenses={porSituacao.pago} {...listaProps} />
                  )}
                  {porSituacao.rejeitado.length > 0 && (
                    <GrupoRecolhido situacao="rejeitado" expenses={porSituacao.rejeitado} {...listaProps} />
                  )}
                </Card>
              )}
            </>
          )}
        </>
      )}

      <GastoFormModal
        mode={editing ? "edit" : "create"}
        expense={editing}
        categories={categorias}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
