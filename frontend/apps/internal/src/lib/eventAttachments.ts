import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { EventoDetalhe } from "./agenda";

/**
 * Hooks de upload e gestão de anexos do evento (feature 153): nota fiscal, contrato,
 * comprovante de pagamento e reembolso. Mesmo padrão de `eventOps.ts`/`observations.ts` —
 * `useMutation` + `onSuccess → queryClient.setQueryData(["event", id], updated)`. As mutações
 * de upload enviam `FormData` (o `apiFetch` detecta e não força `Content-Type`, ver
 * `packages/api-client/src/client.ts`).
 */

function useEventMutation<TVars>(eventId: number, mutationFn: (vars: TVars) => Promise<EventoDetalhe>) {
  const queryClient = useQueryClient();
  return useMutation<EventoDetalhe, Error, TVars>({
    mutationFn,
    onSuccess: (updated) => {
      queryClient.setQueryData(["event", eventId], updated);
    },
  });
}

// ── Nota fiscal ───────────────────────────────────────────────────────────────

export interface AddInvoiceInput {
  amount?: number;
  issue_date?: string;
  file?: File;
}

export function useAddInvoice(eventId: number) {
  return useEventMutation<AddInvoiceInput>(eventId, (input) => {
    const form = new FormData();
    if (input.amount !== undefined) form.append("amount", String(input.amount));
    if (input.issue_date) form.append("issue_date", input.issue_date);
    if (input.file) form.append("file", input.file);
    return apiFetch<EventoDetalhe>(`/api/events/${eventId}/invoices`, { method: "POST", body: form });
  });
}

// ── Contrato ──────────────────────────────────────────────────────────────────

export function useAddContract(eventId: number) {
  return useEventMutation<File>(eventId, (file) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<EventoDetalhe>(`/api/events/${eventId}/contracts`, { method: "POST", body: form });
  });
}

export function useDeleteContract(eventId: number) {
  return useEventMutation<number>(eventId, (contractId) =>
    apiFetch<EventoDetalhe>(`/api/contracts/${contractId}`, { method: "DELETE" }),
  );
}

export function useToggleContractSigned(eventId: number) {
  return useEventMutation<number>(eventId, (contractId) =>
    apiFetch<EventoDetalhe>(`/api/contracts/${contractId}/toggle-signed`, { method: "POST" }),
  );
}

// ── Pagamento (comprovante de cachê) ────────────────────────────────────────────

export interface AddPaymentInput {
  amount: number;
  file: File;
}

export function useAddPayment(eventId: number) {
  return useEventMutation<AddPaymentInput>(eventId, ({ amount, file }) => {
    const form = new FormData();
    form.append("amount", String(amount));
    form.append("file", file);
    return apiFetch<EventoDetalhe>(`/api/events/${eventId}/payments`, { method: "POST", body: form });
  });
}

export function useEditPayment(eventId: number) {
  return useEventMutation<{ paymentId: number; amount: number }>(eventId, ({ paymentId, amount }) =>
    apiFetch<EventoDetalhe>(`/api/payments/${paymentId}`, {
      method: "PATCH",
      body: JSON.stringify({ amount }),
    }),
  );
}

export function useDeletePayment(eventId: number) {
  return useEventMutation<number>(eventId, (paymentId) =>
    apiFetch<EventoDetalhe>(`/api/payments/${paymentId}`, { method: "DELETE" }),
  );
}

// ── Reembolso ─────────────────────────────────────────────────────────────────

export interface AddReimbursementInput {
  description: string;
  amount: number;
  file?: File;
}

export function useAddReimbursement(eventId: number) {
  return useEventMutation<AddReimbursementInput>(eventId, ({ description, amount, file }) => {
    const form = new FormData();
    form.append("description", description);
    form.append("amount", String(amount));
    if (file) form.append("file", file);
    return apiFetch<EventoDetalhe>(`/api/events/${eventId}/reimbursements`, {
      method: "POST",
      body: form,
    });
  });
}

export interface CollectReimbursementInput {
  reimbursementId: number;
  collected_amount: number;
  file: File;
}

export function useCollectReimbursement(eventId: number) {
  return useEventMutation<CollectReimbursementInput>(
    eventId,
    ({ reimbursementId, collected_amount, file }) => {
      const form = new FormData();
      form.append("collected_amount", String(collected_amount));
      form.append("file", file);
      return apiFetch<EventoDetalhe>(`/api/reimbursements/${reimbursementId}/collect`, {
        method: "POST",
        body: form,
      });
    },
  );
}

export function useDeleteReimbursement(eventId: number) {
  return useEventMutation<number>(eventId, (reimbursementId) =>
    apiFetch<EventoDetalhe>(`/api/reimbursements/${reimbursementId}`, { method: "DELETE" }),
  );
}
