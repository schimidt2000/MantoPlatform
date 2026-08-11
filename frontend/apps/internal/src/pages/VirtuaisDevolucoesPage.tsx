import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, CircleDollarSign } from "lucide-react";
import {
  Badge,
  Button,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  apiMoneyToNumber,
  useConcluirDevolucao,
  useVirtualRefunds,
  type VirtualRefund,
} from "../lib/virtuais";

/**
 * Devoluções da Loja de Interações Virtuais (feature 205, US3).
 *
 * Existe porque a InfinitePay **não publica API de estorno**: quando um pagamento chega para um
 * horário que já é de outra família, o sistema cancela o pedido e abre a devolução aqui — mas
 * quem devolve o dinheiro é uma pessoa, no painel da operadora.
 *
 * Por isso a tela mostra `invoice_slug` e `transaction_nsu`: são o que a equipe usa para achar a
 * cobrança lá, sem sair procurando. E por isso o item só sai da lista quando alguém marca como
 * concluído — nenhuma devolução pode se perder por esquecimento (FR-043).
 */

function RefundRow({ refund }: { refund: VirtualRefund }) {
  const concluir = useConcluirDevolucao();
  const [confirmando, setConfirmando] = useState(false);

  return (
    <TableRow>
      <TableCell>
        <div className="font-medium text-ink">{refund.order?.child_name ?? "—"}</div>
        <div className="text-[11px] text-muted">{refund.order?.campaign_title}</div>
        {/* A origem do conflito muda a conversa com a família (FR-018b): "sua reserva venceu" e
            "não conseguimos confirmar seu pagamento a tempo" não são a mesma frase, e a segunda
            é a que evita tratar como atrasada quem pagou em dia. */}
        <div
          className={`mt-1 text-[11px] ${refund.sem_confirmacao ? "text-red" : "text-muted"}`}
        >
          {refund.sem_confirmacao && "⚠ "}
          {refund.reason_label}
        </div>
      </TableCell>
      <TableCell align="right" className="font-medium">
        R$ {formatBRL(apiMoneyToNumber(refund.amount))}
      </TableCell>
      <TableCell>
        <div className="font-mono text-[11px] text-ink">{refund.invoice_slug ?? "—"}</div>
        <div className="font-mono text-[11px] text-muted">{refund.transaction_nsu ?? "—"}</div>
      </TableCell>
      <TableCell>
        <div className="text-[12px] text-ink">{refund.order?.contact_phone_display}</div>
        <div className="text-[11px] text-muted">{refund.order?.contact_email}</div>
      </TableCell>
      <TableCell>
        {refund.status === "pendente" ? (
          <Badge tone="red">Pendente</Badge>
        ) : (
          <Badge tone="green">Concluída</Badge>
        )}
      </TableCell>
      <TableCell align="right">
        {refund.status === "pendente" &&
          (confirmando ? (
            <div className="flex items-center justify-end gap-1">
              <Button
                size="sm"
                loading={concluir.isPending}
                onClick={() => concluir.mutate(refund.id)}
              >
                Confirmar
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirmando(false)}>
                Cancelar
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setConfirmando(true)}>
              <CheckCircle2 className="size-4" />
              Já devolvi
            </Button>
          ))}
      </TableCell>
    </TableRow>
  );
}

export function VirtuaisDevolucoesPage() {
  const reduceMotion = useReducedMotion();
  const { data, isLoading, isError } = useVirtualRefunds("pendente");
  const refunds = data?.refunds ?? [];

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Devoluções — Interações Virtuais"
        subtitle="Pagamentos que chegaram para horários já vendidos. O estorno é feito no painel da InfinitePay; aqui você marca como concluído."
      />

      {isLoading && <Skeleton className="h-24 w-full" />}

      {isError && (
        <div className="rounded-lg border border-red/30 bg-red-soft p-4 text-sm text-red">
          Não foi possível carregar as devoluções.
        </div>
      )}

      {!isLoading && !isError && refunds.length === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-line p-10 text-center">
          <CircleDollarSign className="size-8 text-muted" />
          <p className="text-sm text-muted">
            Nenhuma devolução pendente — nada de dinheiro parado.
          </p>
        </div>
      )}

      {!isLoading && !isError && refunds.length > 0 && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Table>
            <thead>
              <TableRow head>
                <TableCell as="th">Família</TableCell>
                <TableCell as="th" align="right">
                  Valor
                </TableCell>
                <TableCell as="th">Cobrança na operadora</TableCell>
                <TableCell as="th">Contato</TableCell>
                <TableCell as="th">Situação</TableCell>
                <TableCell as="th" align="right">
                  Ação
                </TableCell>
              </TableRow>
            </thead>
            <tbody>
              {refunds.map((refund) => (
                <RefundRow key={refund.id} refund={refund} />
              ))}
            </tbody>
          </Table>
        </motion.div>
      )}
    </div>
  );
}
