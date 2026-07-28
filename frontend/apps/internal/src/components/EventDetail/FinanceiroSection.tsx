import { useRef, useState } from "react";
import { Badge, Button } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
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
} from "../../lib/eventAttachments";
import { brl, Empty, formatDateTime, formatDay, INPUT_CLASS, Panel } from "./parts";

const MONEY_INPUT_CLASS = "h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Contratos do evento: anexar, marcar assinado e (superadmin) excluir. */
function ContratosPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddContract(eventId);
  const del = useDeleteContract(eventId);
  const toggle = useToggleContractSigned(eventId);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isSuperadmin = Boolean(data.flags.is_superadmin);
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
          Enviar contrato
        </Button>
      </div>
      {add.isError && <p className="mt-1 text-sm text-red">Não foi possível anexar o contrato.</p>}
    </Panel>
  );
}

/** Um comprovante de pagamento — superadmin pode corrigir o valor ou excluir. */
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
      </li>
    );
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-sm">
      <span className="text-muted">{formatDateTime(item.created_at)}</span>
      <span className="flex items-center gap-2">
        <a
          href={assetUrl(item.file_path)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue underline"
        >
          Ver comprovante
        </a>
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
                if (window.confirm("Excluir este comprovante de pagamento?")) del.mutate(item.id);
              }}
            >
              Excluir
            </Button>
          </>
        )}
      </span>
    </li>
  );
}

/** Comprovantes de pagamento + status do faturamento. */
function PagamentosPanel({ data }: { data: EventoDetalhe }) {
  const eventId = data.event.id;
  const add = useAddPayment(eventId);
  const [amount, setAmount] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pagamentos = data.pagamentos;
  if (!pagamentos) return null;

  const recebido = pagamentos.received_total ?? 0;
  const total = data.venda?.sale_value ?? 0;
  const quitado = total > 0 && recebido >= total;

  return (
    <Panel
      title="Comprovantes de pagamento"
      actions={quitado ? <Badge tone="green">Quitado ✓</Badge> : null}
    >
      <div className="mb-2 rounded-md border border-line bg-green-soft/30 px-3 py-2 text-sm">
        <span className="font-medium text-ink tabular-nums">
          Recebido {brl(recebido)} de {brl(total)}
        </span>
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
            />
          ))}
        </ul>
      )}
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
        <Button
          size="sm"
          loading={add.isPending}
          disabled={!amount || !file}
          onClick={() =>
            file &&
            add.mutate(
              { amount, file },
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
          Adicionar pagamento
        </Button>
        {add.isError && (
          <p className="w-full text-sm text-red">Informe o valor e anexe o comprovante.</p>
        )}
      </div>
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
                    Abrir
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
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
      {add.isError && (
        <p className="mt-1 text-sm text-red">Informe ao menos o valor, a data ou o arquivo.</p>
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
        Marcar cobrado
      </Button>
      {collect.isError && (
        <p className="w-full text-sm text-red">Informe o valor e anexe o comprovante.</p>
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
                  {item.is_collected && <Badge tone="green" className="ml-2">cobrado</Badge>}
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
              ) : !item.is_collected ? (
                <CollectForm reimbursementId={item.id} eventId={eventId} />
              ) : null}
            </li>
          ))}
        </ul>
      )}
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
          <p className="w-full text-sm text-red">Informe a descrição e o valor do reembolso.</p>
        )}
      </div>
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
