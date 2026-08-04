import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { formatBRL } from "@manto/money";
import {
  apiMoneyToNumber,
  usePedidoCompleto,
  usePedidoVirtual,
  useVerificarPedido,
} from "../lib/virtuais";

/**
 * Página de acompanhamento do pedido (feature 205, US2 + US5).
 *
 * É o destino do retorno do checkout: a família volta da InfinitePay e cai aqui, nunca numa página
 * em branco (FR-035a). Como a confirmação do pagamento é assíncrona, a página mostra "aguardando"
 * e vira "confirmado" sozinha quando o aviso chega — sem a família precisar recarregar nem saber o
 * que é pagamento assíncrono.
 *
 * **Validação dupla (FR-044a)**: o endereço do pedido sozinho mostra só situação, horário e valor.
 * Nome, idade, dicas, endereço e vídeo exigem também o telefone da compra — é o que impede que
 * quem tropece no link veja os dados de uma criança.
 *
 * A **sala** é a única exceção, e por um motivo prático: pedir mais uma etapa antes de uma chamada
 * de 10 minutos custaria a experiência inteira, e quem tem o link do pedido é quem comprou.
 */

const ROTULOS: Record<string, { titulo: string; texto: string }> = {
  reservado: {
    titulo: "Reserva feita",
    texto: "Seu horário está guardado. Conclua o pagamento para confirmar.",
  },
  aguardando: {
    titulo: "Aguardando confirmação do pagamento",
    texto:
      "Assim que o pagamento cair, esta página atualiza sozinha — pode deixar aberta. " +
      "Você também recebe um e-mail com a confirmação.",
  },
  pago: {
    titulo: "Tudo certo! Pagamento confirmado",
    texto: "Sua interação está garantida. Os detalhes de acesso chegam no seu e-mail.",
  },
  expirado: {
    titulo: "A reserva expirou",
    texto: "O horário voltou para a lista. Você pode escolher outro na página da campanha.",
  },
  cancelado: {
    titulo: "Pedido cancelado",
    texto: "A devolução do valor está em andamento. Qualquer dúvida, fale com a gente.",
  },
};

/** Contagem regressiva do soft lock, para a família saber quanto tempo tem (FR-019). */
function useContagem(ate: string | null): string | null {
  const [restante, setRestante] = useState<string | null>(null);
  useEffect(() => {
    if (!ate) {
      setRestante(null);
      return;
    }
    const alvo = new Date(ate).getTime();
    const tick = () => {
      const segundos = Math.max(0, Math.floor((alvo - Date.now()) / 1000));
      const m = String(Math.floor(segundos / 60)).padStart(2, "0");
      const s = String(segundos % 60).padStart(2, "0");
      setRestante(`${m}:${s}`);
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [ate]);
  return restante;
}

export function PedidoVirtualPage() {
  const { token } = useParams<{ token: string }>();
  const reduceMotion = useReducedMotion();
  const { data: pedido, isLoading, error } = usePedidoVirtual(token);
  const restante = useContagem(pedido?.locked_until ?? null);

  const [telefone, setTelefone] = useState("");
  const verificar = useVerificarPedido(token);
  // A consulta só liga depois da validação — antes disso ela devolveria 401, que aqui não é erro,
  // é a proteção funcionando.
  const { data: completoDaSessao } = usePedidoCompleto(token, verificar.isSuccess);
  const completo = verificar.data ?? completoDaSessao;
  const erroExtra = verificar.error as unknown as { attempts_left?: number } | null;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-3 px-4 py-10">
        <div className="h-8 w-2/3 animate-pulse rounded bg-surface-2" />
        <div className="h-24 animate-pulse rounded bg-surface-2" />
      </div>
    );
  }

  if (error || !pedido) {
    return (
      <div className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="font-display text-xl text-ink">Pedido não encontrado</h1>
        <p className="mt-2 text-sm text-muted">
          Confira o link que você recebeu — talvez tenha faltado um pedaço.
        </p>
      </div>
    );
  }

  const rotulo = ROTULOS[pedido.status] ?? ROTULOS.reservado;

  return (
    <motion.div
      className="mx-auto max-w-lg px-4 py-8"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <h1 className="font-display text-2xl text-ink">{rotulo.titulo}</h1>
      <p className="mt-2 text-sm text-ink">{rotulo.texto}</p>

      <dl className="mt-6 divide-y divide-line rounded-xl border border-line">
        {pedido.campaign && (
          <div className="flex items-center justify-between px-4 py-3">
            <dt className="text-[13px] text-muted">Campanha</dt>
            <dd className="text-[15px] text-ink">{pedido.campaign.title}</dd>
          </div>
        )}
        <div className="flex items-center justify-between px-4 py-3">
          <dt className="text-[13px] text-muted">Modalidade</dt>
          <dd className="text-[15px] text-ink">
            {pedido.modality === "ao_vivo" ? "Chamada ao vivo" : "Vídeo gravado"}
          </dd>
        </div>
        {pedido.start_at && (
          <div className="flex items-center justify-between px-4 py-3">
            <dt className="text-[13px] text-muted">Horário</dt>
            <dd className="text-[15px] text-ink">
              {new Date(pedido.start_at).toLocaleString("pt-BR", {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </dd>
          </div>
        )}
        <div className="flex items-center justify-between px-4 py-3">
          <dt className="text-[13px] text-muted">Total</dt>
          <dd className="text-[15px] font-bold text-ink">
            R$ {formatBRL(apiMoneyToNumber(pedido.total_value))}
          </dd>
        </div>
      </dl>

      {restante && pedido.status !== "pago" && (
        <p className="mt-3 text-[13px] text-muted">
          Seu horário fica guardado por mais <strong>{restante}</strong>.
        </p>
      )}

      {pedido.payment_url && pedido.status !== "pago" && (
        <a
          href={pedido.payment_url}
          className="mt-4 flex min-h-[48px] items-center justify-center rounded-xl bg-accent px-4 text-[15px] font-bold text-white"
        >
          Ir para o pagamento
        </a>
      )}

      {pedido.status === "expirado" && pedido.campaign && (
        <a
          href={`/v/${pedido.campaign.slug}`}
          className="mt-4 flex min-h-[48px] items-center justify-center rounded-xl border border-line px-4 text-[15px] text-ink"
        >
          Escolher outro horário
        </a>
      )}

      {/* Acesso à chamada: aparece assim que o pedido está pago. Fica fora da validação dupla
          de propósito — chegar atrasado numa chamada de 10 minutos por causa de uma etapa a mais
          custa a experiência inteira. Os dados da criança seguem protegidos. */}
      {pedido.status === "pago" && pedido.modality === "ao_vivo" && pedido.meet_url && (
        <div className="mt-4 rounded-xl border border-line p-4">
          <p className="text-[13px] text-muted">
            No horário marcado, é só entrar por aqui:
          </p>
          <a
            href={pedido.meet_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 flex min-h-[48px] items-center justify-center rounded-xl bg-accent px-4 text-[15px] font-bold text-white"
          >
            Entrar na chamada
          </a>
          <p className="mt-2 text-[12px] text-muted">
            Guarde este link — ele é só do seu pedido.
          </p>
        </div>
      )}

      {pedido.status === "pago" && pedido.modality === "ao_vivo" && pedido.meet_pending && (
        <p className="mt-4 rounded-xl border border-gold bg-gold-soft p-4 text-[13px] text-ink">
          Estamos preparando o link da sua chamada. Ele aparece aqui em instantes — e você também
          recebe por e-mail. Sua vaga já está garantida.
        </p>
      )}

      {/* Validação dupla: o endereço do pedido sozinho não mostra nada da criança (FR-044a). */}
      {pedido.status === "pago" && !completo && (
        <form
          className="mt-4 rounded-xl border border-line p-4"
          onSubmit={(e) => {
            e.preventDefault();
            verificar.mutate(telefone);
          }}
        >
          <label className="text-[13px] text-muted" htmlFor="telefone-confirmacao">
            Confirme o telefone da compra para ver os detalhes
          </label>
          <input
            id="telefone-confirmacao"
            inputMode="tel"
            autoComplete="tel"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder={pedido.phone_hint ?? "(11) 90000-0000"}
            className="mt-1 min-h-[48px] w-full rounded-lg border border-line bg-surface px-3 text-[15px] text-ink"
          />
          <p className="mt-1 text-[12px] text-muted">
            É assim que garantimos que só você vê os dados da sua criança.
          </p>

          {verificar.isError && (
            <p className="mt-2 text-[13px] text-red" role="alert">
              {verificar.error.message}
              {typeof verificar.error.fields === "undefined" &&
              erroExtra?.attempts_left !== undefined
                ? ` Restam ${erroExtra.attempts_left} tentativa(s).`
                : ""}
            </p>
          )}

          <button
            type="submit"
            disabled={verificar.isPending || telefone.trim().length < 8}
            className="mt-3 min-h-[48px] w-full rounded-xl bg-accent px-4 text-[15px] font-bold text-white disabled:opacity-60"
          >
            {verificar.isPending ? "Conferindo…" : "Ver meu pedido"}
          </button>
        </form>
      )}

      {completo && (
        <motion.div
          className="mt-4 space-y-4"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <dl className="divide-y divide-line rounded-xl border border-line">
            <div className="flex items-center justify-between px-4 py-3">
              <dt className="text-[13px] text-muted">Criança</dt>
              <dd className="text-[15px] text-ink">
                {completo.child_name}, {completo.child_age} anos
              </dd>
            </div>
            {completo.behavior_notes && (
              <div className="px-4 py-3">
                <dt className="text-[13px] text-muted">Dicas que você contou</dt>
                <dd className="mt-1 whitespace-pre-line text-[14px] text-ink">
                  {completo.behavior_notes}
                </dd>
              </div>
            )}
            {completo.gift && (
              <div className="flex items-center justify-between px-4 py-3">
                <dt className="text-[13px] text-muted">Presente</dt>
                <dd className="text-[15px] text-ink">{completo.gift.name}</dd>
              </div>
            )}
            {completo.delivery_address && (
              <div className="px-4 py-3">
                <dt className="text-[13px] text-muted">Entrega</dt>
                <dd className="mt-1 text-[14px] text-ink">{completo.delivery_address}</dd>
              </div>
            )}
          </dl>

          {/* O vídeo vem pelo endpoint que valida a cada requisição — nunca por link direto
              de arquivo (FR-038e). */}
          {completo.video_url ? (
            <div className="rounded-xl border border-line p-3">
              <p className="mb-2 text-[13px] text-muted">O vídeo da {completo.child_name}:</p>
              <video
                controls
                playsInline
                preload="metadata"
                className="w-full rounded-lg"
                src={completo.video_url}
              >
                Seu navegador não consegue exibir o vídeo.
              </video>
            </div>
          ) : (
            completo.modality === "gravado" && (
              <p className="rounded-xl border border-line p-4 text-[13px] text-muted">
                O vídeo está sendo gravado. Avisamos por e-mail assim que ficar pronto
                {completo.recorded_due_date
                  ? ` — o prazo é até ${new Date(completo.recorded_due_date).toLocaleDateString("pt-BR")}.`
                  : "."}
              </p>
            )
          )}
        </motion.div>
      )}

      {pedido.campaign?.whatsapp_phone && (
        <a
          href={`https://wa.me/${pedido.campaign.whatsapp_phone.replace(/\D/g, "")}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 flex min-h-[44px] items-center justify-center rounded-xl border border-line text-[15px] text-ink"
        >
          Falar com a gente
        </a>
      )}
    </motion.div>
  );
}
