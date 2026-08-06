import { Badge } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { PortalRole } from "../lib/portalAgenda";

/**
 * Exibição do cachê do artista — fonte única para Convites, Agenda e Histórico.
 *
 * Existe como componente porque a ausência dele foi exatamente a origem do bug relatado: cada
 * tela decidia por conta própria se mostrava o valor, e a de Convites — a única em que o número
 * muda a decisão — simplesmente não mostrava. Centralizando, uma tela nova nasce certa.
 *
 * Três estados distintos de propósito:
 * - `cache_defined === false`: a produção ainda não definiu o valor. Nunca escrever "R$ 0,00"
 *   aqui — anunciaria um cachê zerado que ninguém combinou.
 * - deslocamento > 0: mostra o total e abre a composição, senão o artista estranha a diferença
 *   entre o combinado e o que aparece.
 * - `payment` (só no histórico): pago/a receber. Em convite e evento futuro esse rótulo seria
 *   ruído — nada foi pago ainda porque o evento nem aconteceu.
 */
export function CacheLine({
  role,
  variant = "linha",
  payment = false,
}: {
  role: PortalRole;
  /** `destaque` para a decisão de aceitar um convite; `linha` para listagens. */
  variant?: "destaque" | "linha";
  /** Exibe a situação de pagamento — só faz sentido em evento já realizado. */
  payment?: boolean;
}) {
  if (!role.cache_defined) {
    return (
      <p className={variant === "destaque" ? "text-sm text-muted" : "text-xs text-muted"}>
        Cachê a combinar com a produção
      </p>
    );
  }

  const temDeslocamento = role.travel_cache > 0;

  if (variant === "destaque") {
    return (
      <div className="rounded-lg border border-line bg-surface-2 px-3 py-2.5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">Você recebe</p>
        <p className="text-2xl font-semibold tabular-nums text-ink">
          R$ {formatBRL(role.cache_total)}
        </p>
        {temDeslocamento && (
          <p className="text-xs text-muted">
            R$ {formatBRL(role.cache_value)} de cachê + R$ {formatBRL(role.travel_cache)} de
            deslocamento
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <p className="text-sm text-ink">
        Cachê{" "}
        <strong className="font-semibold tabular-nums">R$ {formatBRL(role.cache_total)}</strong>
      </p>
      {payment && (
        <Badge tone={role.payment_status === "pago" ? "green" : "neutral"}>
          {role.payment_status === "pago" ? "PAGO" : "A RECEBER"}
        </Badge>
      )}
      {temDeslocamento && (
        <span className="w-full text-xs text-muted">
          inclui R$ {formatBRL(role.travel_cache)} de deslocamento
        </span>
      )}
    </div>
  );
}
