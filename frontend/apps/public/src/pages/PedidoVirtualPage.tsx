import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { formatBRL } from "@manto/money";
import {
  apiMoneyToNumber,
  useContagemDeSegundos,
  usePedidoCompleto,
  usePedidoVirtual,
  useRetornoCheckout,
  useVerificarPedido,
  type VirtualOrderSummary,
} from "../lib/virtuais";
import { DICAS_DO_DIA, FORMATOS, whatsappLink } from "../lib/lojaTema";
import {
  BOTAO_PRINCIPAL,
  BOTAO_SECUNDARIO,
  Ornamento,
  TituloSecao,
  classeCampo,
} from "../components/loja/LojaLayout";

/**
 * Página de acompanhamento do pedido (feature 205, US2 + US5; tema da estação na 304).
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
  // Feature 310 (FR-037): três esperas diferentes, três textos. Antes, quem voltava do checkout SEM
  // pagar lia "aguardando a confirmação do pagamento" e achava que tinha pago.
  gerando: {
    titulo: "Gerando o pagamento…",
    texto: "Seu horário está guardado. Em instantes aparece o botão para pagar — pode esperar aqui.",
  },
  reservado: {
    titulo: "Reserva feita",
    texto: "Seu horário está guardado. Conclua o pagamento para confirmar.",
  },
  aguardando: {
    titulo: "Ainda não identificamos o pagamento",
    texto:
      "Se você já pagou, esta página atualiza sozinha em instantes — pode deixar aberta. " +
      "Se ainda não, é só tocar em \"Ir para o pagamento\".",
  },
  confirmando: {
    titulo: "Confirmando o pagamento…",
    texto:
      "Recebemos o aviso da operadora e estamos conferindo. Esta página atualiza sozinha, e você " +
      "também recebe um e-mail com a confirmação.",
  },
  pago: {
    titulo: "Tudo certo! Reserva confirmada",
    texto: "O Papai Noel já está sabendo. Guarde esta página: é por ela que você chega a tudo.",
  },
  expirado: {
    titulo: "A reserva expirou",
    texto: "O pagamento não chegou a tempo e o horário voltou para a agenda. Você pode escolher outro.",
  },
  cancelado: {
    titulo: "Pedido cancelado",
    texto: "A devolução do valor está em andamento. Qualquer dúvida, fale com a gente.",
  },
};

/** `start_at` é hora de parede de São Paulo, sem fuso — lida do texto (ver CampanhaVirtualPage). */
function formatarHorario(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano} às ${iso.slice(11, 16)}`;
}

/**
 * Prazo do vídeo (`date.isoformat()`, `2026-12-20`). `new Date("2026-12-20")` é meia-noite em
 * UTC — no Brasil vira 19/12, um dia antes do prazo de verdade. Por isso a data sai do texto.
 */
function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/** Qual dos textos de espera vale para o pedido agora (feature 310, FR-037). */
function chaveDoRotulo(pedido: VirtualOrderSummary, confirmando: boolean): string {
  if (pedido.status === "reservado" && !pedido.payment_url) return "gerando";
  if ((pedido.status === "aguardando" || pedido.status === "reservado") &&
      (pedido.confirming || confirmando)) return "confirmando";
  return pedido.status;
}

/**
 * Lê UMA vez os identificadores que a InfinitePay põe na URL de retorno, manda ao servidor e
 * limpa a URL (feature 310, R3): o link compartilhado depois não carrega identificador nenhum.
 */
function useRetornoDoCheckout(token: string | undefined): boolean {
  const [params, setParams] = useSearchParams();
  const retorno = useRetornoCheckout(token);
  const enviado = useRef(false);
  useEffect(() => {
    const orderNsu = params.get("order_nsu");
    if (!token || !orderNsu || enviado.current) return;
    enviado.current = true;
    retorno.mutate({
      order_nsu: orderNsu,
      slug: params.get("slug"),
      transaction_nsu: params.get("transaction_nsu"),
      capture_method: params.get("capture_method"),
      receipt_url: params.get("receipt_url"),
    });
    setParams({}, { replace: true });
  }, [params, setParams, token, retorno]);
  return retorno.isPending;
}

export function PedidoVirtualPage() {
  const { token } = useParams<{ token: string }>();
  const reduceMotion = useReducedMotion();
  const { data: pedido, isLoading, error } = usePedidoVirtual(token);
  const restante = useContagemDeSegundos(pedido?.seconds_left);
  const conferindoRetorno = useRetornoDoCheckout(token);

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
        <div className="h-8 w-2/3 animate-pulse rounded bg-alo-surface" />
        <div className="h-24 animate-pulse rounded bg-alo-surface" />
      </div>
    );
  }

  if (error || !pedido) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <Ornamento />
        <h1 className="mt-4 font-alo-display text-[26px] text-alo-gold">Pedido não encontrado</h1>
        <p className="mt-3 text-[14px] text-alo-muted">
          Confira o link que você recebeu — talvez tenha faltado um pedaço.
        </p>
      </div>
    );
  }

  const rotulo = ROTULOS[chaveDoRotulo(pedido, conferindoRetorno)] ?? ROTULOS.reservado;
  const pago = pedido.status === "pago";
  const aoVivo = pedido.modality === "ao_vivo";

  return (
    <motion.div
      className="mx-auto max-w-lg px-4 py-10"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="text-center">
        <Ornamento />
        <h1 className="mt-4 font-alo-display text-[28px] leading-tight text-alo-gold">
          {rotulo.titulo}
        </h1>
        <p className="mt-2 text-[15px] text-alo-ink">{rotulo.texto}</p>
      </div>

      <dl className="mt-6 divide-y divide-alo-line rounded-2xl border border-alo-line bg-alo-surface">
        {pedido.campaign && (
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <dt className="text-[13px] text-alo-muted">Reserva</dt>
            <dd className="text-right text-[15px] text-alo-ink">{pedido.campaign.title}</dd>
          </div>
        )}
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <dt className="text-[13px] text-alo-muted">Formato</dt>
          <dd className="text-[15px] text-alo-ink">
            {aoVivo ? FORMATOS.ao_vivo.nome : FORMATOS.gravado.nome}
          </dd>
        </div>
        {pedido.start_at && (
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <dt className="text-[13px] text-alo-muted">Horário (Brasília)</dt>
            <dd className="text-[15px] text-alo-ink">{formatarHorario(pedido.start_at)}</dd>
          </div>
        )}
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <dt className="text-[13px] text-alo-muted">Total</dt>
          <dd className="text-[15px] font-bold text-alo-ink">
            R$ {formatBRL(apiMoneyToNumber(pedido.total_value))}
          </dd>
        </div>
      </dl>

      {restante && !pago && (
        <p className="mt-3 text-center text-[13px] text-alo-muted">
          Seu horário fica guardado por mais <strong className="text-alo-ink">{restante}</strong>.
        </p>
      )}

      {pedido.payment_url && !pago && (
        <a href={pedido.payment_url} className={`mt-4 ${BOTAO_PRINCIPAL}`}>
          Ir para o pagamento →
        </a>
      )}

      {pedido.status === "expirado" && pedido.campaign && (
        // `<Link>`, não `<a href>`: o href cru ignorava o basename `/catalogo` — em `alo.*`
        // virava `/catalogo/v/v/<slug>` e a família caía numa página em branco (304).
        <Link to={`/v/${pedido.campaign.slug}`} className={`mt-4 ${BOTAO_SECUNDARIO}`}>
          Escolher outro horário
        </Link>
      )}

      {/* Acesso à chamada: aparece assim que o pedido está pago. Fica fora da validação dupla
          de propósito — chegar atrasado numa chamada de 10 minutos por causa de uma etapa a mais
          custa a experiência inteira. Os dados da criança seguem protegidos. */}
      {pago && aoVivo && pedido.meet_url && (
        <div className="mt-6 rounded-2xl border border-alo-gold/50 bg-alo-surface p-4">
          <p className="text-[14px] text-alo-muted">No horário marcado, é só entrar por aqui:</p>
          <a
            href={pedido.meet_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`mt-3 ${BOTAO_PRINCIPAL}`}
          >
            Entrar na chamada com o Papai Noel
          </a>
          <p className="mt-2 text-[12px] text-alo-muted">Guarde este link — ele é só do seu pedido.</p>
        </div>
      )}

      {pago && aoVivo && pedido.meet_pending && (
        <p className="mt-6 rounded-2xl border border-alo-gold/50 bg-alo-surface p-4 text-[14px] text-alo-ink">
          Estamos preparando o link da sua chamada. Ele aparece aqui em instantes — e você também
          recebe por e-mail. Sua vaga já está garantida.
        </p>
      )}

      {pago && aoVivo && (
        <section className="mt-6">
          <TituloSecao>Para o grande dia</TituloSecao>
          <ul className="mt-3 space-y-2">
            {DICAS_DO_DIA.map((dica) => (
              <li key={dica} className="flex gap-2 text-[14px] text-alo-ink">
                <span aria-hidden="true" className="text-alo-gold">
                  ✦
                </span>
                {dica}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Validação dupla: o endereço do pedido sozinho não mostra nada da criança (FR-044a). */}
      {pago && !completo && (
        <form
          className="mt-6 rounded-2xl border border-alo-line bg-alo-surface p-4"
          onSubmit={(e) => {
            e.preventDefault();
            verificar.mutate(telefone);
          }}
        >
          <label className="text-[13px] text-alo-muted" htmlFor="telefone-confirmacao">
            Confirme o telefone da compra para ver os detalhes
          </label>
          <input
            id="telefone-confirmacao"
            inputMode="tel"
            autoComplete="tel"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder={pedido.phone_hint ?? "(11) 90000-0000"}
            className={`mt-1 ${classeCampo(false)}`}
          />
          <p className="mt-1 text-[12px] text-alo-muted">
            É assim que garantimos que só você vê os dados da sua criança.
          </p>

          {verificar.isError && (
            <p className="mt-2 text-[13px] text-alo-error" role="alert">
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
            className={`mt-3 ${BOTAO_PRINCIPAL}`}
          >
            {verificar.isPending ? "Conferindo…" : "Ver meu pedido"}
          </button>
        </form>
      )}

      {completo && (
        <motion.div
          className="mt-6 space-y-4"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <dl className="divide-y divide-alo-line rounded-2xl border border-alo-line bg-alo-surface">
            <div className="flex items-center justify-between gap-3 px-4 py-3">
              <dt className="text-[13px] text-alo-muted">Criança</dt>
              <dd className="text-[15px] text-alo-ink">
                {completo.child_name}, {completo.child_age} anos
              </dd>
            </div>
            {completo.behavior_notes && (
              <div className="px-4 py-3">
                <dt className="text-[13px] text-alo-muted">O que você contou</dt>
                <dd className="mt-1 whitespace-pre-line text-[14px] text-alo-ink">
                  {completo.behavior_notes}
                </dd>
              </div>
            )}
            {completo.gift && (
              <div className="flex items-center justify-between gap-3 px-4 py-3">
                <dt className="text-[13px] text-alo-muted">Presente</dt>
                <dd className="text-[15px] text-alo-ink">{completo.gift.name}</dd>
              </div>
            )}
            {completo.delivery_address && (
              <div className="px-4 py-3">
                <dt className="text-[13px] text-alo-muted">Entrega</dt>
                <dd className="mt-1 text-[14px] text-alo-ink">{completo.delivery_address}</dd>
              </div>
            )}
          </dl>

          {/* O vídeo vem pelo endpoint que valida a cada requisição — nunca por link direto
              de arquivo (FR-038e). */}
          {completo.video_url ? (
            <div className="rounded-2xl border border-alo-gold/50 bg-alo-surface p-3">
              <p className="mb-2 text-[14px] text-alo-muted">
                O vídeo do Papai Noel para {completo.child_name}:
              </p>
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
              <p className="rounded-2xl border border-alo-line bg-alo-surface p-4 text-[14px] text-alo-muted">
                O Papai Noel está preparando o vídeo. Avisamos por e-mail assim que ficar pronto
                {completo.recorded_due_date
                  ? ` — o prazo é até ${formatarData(completo.recorded_due_date)}.`
                  : "."}
              </p>
            )
          )}
        </motion.div>
      )}

      <a
        href={whatsappLink(pedido.campaign?.whatsapp_phone ?? undefined)}
        target="_blank"
        rel="noopener noreferrer"
        className={`mt-8 ${BOTAO_SECUNDARIO}`}
      >
        Falar com a gente no WhatsApp
      </a>
    </motion.div>
  );
}
