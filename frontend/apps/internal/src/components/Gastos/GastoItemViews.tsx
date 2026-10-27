import { useState, type ReactNode } from "react";
import { FileText, Link2, Pencil, Trash2 } from "lucide-react";
import { Button, ConfirmDialog, cn } from "@manto/ui";
import { SeloSituacao } from "../SeloSituacao";
import { LinkDeArquivo } from "../ArquivoViewer";
import { brl } from "../../lib/pagamentos";
import {
  SITUACAO_LABELS,
  SITUACAO_TONE,
  formatarDataGasto,
  situacaoDe,
  useApproveGasto,
  useDeleteGasto,
  useGastosEventos,
  useLinkGastoEvento,
  useRejectGasto,
  type GastoExtra,
  type GastoMarketingBatch,
} from "../../lib/gastos";

/**
 * Vistas de um gasto extra (feature 314): a linha da tabela do computador e o cartão do celular,
 * com as mesmas ações. Mesmo desenho de `components/Pagamentos/PagamentoItemViews.tsx`.
 */

const ROTULO_DESEMBOLSO: Record<"reembolso" | "fornecedor" | "cliente", string> = {
  reembolso: "reembolso",
  fornecedor: "fornecedor",
  cliente: "devolução à cliente",
};

const formatDate = formatarDataGasto;

interface ItemProps {
  expense: GastoExtra;
  canManage: boolean;
  onEdit: (expense: GastoExtra) => void;
}

export function SituacaoBadge({ expense }: { expense: GastoExtra }) {
  const situacao = situacaoDe(expense);
  return (
    <span className="inline-flex max-w-full flex-col items-start gap-0.5">
      {/* Quebra em vez de `nowrap`: "Aguardando aprovação" não cabe na coluna de 112px e, sem
          quebrar, o selo invadia a coluna Desembolso (a célula não corta, então não vira rolagem). */}
      <span
        className={cn(
          "max-w-full rounded-md border px-2 py-0.5 text-xs font-medium leading-tight",
          SITUACAO_TONE[situacao].select,
        )}
      >
        {SITUACAO_LABELS[situacao]}
      </span>
      {expense.status === "aprovado" && expense.approved_with_edits && (
        <span className="text-[11px] text-muted">aprovado com edições</span>
      )}
    </span>
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
        aria-label="Data do evento"
      />
      <select
        className="h-8 min-w-0 max-w-full rounded-md border border-line bg-panel px-2"
        value={expense.event_id ?? ""}
        onChange={(e) => link.mutate({ id: expense.id, event_id: e.target.value ? Number(e.target.value) : null })}
        disabled={link.isPending}
        aria-label="Evento vinculado"
      >
        <option value="">Sem evento vinculado</option>
        {/* Feature 312: a lista do dia não oferece o cancelado; o vínculo que já existe (a devolução,
            a multa) aparece como opção fixa, em vez de o select dizer "Sem evento vinculado". */}
        {expense.event_id != null &&
          !eventos.data?.events.some((ev) => ev.id === expense.event_id) && (
            <option value={expense.event_id}>
              {expense.event_title ?? `Evento #${expense.event_id}`}
              {expense.event_cancelled ? " (cancelado)" : ""}
            </option>
          )}
        {eventos.data?.events.map((ev) => (
          <option key={ev.id} value={ev.id}>
            {ev.label}
          </option>
        ))}
      </select>
      {link.isError && (
        <p className="w-full text-red" role="alert">
          {(link.error as Error | null)?.message || "Não foi possível vincular o evento."}
        </p>
      )}
    </div>
  );
}

function Desembolso({ expense }: { expense: GastoExtra }) {
  if (!expense.disbursement_type) return <span className="text-muted">—</span>;
  return (
    <>
      {expense.payee_name}
      <span className="ml-1 text-xs text-muted">({ROTULO_DESEMBOLSO[expense.disbursement_type]})</span>
    </>
  );
}

function Evento({ expense, recortado }: { expense: GastoExtra; recortado: boolean }) {
  if (!expense.event_title) return <span className="text-muted">—</span>;
  return (
    // Na tabela, o título do evento carrega o elenco inteiro ("(R&I) CARRO VERMELHO + CARRO AMARELO +
    // …") e quebrava em cinco linhas, empurrando a linha a 300px: duas linhas e o nome inteiro na
    // dica. No cartão do celular vai inteiro — dica não abre com o dedo (achado G8 do converge).
    <span className={recortado ? "line-clamp-2" : undefined} title={recortado ? expense.event_title : undefined}>
      {/* Feature 312: o gasto ligado a um evento cancelado (a devolução, a multa) leva o selo. */}
      {expense.event_cancelled && <SeloSituacao situacao="cancelado" compacto />}
      {expense.event_title}
    </span>
  );
}

interface AcoesProps extends ItemProps {
  /** Tabela do computador: ações secundárias em ícone. Cartão do celular: tudo com texto. */
  compacto: boolean;
  onToggleLink: () => void;
}

/** Botão de ícone com o nome acessível e a dica iguais (FR-018). */
function IconeAcao({ rotulo, children, onClick }: { rotulo: string; children: ReactNode; onClick: () => void }) {
  return (
    <Button size="sm" variant="ghost" className="h-8 w-8 p-0" aria-label={rotulo} title={rotulo} onClick={onClick}>
      {children}
    </Button>
  );
}

function AcoesDoGasto({ expense, canManage, onEdit, compacto, onToggleLink }: AcoesProps) {
  const approve = useApproveGasto();
  const reject = useRejectGasto();
  const del = useDeleteGasto();
  const [confirmarExclusao, setConfirmarExclusao] = useState(false);

  // Feature 306: a devolução de um evento cancelado não se exclui nem se religa aqui (o servidor
  // recusa com 409); a correção do valor é pelo "Alterar devolução" na tela do evento.
  const travado = Boolean(expense.locked);
  const canDelete = !travado && (canManage || expense.status === "pendente");
  const pendenteDeGestao = canManage && expense.status === "pendente";
  const erroDaAcao = (approve.error ?? reject.error) as Error | null;
  const erroDaExclusao = del.isError
    ? (del.error as Error | null)?.message || "Não foi possível excluir o gasto. Tente novamente."
    : null;

  const handleReject = () => {
    // `null` = a pessoa clicou em Cancelar no prompt. Antes da 314 o `?? ""` rejeitava mesmo assim.
    const motivo = window.prompt("Motivo da rejeição (opcional):");
    if (motivo === null) return;
    reject.mutate({ id: expense.id, motivo });
  };

  const verNota = expense.receipt_url ? (
    compacto ? (
      <Button asChild size="sm" variant="ghost" className="h-8 w-8 p-0">
        <LinkDeArquivo caminho={expense.receipt_url} aria-label="Ver nota fiscal" title="Ver nota fiscal">
          <FileText className="h-4 w-4" aria-hidden />
        </LinkDeArquivo>
      </Button>
    ) : (
      <Button asChild size="sm" variant="outline">
        <LinkDeArquivo caminho={expense.receipt_url}>Ver nota fiscal</LinkDeArquivo>
      </Button>
    )
  ) : null;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1">
        {pendenteDeGestao && (
          <>
            <Button size="sm" loading={approve.isPending} onClick={() => approve.mutate(expense.id)}>
              Aprovar
            </Button>
            <Button size="sm" variant="outline" loading={reject.isPending} onClick={handleReject}>
              Rejeitar
            </Button>
          </>
        )}
        {compacto ? (
          <span className="flex items-center">
            {verNota}
            {canManage && (
              <IconeAcao rotulo="Editar" onClick={() => onEdit(expense)}>
                <Pencil className="h-4 w-4" aria-hidden />
              </IconeAcao>
            )}
            {canManage && !travado && (
              <IconeAcao rotulo="Vincular evento" onClick={onToggleLink}>
                <Link2 className="h-4 w-4" aria-hidden />
              </IconeAcao>
            )}
            {canDelete && (
              <IconeAcao rotulo="Excluir" onClick={() => setConfirmarExclusao(true)}>
                <Trash2 className="h-4 w-4" aria-hidden />
              </IconeAcao>
            )}
          </span>
        ) : (
          <>
            {verNota}
            {canManage && (
              <Button size="sm" variant="ghost" onClick={() => onEdit(expense)}>
                Editar
              </Button>
            )}
            {canManage && !travado && (
              <Button size="sm" variant="ghost" onClick={onToggleLink}>
                Vincular evento
              </Button>
            )}
            {canDelete && (
              <Button size="sm" variant="ghost" onClick={() => setConfirmarExclusao(true)}>
                Excluir
              </Button>
            )}
          </>
        )}
      </div>
      {travado && <p className="mt-1 text-xs text-muted">Devolução de cancelado: travada.</p>}
      {erroDaAcao && (
        <p className="mt-1 text-xs text-red" role="alert">
          {erroDaAcao.message || "Não foi possível concluir a ação."}
        </p>
      )}
      {/* Princípio V: exclusão é a ação que não volta — diálogo da casa com o que está em jogo, no
          lugar do `window.confirm` que só mostrava a descrição. */}
      <ConfirmDialog
        open={confirmarExclusao}
        title="Excluir este gasto?"
        description={
          <>
            “{expense.description}” — {brl(expense.amount)}. Esta exclusão não pode ser desfeita.
          </>
        }
        confirmLabel="Excluir"
        destructive
        pending={del.isPending}
        error={erroDaExclusao}
        onConfirm={() => del.mutate(expense.id, { onSuccess: () => setConfirmarExclusao(false) })}
        onOpenChange={(aberto) => {
          setConfirmarExclusao(aberto);
          if (!aberto) del.reset();
        }}
      />
    </div>
  );
}

function GastoRow({ expense, canManage, onEdit }: ItemProps) {
  const [showLink, setShowLink] = useState(false);
  const travado = Boolean(expense.locked);
  return (
    <>
      <tr className="border-b border-line align-top">
        <td className="whitespace-nowrap px-2 py-2 tabular-nums">{formatDate(expense.expense_date)}</td>
        <td className="px-2 py-2 [overflow-wrap:anywhere]">
          <p className="font-medium text-ink">{expense.description}</p>
          <p className="text-xs text-muted">
            {expense.category}
            {expense.notes && ` · ${expense.notes}`}
          </p>
          {canManage && expense.created_by_name && (
            <p className="text-xs text-muted">por {expense.created_by_name}</p>
          )}
          {expense.marketing_batch && <MarketingBatchDetail batch={expense.marketing_batch} />}
        </td>
        <td className="whitespace-nowrap px-2 py-2 text-right tabular-nums">{brl(expense.amount)}</td>
        <td className="px-2 py-2">
          <SituacaoBadge expense={expense} />
        </td>
        <td className="px-2 py-2 [overflow-wrap:anywhere]">
          <Desembolso expense={expense} />
        </td>
        <td className="px-2 py-2 [overflow-wrap:anywhere]">
          <Evento expense={expense} recortado />
        </td>
        <td className="px-2 py-2">
          <AcoesDoGasto
            expense={expense}
            canManage={canManage}
            onEdit={onEdit}
            compacto
            onToggleLink={() => setShowLink((v) => !v)}
          />
        </td>
      </tr>
      {showLink && !travado && (
        <tr className="border-b border-line bg-surface-2/50">
          <td colSpan={7} className="px-2 py-2">
            <EventoVincular expense={expense} />
          </td>
        </tr>
      )}
    </>
  );
}

function GastoCard({ expense, canManage, onEdit }: ItemProps) {
  const [showLink, setShowLink] = useState(false);
  const travado = Boolean(expense.locked);
  return (
    <article className="rounded-lg border border-line bg-panel p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-ink [overflow-wrap:anywhere]">{expense.description}</p>
          <p className="text-xs text-muted">
            {formatDate(expense.expense_date)} · {expense.category}
          </p>
        </div>
        <p className="shrink-0 font-semibold tabular-nums text-ink">{brl(expense.amount)}</p>
      </div>
      <div className="mt-2">
        <SituacaoBadge expense={expense} />
      </div>
      {expense.notes && <p className="mt-2 text-xs text-muted [overflow-wrap:anywhere]">{expense.notes}</p>}
      {expense.marketing_batch && <MarketingBatchDetail batch={expense.marketing_batch} />}
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-muted">Desembolso</dt>
        <dd className="min-w-0 [overflow-wrap:anywhere]">
          <Desembolso expense={expense} />
        </dd>
        <dt className="text-muted">Evento</dt>
        <dd className="min-w-0 [overflow-wrap:anywhere]">
          <Evento expense={expense} recortado={false} />
        </dd>
        {canManage && (
          <>
            <dt className="text-muted">Autor</dt>
            <dd className="min-w-0">{expense.created_by_name ?? "—"}</dd>
          </>
        )}
      </dl>
      <div className="mt-3">
        <AcoesDoGasto
          expense={expense}
          canManage={canManage}
          onEdit={onEdit}
          compacto={false}
          onToggleLink={() => setShowLink((v) => !v)}
        />
      </div>
      {showLink && !travado && (
        <div className="mt-2 rounded-md bg-surface-2/50 p-2">
          <EventoVincular expense={expense} />
        </div>
      )}
    </article>
  );
}

const TH = "px-2 py-2";

/**
 * Lista de gastos nas duas formas: cartões abaixo de `xl` e tabela a partir dele.
 *
 * A tabela é `table-fixed` SEM `min-w` e sem `overflow-x-auto` (feature 314): as colunas fixas
 * somam 800px e a coluna Gasto fica com o resto, então a 1280px (976px úteis ao lado do menu) ainda
 * não há rolagem lateral. Antes eram 10 colunas com `min-w-[960px]` e as ações em `nowrap`, presas
 * num `max-w-6xl` — a rolagem ficava no rodapé de 186 linhas e cortava os botões.
 */
export function ListaDeGastos({
  expenses,
  canManage,
  onEdit,
}: {
  expenses: GastoExtra[];
  canManage: boolean;
  onEdit: (expense: GastoExtra) => void;
}) {
  return (
    <>
      {/* `[&>*]:min-w-0`: item de grade sem isso não encolhe abaixo do conteúdo (lição da 226). */}
      <div className="grid gap-2 p-3 md:grid-cols-2 xl:hidden [&>*]:min-w-0">
        {expenses.map((e) => (
          <GastoCard key={e.id} expense={e} canManage={canManage} onEdit={onEdit} />
        ))}
      </div>
      <div className="hidden xl:block">
        <table className="w-full table-fixed border-collapse text-[13px]">
          <colgroup>
            <col className="w-24" />
            <col />
            <col className="w-28" />
            <col className="w-28" />
            <col className="w-36" />
            <col className="w-40" />
            <col className="w-44" />
          </colgroup>
          <thead>
            <tr className="border-b-2 border-line text-left text-[11px] font-bold uppercase tracking-wide text-muted">
              <th className={TH}>Data</th>
              <th className={TH}>Gasto</th>
              <th className={`${TH} text-right`}>Valor</th>
              <th className={TH}>Situação</th>
              <th className={TH}>Desembolso</th>
              <th className={TH}>Evento</th>
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
    </>
  );
}
