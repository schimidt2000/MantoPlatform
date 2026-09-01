import { useState, type FormEvent } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  FileUpload,
  Input,
} from "@manto/ui";
import { formatBRL, MoneyInput } from "@manto/money";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import {
  useAddSalaryAdvance,
  useDeleteSalaryAdvance,
  type PagamentoItem,
} from "../../lib/financeiro";
import { brl, formatDate, todayIso } from "../../lib/pagamentos";

/** Espelha `ALLOWED_DOCUMENT_EXTENSIONS` (`app/storage.py`): foto do papel ou PDF. */
const PROOF_ACCEPT = ".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif";
/** Mesmo teto do endpoint (`api_salary_advance`) — anunciar aqui evita o 400 depois do upload. */
const PROOF_MAX_BYTES = 10 * 1024 * 1024;

const MONEY_INPUT_CLASS =
  "h-11 w-full rounded-md border border-line-strong bg-panel px-3 text-sm text-ink " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

interface SalaryAdvancesDialogProps {
  /**
   * Item de salário lido DIRETO da query da planilha — nunca uma cópia congelada em
   * `useState`. Adicionar/remover adiantamento muda o próprio item no servidor; com um
   * instantâneo, o diálogo continuaria mostrando o total antigo depois de gravar.
   */
  item: PagamentoItem;
  open: boolean;
  onClose: () => void;
}

/**
 * Janela sobreposta de adiantamentos de salário (feature 226).
 *
 * Substitui o `<details>` que abria dentro da célula "Valor": mexer em dinheiro dentro de uma
 * célula de tabela obrigava a rolar a planilha de lado para achar o formulário, e no celular
 * ele nascia com 28px de largura. Aqui o diálogo repete o que a versão Jinja tinha
 * (`#adv-modal`): bruto, lista do que já foi adiantado, líquido a pagar e o formulário.
 */
export function SalaryAdvancesDialog({ item, open, onClose }: SalaryAdvancesDialogProps) {
  const addAdvance = useAddSalaryAdvance();
  const deleteAdvance = useDeleteSalaryAdvance();

  const [amount, setAmount] = useState(0);
  const [advanceDate, setAdvanceDate] = useState(todayIso());
  const [proof, setProof] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  /** Trocar a chave zera o nome do arquivo guardado dentro do `FileUpload` após gravar. */
  const [formNonce, setFormNonce] = useState(0);
  /** Adiantamento aguardando confirmação de remoção (Princípio V, sem `window.confirm`). */
  const [confirmingId, setConfirmingId] = useState<number | null>(null);

  const advances = item.advances ?? [];
  /** O que ainda cabe adiantar: o backend recusa `total adiantado + novo > salário bruto`. */
  const disponivel = item.amount;
  const podeAdiantar = typeof item.id === "number" && disponivel > 0;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    if (typeof item.id !== "number") return;
    if (amount <= 0) {
      setLocalError("Informe um valor de adiantamento maior que zero.");
      return;
    }
    if (amount > disponivel) {
      setLocalError(
        `A soma dos adiantamentos não pode passar do salário — ainda cabem ${brl(disponivel)}.`,
      );
      return;
    }
    if (!proof) {
      setLocalError("Anexe o comprovante do adiantamento.");
      return;
    }
    addAdvance.mutate(
      {
        salaryPaymentId: item.id,
        amount: formatBRL(amount),
        advanceDate: advanceDate || undefined,
        proof,
      },
      {
        onSuccess: () => {
          setAmount(0);
          setAdvanceDate(todayIso());
          setProof(null);
          setFormNonce((n) => n + 1);
        },
      },
    );
  };

  const handleDelete = (advanceId: number) => {
    setLocalError(null);
    deleteAdvance.mutate(advanceId, { onSettled: () => setConfirmingId(null) });
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Adiantamentos de salário</DialogTitle>
          <DialogDescription>
            {item.person_name || "Funcionário"} · vencimento em {formatDate(item.date)}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-3 gap-2 rounded-md border border-line bg-surface-2 p-3 text-center">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted">Salário</div>
            <div className="text-sm font-bold tabular-nums text-ink">{brl(item.gross_amount)}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted">Adiantado</div>
            <div className="text-sm font-bold tabular-nums text-gold-ink">
              {brl(item.advance_amount)}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted">A pagar</div>
            <div className="text-sm font-bold tabular-nums text-ink">{brl(item.amount)}</div>
          </div>
        </div>

        <section className="mt-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
            Adiantamentos lançados
          </h3>
          {advances.length === 0 ? (
            <p className="mt-1 text-sm text-muted">Nenhum adiantamento ainda.</p>
          ) : (
            <ul className="mt-1 divide-y divide-line">
              {advances.map((advance) => {
                const proofUrl = assetUrl(advance.proof);
                const confirming = confirmingId === advance.id;
                return (
                  <li key={advance.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                    <span className="font-bold tabular-nums text-ink">{brl(advance.amount)}</span>
                    <span className="text-xs text-muted">{formatDate(advance.date)}</span>
                    {proofUrl ? (
                      <a
                        href={proofUrl}
                        target="_blank"
                        rel="noopener"
                        className="text-xs text-blue hover:underline"
                      >
                        ver comprovante
                      </a>
                    ) : (
                      <span className="text-xs text-muted">sem comprovante</span>
                    )}
                    <span className="ml-auto flex items-center gap-1">
                      {confirming ? (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-red"
                            loading={deleteAdvance.isPending}
                            onClick={() => handleDelete(advance.id)}
                          >
                            Confirmar
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            disabled={deleteAdvance.isPending}
                            onClick={() => setConfirmingId(null)}
                          >
                            Cancelar
                          </Button>
                        </>
                      ) : (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="text-red"
                          disabled={deleteAdvance.isPending}
                          onClick={() => setConfirmingId(advance.id)}
                        >
                          Remover
                        </Button>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          {deleteAdvance.isError && (
            <p className="mt-1 text-sm text-red" role="alert">
              {errorMessage(deleteAdvance.error, "Não foi possível remover o adiantamento.")}
            </p>
          )}
        </section>

        {podeAdiantar ? (
          <form onSubmit={handleSubmit} className="mt-4 space-y-3 border-t border-line pt-4">
            <h3 className="text-xs font-bold uppercase tracking-wide text-muted">
              Novo adiantamento
            </h3>
            <div className="flex flex-wrap gap-3">
              <label className="min-w-0 flex-1">
                <span className="mb-1 block text-sm text-muted">Valor (máx. {brl(disponivel)})</span>
                <MoneyInput
                  value={amount}
                  // Voltar a digitar apaga o resultado do envio anterior — senão o "Adiantamento
                  // registrado." fica pendurado ao lado de um valor novo, ainda não enviado.
                  onValueChange={(next) => {
                    setAmount(next);
                    setLocalError(null);
                    if (addAdvance.isSuccess || addAdvance.isError) addAdvance.reset();
                  }}
                  className={MONEY_INPUT_CLASS}
                  aria-label="Valor do adiantamento"
                  aria-invalid={Boolean(fieldError(addAdvance.error, "amount"))}
                  disabled={addAdvance.isPending}
                />
              </label>
              <label className="min-w-0 flex-1">
                <span className="mb-1 block text-sm text-muted">Data</span>
                <Input
                  type="date"
                  value={advanceDate}
                  onChange={(e) => setAdvanceDate(e.target.value)}
                  aria-label="Data do adiantamento"
                  disabled={addAdvance.isPending}
                />
              </label>
            </div>
            <FileUpload
              key={formNonce}
              label="Comprovante"
              required
              accept={PROOF_ACCEPT}
              maxSizeBytes={PROOF_MAX_BYTES}
              error={fieldError(addAdvance.error, "advance_proof")}
              onChange={(file) => {
                setProof(file);
                setLocalError(null);
              }}
            />
            {(localError || addAdvance.isError) && (
              <p className="text-sm text-red" role="alert">
                {localError ??
                  errorMessage(addAdvance.error, "Não foi possível registrar o adiantamento.")}
              </p>
            )}
            {addAdvance.isSuccess && !localError && (
              <p aria-live="polite" className="text-sm text-green">
                Adiantamento registrado.
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Fechar
              </Button>
              <Button type="submit" loading={addAdvance.isPending}>
                Adicionar adiantamento
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-4 border-t border-line pt-4">
            <p className="text-sm text-muted">
              {typeof item.id === "number"
                ? "O salário já está totalmente adiantado — remova um lançamento acima para abrir espaço."
                : "Este lançamento não aceita adiantamento."}
            </p>
            <div className="mt-3 flex justify-end">
              <Button type="button" variant="ghost" onClick={onClose}>
                Fechar
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
