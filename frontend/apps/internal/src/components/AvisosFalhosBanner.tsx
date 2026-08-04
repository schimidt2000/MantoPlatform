import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, RotateCcw, Send } from "lucide-react";
import { Button } from "@manto/ui";
import { useReenviarAviso, useRegerarSala, type AvisoFalho } from "../lib/virtuais";

/**
 * Banner de falha de entrega automática (feature 205, FR-039c e FR-056a).
 *
 * Existe porque a falha silenciosa é o pior desfecho possível: o pedido está pago, a família está
 * esperando, e a única pista de que o e-mail não chegou era uma coluna no banco que nenhuma tela
 * lia. Quem atende o telefone quando a mãe liga precisa ver isso **antes** de jurar que enviou.
 *
 * Dois estados, com urgências diferentes:
 *
 * - **ainda tentando** — a varredura vai insistir sozinha; o banner informa, não cobra ação.
 * - **esgotado** — o sistema desistiu depois de 3 tentativas. Aqui alguém precisa agir, e o botão
 *   de reenvio é a ação; o WhatsApp segue como reforço quando nem o reenvio resolve.
 *
 * Compartilhado entre a Fila de Produção e o painel do evento de propósito: a mesma falha aparece
 * nos dois lugares, e duas montagens divergiriam no primeiro ajuste de texto (Princípio I).
 */
export function AvisosFalhosBanner({
  orderId,
  avisos,
  meetRetryEsgotado = false,
  meetAttempts = 0,
  whatsappUrl = null,
  compacto = false,
}: {
  orderId: number;
  avisos: AvisoFalho[];
  /** A sala parou de ser retentada — a família não tem por onde entrar na chamada. */
  meetRetryEsgotado?: boolean;
  meetAttempts?: number;
  whatsappUrl?: string | null;
  /** Versão enxuta para dentro da linha da tabela. */
  compacto?: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const reenviar = useReenviarAviso();
  const regerarSala = useRegerarSala();

  if (avisos.length === 0 && !meetRetryEsgotado) return null;

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      role="alert"
      className={`rounded-md border border-red/40 bg-red-soft px-3 py-2 ${
        compacto ? "text-[11px]" : "text-sm"
      }`}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red" aria-hidden />
        <div className="min-w-0 flex-1 space-y-2">
          <p className="font-medium text-red">
            {avisos.length > 0
              ? "Falha no envio de notificação"
              : "A sala da chamada não foi criada"}
          </p>

          {avisos.map((aviso) => (
            <div key={aviso.kind} className="space-y-1">
              <p className="text-ink">
                <span className="font-medium">{aviso.label}</span>{" "}
                {aviso.esgotado ? (
                  <span className="text-red">
                    — o sistema desistiu após {aviso.attempts} tentativa(s). A família não recebeu.
                  </span>
                ) : (
                  <span className="text-muted">
                    — {aviso.attempts} tentativa(s); a varredura ainda vai tentar de novo.
                  </span>
                )}
              </p>
              {aviso.error_message && (
                <p className="break-words text-[11px] text-muted">{aviso.error_message}</p>
              )}
              <Button
                size="sm"
                variant={aviso.esgotado ? "default" : "outline"}
                loading={reenviar.isPending && reenviar.variables?.kind === aviso.kind}
                onClick={() => reenviar.mutate({ orderId, kind: aviso.kind })}
              >
                <Send className="size-4" />
                Reenviar manualmente
              </Button>
            </div>
          ))}

          {meetRetryEsgotado && (
            <div className="space-y-1">
              <p className="text-ink">
                <span className="font-medium">Sala do Meet</span>{" "}
                <span className="text-red">
                  — não foi criada após {meetAttempts} tentativa(s). Sem ela, a família não tem por
                  onde entrar na chamada.
                </span>
              </p>
              <Button
                size="sm"
                loading={regerarSala.isPending}
                onClick={() => regerarSala.mutate({ orderId })}
              >
                <RotateCcw className="size-4" />
                Tentar criar a sala de novo
              </Button>
            </div>
          )}

          {(reenviar.isError || regerarSala.isError) && (
            <p className="text-[11px] text-red">
              {reenviar.error?.message ?? regerarSala.error?.message}
              {whatsappUrl && " — use o WhatsApp para o reforço manual."}
            </p>
          )}
          {reenviar.isSuccess && !reenviar.isPending && (
            <p className="text-[11px] text-green">Aviso entregue.</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
