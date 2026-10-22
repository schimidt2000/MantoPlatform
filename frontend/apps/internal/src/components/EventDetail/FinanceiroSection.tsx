import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { MoneyInput } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";
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
  type PossivelDuplicata,
} from "../../lib/eventAttachments";
import { Empty, INPUT_CLASS, Panel, brl, formatDateTime, formatDay } from "./parts";

const MONEY_INPUT_CLASS = "h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Contratos do evento: anexar, marcar assinado e (superadmin) excluir. */
function ContratosPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddContract(eventId);
  const del = useDeleteContract(eventId);
  const toggle = useToggleContractSigned(eventId);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Feature 312: contrato não é dado de venda — no cancelado fica para consulta.
  const consulta = Boolean(data.flags.somente_consulta);
  const isSuperadmin = Boolean(data.flags.is_superadmin) && !consulta;
  const contratos = data.contratos ?? [];

  return (
    <Panel
      title="Contrato assinado"
      actions={
        contratos.length > 0 ? (
          <Badge tone={contratos.some((c) => c.is_signed) ? "green" : "gold"}>
            {contratos.some((c) => c.is_signed) ? "Assinado" : "Pendente"}
          </Badge>
        ) : null
      }
    >
      {contratos.length === 0 ? (
        <Empty>Nenhum contrato anexado.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {contratos.map((contrato) => (
            <li
              key={contrato.id}
              className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-sm"
            >
              <a
                href={assetUrl(contrato.file_path)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue underline"
              >
                Ver contrato
              </a>
              <span className="flex items-center gap-2">
                <span className={contrato.is_signed ? "text-green" : "text-muted"}>
                  {contrato.is_signed ? "Assinado" : "Pendente"}
                </span>
                {isSuperadmin && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={toggle.isPending}
                      onClick={() => toggle.mutate(contrato.id)}
                    >
                      {contrato.is_signed ? "Desmarcar" : "Marcar assinado"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red"
                      loading={del.isPending}
                      onClick={() => {
                        if (window.confirm("Excluir este contrato?")) del.mutate(contrato.id);
                      }}
                    >
                      Excluir
                    </Button>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!consulta && (
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <p className="w-full text-xs text-muted">PDF / JPG / PNG — máx. 10 MB</p>
        <input
          ref={inputRef}
          type="file"
          className="text-sm text-ink"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label="Arquivo do contrato"
        />
        <Button
          size="sm"
          loading={add.isPending}
          disabled={!file}
          onClick={() =>
            file &&
            add.mutate(
              { file },
              {
                onSuccess: () => {
                  setFile(null);
                  if (inputRef.current) inputRef.current.value = "";
                },
              },
            )
          }
        >
          Inserir contrato
        </Button>
      </div>
      )}
      {add.isError && <p className="mt-1 text-sm text-red">Não foi possível inserir o contrato.</p>}
    </Panel>
  );
}

/** Um comprovante de pagamento — superadmin pode corrigir o valor ou excluir. */
/**
 * "Anexar comprovante" num pagamento de PIX que nasceu sem arquivo (feature 318): o arquivo vai
 * para o mesmo pagamento — o recebido não muda.
 */
function AnexarAoPix({
  eventId,
  item,
}: {
  eventId: number;
  item: NonNullable<EventoDetalhe["pagamentos"]>["items"][number];
}) {
  const add = useAddPayment(eventId);
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        aria-label="Anexar comprovante a este PIX"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) add.mutate({ amount: item.amount ?? 0, file, anexarA: item.id });
        }}
      />
      <Button variant="ghost" size="sm" loading={add.isPending} onClick={() => inputRef.current?.click()}>
        Anexar comprovante
      </Button>
      {add.isError && (
        <span role="alert" className="text-xs text-red">
          {add.error?.message || "Não foi possível anexar."}
        </span>
      )}
    </>
  );
}

function PagamentoItem({
  item,
  eventId,
  isSuperadmin,
  podeAnexar,
}: {
  item: NonNullable<EventoDetalhe["pagamentos"]>["items"][number];
  eventId: number;
  isSuperadmin: boolean;
  podeAnexar: boolean;
}) {
  const edit = useEditPayment(eventId);
  const del = useDeletePayment(eventId);
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(item.amount ?? 0);

  if (editing) {
    return (
      <li className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-sm">
        <span className="text-muted">{formatDateTime(item.created_at)}</span>
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
              edit.mutate({ paymentId: item.id, amount }, { onSuccess: () => setEditing(false) })
            }
          >
            Salvar
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            Cancelar
          </Button>
        </span>
        {edit.isError && (
          <p className="w-full text-sm text-red" role="alert">
            {edit.error?.message || "Não foi possível corrigir o comprovante."}
          </p>
        )}
      </li>
    );
  }

  const pix = item.pix;
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-sm">
      <span className="min-w-0 text-muted">
        {pix ? (
          // Feature 318: o pagamento veio do aviso de PIX do banco (ligado sozinho ou confirmado).
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="text-ink">
              PIX · {item.conta ?? pix.conta ?? "conta não cadastrada"} · {formatDateTime(pix.recebido_em)}
              {pix.pagador && ` · de ${pix.pagador}`}
            </span>
            <Badge tone={pix.automatico ? "green" : "blue"}>
              {pix.automatico ? "automático" : `confirmado por ${pix.decidido_por ?? "—"}`}
            </Badge>
          </span>
        ) : (
          <>
            {formatDateTime(item.created_at)}
            {item.conta && ` · ${item.conta}`}
          </>
        )}
      </span>
      <span className="flex items-center gap-2">
        {item.file_path ? (
          <a
            href={assetUrl(item.file_path)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue underline"
          >
            Ver comprovante
          </a>
        ) : (
          podeAnexar && <AnexarAoPix eventId={eventId} item={item} />
        )}
        <span className="tabular-nums text-ink">{brl(item.amount)}</span>
        {isSuperadmin && (
          <>
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
              Editar
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-red"
              loading={del.isPending}
              onClick={() => {
                if (window.confirm("Excluir este comprovante?")) del.mutate(item.id);
              }}
            >
              Excluir
            </Button>
          </>
        )}
      </span>
      {del.isError && (
        <p className="w-full text-sm text-red" role="alert">
          {del.error?.message || "Não foi possível excluir o comprovante."}
        </p>
      )}
    </li>
  );
}

type Pagamentos = NonNullable<EventoDetalhe["pagamentos"]>;

/** "Inclui R$ X em comprovantes de outros eventos do grupo", com o link de cada um. */
function OutrosDoGrupo({ outros }: { outros: NonNullable<Pagamentos["outros_do_grupo"]> }) {
  if (outros.length === 0) return null;
  const soma = outros.reduce((acc, item) => acc + item.total, 0);
  return (
    <div className="mt-1 text-xs text-muted">
      Inclui {brl(soma)} em comprovantes de outros eventos do grupo:
      <ul className="mt-0.5 space-y-0.5">
        {outros.map((item) => (
          <li key={item.event_id} className="break-words">
            <Link to={`/events/${item.event_id}?aba=comercial`} className="text-blue underline">
              {item.event_title}
            </Link>{" "}
            <span className="tabular-nums">({brl(item.total)})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * A linha "Recebido X de Y" (feature 299): a conta é a do GRUPO, a mesma da Home. Sem as chaves
 * novas (servidor antigo, na janela de deploy), vale o texto de antes — só o próprio evento.
 */
function ResumoDoRecebido({ data, pagamentos }: { data: EventoDetalhe; pagamentos: Pagamentos }) {
  const cobranca = data.cobranca;
  const doEvento = pagamentos.received_total ?? 0;
  if (!cobranca || cobranca.escopo === undefined) {
    return (
      <span className="font-medium text-ink tabular-nums">
        Recebido {brl(doEvento)} de {brl(data.venda?.sale_value ?? 0)}
      </span>
    );
  }
  const recebido = cobranca.recebido ?? 0;
  // Feature 306 (FR-074): no evento cancelado a venda acabou, e nada falta receber. Só o dia cortado
  // de um grupo que segue vivo (regime `dia`) continua mostrando o que falta da venda do grupo.
  const semFalta =
    cobranca.quitado || (Boolean(data.event.cancelled_at) && data.event.cancelamento?.regime !== "dia");
  // Cortesia ou permuta não é venda: nada de "de R$ 0,00 — falta R$ 0,00" nem "Quitado".
  const cortesia = Boolean(cobranca.cortesia);
  if (cobranca.escopo === "grupo_outro") {
    const grupo = data.event.group;
    return (
      <span className="space-y-0.5 text-ink">
        <span className="block">
          Este evento é parte do grupo {grupo?.display_name ?? ""}. A venda está no{" "}
          {grupo?.leader ? (
            <Link to={`/events/${grupo.leader.id}?aba=comercial`} className="text-blue underline">
              {grupo.leader.title}
            </Link>
          ) : (
            "evento principal"
          )}
          .
        </span>
        <span className="block font-medium tabular-nums">
          {cortesia ? (
            `Recebido no grupo ${brl(recebido)} · cortesia ou permuta`
          ) : cobranca.sem_valor ? (
            // O principal ainda sem valor: nunca "de R$ 0,00 — falta R$ 0,00" (US1/AC6).
            `Recebido no grupo ${brl(recebido)} · valor de venda a definir`
          ) : (
            <>
              Recebido no grupo {brl(recebido)}
              {(cobranca.devolvido ?? 0) > 0 && ` (devolvidos ${brl(cobranca.devolvido ?? 0)})`} de{" "}
              {brl(cobranca.valor ?? 0)}
              {!semFalta && ` — falta ${brl(cobranca.outstanding ?? 0)}`}
            </>
          )}
        </span>
        <span className="block text-xs text-muted tabular-nums">neste evento: {brl(doEvento)}</span>
      </span>
    );
  }
  if (cortesia) {
    return (
      <span className="block text-ink">
        <span className="font-medium tabular-nums">Recebido {brl(recebido)} · cortesia ou permuta</span>
        <OutrosDoGrupo outros={pagamentos.outros_do_grupo ?? []} />
      </span>
    );
  }
  if (cobranca.sem_valor) {
    return (
      <span className="block text-ink">
        <span className="font-medium tabular-nums">Recebido {brl(recebido)} · valor de venda a definir</span>
        <OutrosDoGrupo outros={pagamentos.outros_do_grupo ?? []} />
      </span>
    );
  }
  return (
    <span className="block text-ink">
      <span className="font-medium tabular-nums">
        Recebido {brl(recebido)}
        {(cobranca.devolvido ?? 0) > 0 && ` (devolvidos ${brl(cobranca.devolvido ?? 0)})`} de{" "}
        {brl(cobranca.valor ?? 0)}
        {!semFalta && ` — falta ${brl(cobranca.outstanding ?? 0)}`}
      </span>
      <OutrosDoGrupo outros={pagamentos.outros_do_grupo ?? []} />
    </span>
  );
}

/** Comprovantes de pagamento + status do faturamento. */
function PagamentosPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddPayment(eventId);
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [contaId, setContaId] = useState<number | null>(null);
  // Feature 318: o 409 `possivel_duplicata` — o comprovante pode ser do PIX que já entrou.
  const [duplicata, setDuplicata] = useState<PossivelDuplicata | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pagamentos = data.pagamentos;
  if (!pagamentos) return null;

  function limpar() {
    setAmount(0);
    setFile(null);
    setContaId(null);
    setDuplicata(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function enviar(extra: { anexarA?: number; forcarNovo?: boolean } = {}) {
    if (!file) return;
    add.mutate(
      { amount, file, contaId, ...extra },
      {
        onSuccess: limpar,
        onError: (erro) => {
          if (erro instanceof ApiRequestError && erro.details?.codigo === "possivel_duplicata") {
            setDuplicata((erro.details.pagamento as PossivelDuplicata) ?? null);
          }
        },
      },
    );
  }
  // Feature 306: no cancelado, só quem corrige a venda do cancelado lança comprovante. O que já
  // existia se gata com `!== false` (janela de deploy: backend antigo não manda a chave).
  const podeLancar = data.flags.can_edit_pagamentos !== false;

  // "Quitado" vem do servidor, com a folga de centavos e o grupo (feature 299); sem a chave
  // (servidor antigo), a conta de antes, só com o próprio evento.
  const total = data.venda?.sale_value ?? 0;
  const quitado =
    data.cobranca?.quitado ?? (total > 0 && (pagamentos.received_total ?? 0) >= total);

  return (
    <Panel
      title="Comprovantes de pagamento"
      actions={quitado ? <Badge tone="green">Quitado ✓</Badge> : null}
    >
      <div className="mb-2 rounded-md border border-line bg-green-soft/30 px-3 py-2 text-sm">
        <ResumoDoRecebido data={data} pagamentos={pagamentos} />
      </div>
      {pagamentos.items.length === 0 ? (
        <Empty>Nenhum pagamento registrado.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {pagamentos.items.map((item) => (
            <PagamentoItem
              key={item.id}
              item={item}
              eventId={eventId}
              isSuperadmin={Boolean(data.flags.is_superadmin)}
              podeAnexar={podeLancar}
            />
          ))}
        </ul>
      )}
      {podeLancar && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <MoneyInput
            value={amount}
            onValueChange={setAmount}
            className={MONEY_INPUT_CLASS}
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
          {(pagamentos.contas ?? []).length > 0 && (
            <select
              className="h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink"
              value={contaId ?? ""}
              onChange={(e) => setContaId(e.target.value ? Number(e.target.value) : null)}
              aria-label="Conta que recebeu"
            >
              <option value="">Conta que recebeu (opcional)</option>
              {(pagamentos.contas ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.apelido}
                </option>
              ))}
            </select>
          )}
          <Button size="sm" loading={add.isPending} disabled={!amount || !file} onClick={() => enviar()}>
            Inserir comprovante
          </Button>
          {add.isError && !duplicata && (
            <p className="w-full text-sm text-red" role="alert">
              {add.error?.message || "Informe o valor e insira o comprovante."}
            </p>
          )}
        </div>
      )}
      <Dialog open={duplicata !== null} onOpenChange={(aberto) => !aberto && setDuplicata(null)}>
        <DialogContent open={duplicata !== null}>
          <DialogHeader>
            <DialogTitle>Esse comprovante é do PIX que já entrou?</DialogTitle>
            <DialogDescription>
              {duplicata &&
                `Um PIX de ${brl(Number(duplicata.valor))}${duplicata.pagador ? ` de ${duplicata.pagador}` : ""}` +
                  `${duplicata.recebido_em ? ` em ${formatDateTime(duplicata.recebido_em)}` : ""}` +
                  `${duplicata.conta ? ` (${duplicata.conta})` : ""} já foi registrado nesta venda. ` +
                  "Se for o mesmo pagamento, o arquivo é anexado a ele e o recebido não muda."}
            </DialogDescription>
          </DialogHeader>
          {add.isError && duplicata && !(add.error instanceof ApiRequestError && add.error.details?.codigo === "possivel_duplicata") && (
            <p role="alert" className="rounded-md bg-red-soft px-3 py-2 text-sm text-red">
              {add.error?.message || "Não foi possível registrar."}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" disabled={add.isPending} onClick={() => setDuplicata(null)}>
              Cancelar
            </Button>
            <Button variant="outline" disabled={add.isPending} onClick={() => enviar({ forcarNovo: true })}>
              Não, é outro pagamento
            </Button>
            <Button loading={add.isPending} onClick={() => duplicata && enviar({ anexarA: duplicata.id })}>
              Sim, anexar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Panel>
  );
}

/** Notas fiscais anexadas ao evento. */
function NotasFiscaisPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddInvoice(eventId);
  const [amount, setAmount] = useState(0);
  const [issueDate, setIssueDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const notas = data.notas_fiscais;
  if (!notas) return null;
  // Feature 306: no cancelado, só pela flag de correção da venda do cancelado.
  const podeLancar = !data.event.cancelled_at || Boolean(data.flags.can_edit_venda_cancelado);

  return (
    <Panel title="Notas fiscais">
      {notas.length === 0 ? (
        <Empty>Nenhuma nota fiscal anexada.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {notas.map((nota) => (
            <li key={nota.id} className="flex items-center justify-between gap-2 py-1.5 text-sm">
              <span className="text-ink tabular-nums">
                {brl(nota.amount)}
                {nota.issue_date && ` · ${formatDay(nota.issue_date)}`}
              </span>
              <span className="flex items-center gap-2">
                <Badge tone={nota.status === "emitida" ? "green" : "neutral"}>
                  {nota.status === "emitida" ? "Emitida" : "A emitir"}
                </Badge>
                {nota.file && (
                  <a
                    href={assetUrl(nota.file)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue underline"
                  >
                    Ver nota
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {podeLancar && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <MoneyInput
            value={amount}
            onValueChange={setAmount}
            className={MONEY_INPUT_CLASS}
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
            onClick={() =>
              add.mutate(
                {
                  amount: amount || undefined,
                  issue_date: issueDate || undefined,
                  file: file ?? undefined,
                },
                {
                  onSuccess: () => {
                    setAmount(0);
                    setIssueDate("");
                    setFile(null);
                    if (inputRef.current) inputRef.current.value = "";
                  },
                },
              )
            }
          >
            Adicionar
          </Button>
        </div>
      )}
      {add.isError && (
        <p className="mt-1 text-sm text-red" role="alert">
          {add.error?.message || "Informe ao menos o valor, a data ou o arquivo."}
        </p>
      )}
    </Panel>
  );
}

/** Formulário de "marcar reembolso como cobrado" — some assim que ele é cobrado. */
function CollectForm({ reimbursementId, eventId }: { reimbursementId: number; eventId: number }) {
  const collect = useCollectReimbursement(eventId);
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      <Button
        size="sm"
        loading={collect.isPending}
        disabled={!amount || !file}
        onClick={() =>
          file &&
          collect.mutate(
            { reimbursementId, collected_amount: amount, file },
            {
              onSuccess: () => {
                setAmount(0);
                setFile(null);
                if (inputRef.current) inputRef.current.value = "";
              },
            },
          )
        }
      >
        Marcar como cobrado
      </Button>
      {collect.isError && (
        <p className="w-full text-sm text-red" role="alert">
          {collect.error?.message || "Informe o valor e insira o comprovante."}
        </p>
      )}
    </div>
  );
}

/** Reembolsos: despesas a cobrar da cliente. */
function ReembolsosPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddReimbursement(eventId);
  const del = useDeleteReimbursement(eventId);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const reembolsos = data.reembolsos;
  if (!reembolsos) return null;
  const isSuperadmin = Boolean(data.flags.is_superadmin);
  // Feature 306: no cancelado, só pela flag de correção da venda do cancelado.
  const podeLancar = !data.event.cancelled_at || Boolean(data.flags.can_edit_venda_cancelado);

  return (
    <Panel
      title="Reembolsos"
      actions={
        (reembolsos.pendentes_total ?? 0) > 0 ? (
          <Badge tone="gold">Pendente {brl(reembolsos.pendentes_total)}</Badge>
        ) : null
      }
    >
      {reembolsos.items.length === 0 ? (
        <Empty>Nenhum reembolso registrado.</Empty>
      ) : (
        <ul className="divide-y divide-line">
          {reembolsos.items.map((item) => (
            <li key={item.id} className="py-1.5 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
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
                  {item.is_collected && <Badge tone="green" className="ml-2">Cobrado</Badge>}
                </span>
                <span className="flex items-center gap-2">
                  <span className="tabular-nums text-ink">{brl(item.amount)}</span>
                  {isSuperadmin && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red"
                      loading={del.isPending}
                      onClick={() => {
                        if (window.confirm("Excluir este reembolso?")) del.mutate(item.id);
                      }}
                    >
                      Excluir
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
              ) : !item.is_collected && podeLancar ? (
                <CollectForm reimbursementId={item.id} eventId={eventId} />
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {podeLancar && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <input
            className={`${INPUT_CLASS} min-w-40 flex-1`}
            placeholder="Ex.: Bagagem extra"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            aria-label="Descrição do reembolso"
          />
          <MoneyInput
            value={amount}
            onValueChange={setAmount}
            className={MONEY_INPUT_CLASS}
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
            onClick={() =>
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
              )
            }
          >
            Registrar reembolso
          </Button>
          {add.isError && (
            <p className="w-full text-sm text-red" role="alert">
              {add.error?.message || "Informe a descrição e o valor do reembolso."}
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}

export interface FinanceiroSectionProps {
  data: EventoDetalhe;
}

/** Contratos, notas fiscais, pagamentos e reembolsos (coluna direita, feature 190). */
export function FinanceiroSection({ data }: FinanceiroSectionProps) {
  return (
    <>
      {data.contratos && <ContratosPanel data={data} />}
      {data.notas_fiscais && <NotasFiscaisPanel data={data} />}
      {data.pagamentos && <PagamentosPanel data={data} />}
      {data.reembolsos && <ReembolsosPanel data={data} />}
    </>
  );
}
