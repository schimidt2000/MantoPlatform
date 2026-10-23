import { useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AvatarThumb, Combobox } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { EnderecoInput } from "../components/EnderecoInput";
import {
  apiMoneyToNumber,
  fieldErrorsFrom,
  getClientToken,
  lembrarReservaDaAba,
  renovarClientToken,
  tokenDaAbaPara,
  useAbandonarReserva,
  useContagemDeSegundos,
  useCampanhaVirtual,
  useHorariosVirtuais,
  useReservar,
  type VirtualModality,
  type VirtualSlotPublic,
} from "../lib/virtuais";
import { AVISO_UM_FORMATO, CAMPANHA, FAQ_LOJA, FORMATOS, whatsappLink } from "../lib/lojaTema";
import {
  BOTAO_PRINCIPAL,
  BOTAO_SECUNDARIO,
  Ornamento,
  TituloSecao,
  classeCampo,
} from "../components/loja/LojaLayout";

/**
 * Landing e checkout da Loja de Interações Virtuais (feature 205, US2; tema da estação na 304).
 *
 * Mobile-first de verdade (Princípio X): coluna única, alvos de toque ≥ 44px, nada de texto
 * informativo abaixo de 12px, e nenhuma largura fixa que force rolagem horizontal em 320px.
 *
 * O FAQ fica **apenas no fim da página** (FR-013): quem chegou pelo Instagram quer ver preço e
 * horário primeiro; a dúvida vem depois, e o que o FAQ não resolve vira WhatsApp.
 *
 * Cada reserva é de UM formato — chamada ao vivo ou vídeo gravado (decisão do dono, 304). A
 * cartinha não é campo: é algo que a criança faz durante a chamada, e o formulário só convida a
 * família a contar o que está escrito nela.
 */

const CAMPOS_ROLAVEIS = [
  "child_name",
  "child_age",
  "contact_phone",
  "contact_email",
  "delivery_address",
  "slot_id",
] as const;

/**
 * `start_at` chega sem fuso (`2026-12-20T14:00:00`): é a hora de parede de São Paulo, a mesma
 * que o time vê na agenda. Lemos dia e hora do próprio texto, sem passar por `Date`, para que uma
 * família em outro fuso veja o horário que foi de fato combinado.
 */
function diaDoHorario(iso: string): string {
  return iso.slice(0, 10);
}

function horaDoHorario(iso: string): string {
  return iso.slice(11, 16);
}

function rotuloDoDia(dia: string): string {
  const [ano, mes, d] = dia.split("-").map(Number);
  // Meio-dia: longe da virada do dia em qualquer fuso, só para o nome do dia da semana.
  const data = new Date(ano, mes - 1, d, 12);
  const texto = data.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function CampanhaVirtualPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();

  const { data: campanha, isLoading, error } = useCampanhaVirtual(slug);
  const [modalidade, setModalidade] = useState<VirtualModality>("ao_vivo");
  const { data: horarios, refetch: recarregarHorarios } = useHorariosVirtuais(
    slug,
    modalidade === "ao_vivo",
  );
  const reservar = useReservar(slug);

  const [slotId, setSlotId] = useState<number | null>(null);
  const [presenteId, setPresenteId] = useState<number | null>(null);
  const [nome, setNome] = useState("");
  const [idade, setIdade] = useState("");
  const [dicas, setDicas] = useState("");
  const [telefone, setTelefone] = useState("");
  const [email, setEmail] = useState("");
  const [endereco, setEndereco] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});
  const [avisoTopo, setAvisoTopo] = useState<string | null>(null);
  // 429 do mesmo telefone: o servidor manda o token da reserva que já existe, para a família
  // retomar ou abandonar (FR-020a da 205) — antes só lia "abandone-a" sem ter como.
  const [reservaExistente, setReservaExistente] = useState<string | null>(null);
  const abandonar = useAbandonarReserva();

  const refs = useRef<Record<string, HTMLElement | null>>({});
  const lockRestante = useContagemDeSegundos(reservar.data?.seconds_left);

  const precoInteracao = useMemo(() => {
    if (!campanha) return 0;
    return apiMoneyToNumber(
      modalidade === "ao_vivo" ? campanha.price_live : campanha.price_recorded,
    );
  }, [campanha, modalidade]);

  // Horários agrupados por dia, na ordem em que a API devolve (já cronológica).
  const dias = useMemo(() => {
    const grupos = new Map<string, VirtualSlotPublic[]>();
    for (const slot of horarios?.slots ?? []) {
      const dia = diaDoHorario(slot.start_at);
      grupos.set(dia, [...(grupos.get(dia) ?? []), slot]);
    }
    return [...grupos.entries()];
  }, [horarios]);

  const precoPresente = presenteId ? apiMoneyToNumber(campanha?.price_gift ?? null) : 0;
  const total = precoInteracao + precoPresente;
  const gravadoEsgotado = (campanha?.recorded_available ?? 0) <= 0;

  const enviar = () => {
    setErros({});
    setAvisoTopo(null);
    setReservaExistente(null);
    reservar.mutate(
      {
        modality: modalidade,
        slot_id: modalidade === "ao_vivo" ? slotId : null,
        gift_item_id: presenteId,
        client_token: getClientToken(),
        child_name: nome,
        child_age: Number(idade),
        behavior_notes: dicas,
        contact_phone: telefone,
        contact_email: email,
        delivery_address: endereco,
      },
      {
        onSuccess: (data) => {
          // Feature 310 (FR-036): a próxima reserva nesta aba (outro horário, o irmão) é um
          // pedido novo, não o link deste. Antes de trocar, guarda a prova para "abandonar".
          lembrarReservaDaAba(data.public_token, getClientToken());
          renovarClientToken();
          // O link da operadora abre em seguida; a família volta para a página do pedido.
          if (data.payment_url) window.location.href = data.payment_url;
          else navigate(`/v/pedido/${data.public_token}`);
        },
        onError: (erro) => {
          const campos = fieldErrorsFrom(erro);
          setErros(campos);

          // Nada do que a família digitou é apagado (Princípio V) — só destacamos o campo e
          // levamos o foco até ele.
          const primeiro = CAMPOS_ROLAVEIS.find((c) => c in campos);
          if (primeiro) {
            const el = refs.current[primeiro];
            el?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
            el?.focus?.();
          }

          const status = (erro as { status?: number }).status;
          if (status === 409) {
            setAvisoTopo(
              erro.message || "Este horário acabou de ser reservado. Escolha outro, por favor.",
            );
            setSlotId(null);
            void recarregarHorarios();
          } else if (status === 429) {
            setAvisoTopo(erro.message);
            const existente = (erro as { details?: Record<string, unknown> }).details
              ?.existing_order_token;
            setReservaExistente(typeof existente === "string" ? existente : null);
          } else if (status === 502 || status === 503) {
            setAvisoTopo(erro.message);
          }
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-3 px-4 py-6">
        <div className="h-72 animate-pulse rounded-2xl bg-alo-surface" />
        <div className="h-7 w-2/3 animate-pulse rounded bg-alo-surface" />
        <div className="h-24 animate-pulse rounded bg-alo-surface" />
      </div>
    );
  }

  if (error || !campanha) {
    const status = (error as { status?: number } | null)?.status;
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <Ornamento />
        <h1 className="mt-4 font-alo-display text-[26px] text-alo-gold">
          {status === 410 ? "As reservas estão fechadas por enquanto" : "Não encontramos esta página"}
        </h1>
        <p className="mt-3 text-[14px] text-alo-muted">
          {status === 410
            ? "A agenda está pausada. Fique de olho nas nossas redes — ou chame a gente no WhatsApp."
            : "Confira o link que você recebeu — talvez tenha faltado um pedaço."}
        </p>
        <a
          href={whatsappLink()}
          target="_blank"
          rel="noopener noreferrer"
          className={`mt-6 ${BOTAO_SECUNDARIO}`}
        >
          Falar com a gente no WhatsApp
        </a>
      </div>
    );
  }

  // O título da campanha do Natal já diz "com o Papai Noel"; repetir o personagem embaixo
  // seria eco. Só mostra quando o título não o nomeia.
  const mostrarPersonagem =
    campanha.character &&
    !campanha.title.toLowerCase().includes(campanha.character.name.toLowerCase());
  const dicasDoFormato = CAMPANHA.dicas[modalidade];
  // Campanha sem FAQ próprio herda o da loja (304): quem chega direto pelo link da campanha —
  // story, bio — nunca passa pela vitrine, e é justamente aqui, perto do "Reservar", que a dúvida
  // aparece. Uma fonte só para o texto, em vez de copiá-lo para o banco de cada campanha.
  const faq = campanha.faq.length > 0 ? campanha.faq : FAQ_LOJA;
  const cartao = (selecionado: boolean) =>
    `min-h-[44px] rounded-2xl border p-4 text-left transition-colors ${
      selecionado
        ? "border-alo-gold bg-alo-surface-2 ring-1 ring-alo-gold"
        : "border-alo-line bg-alo-surface hover:border-alo-gold/50"
    }`;

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      {campanha.cover_url && (
        <img
          src={assetUrl(campanha.cover_url) ?? undefined}
          alt={campanha.title}
          className="mb-5 w-full rounded-2xl border border-alo-line object-cover"
        />
      )}

      <h1 className="text-center font-alo-display text-[30px] leading-tight text-alo-ink">
        {campanha.title}
      </h1>
      {mostrarPersonagem && (
        <p className="text-center text-[14px] text-alo-muted">com {campanha.character?.name}</p>
      )}
      <Ornamento className="mt-3" />
      {campanha.intro_html && (
        <p className="mt-4 whitespace-pre-line text-[15px] leading-relaxed text-alo-ink">
          {campanha.intro_html}
        </p>
      )}

      <AnimatePresence>
        {avisoTopo && (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 rounded-xl border border-alo-gold bg-alo-surface-2 p-3 text-[14px] text-alo-ink"
            role="status"
          >
            {avisoTopo}
            {reservaExistente && (
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <Link to={`/v/pedido/${reservaExistente}`} className={BOTAO_SECUNDARIO}>
                  Ver a reserva que já tenho
                </Link>
                {/* Só a aba que criou a reserva tem a prova para abandoná-la. */}
                {tokenDaAbaPara(reservaExistente) && (
                  <button
                    type="button"
                    className={BOTAO_SECUNDARIO}
                    disabled={abandonar.isPending}
                    onClick={() =>
                      abandonar.mutate(
                        {
                          token: reservaExistente,
                          clientToken: tokenDaAbaPara(reservaExistente) ?? "",
                        },
                        {
                          onSuccess: () => enviar(),
                          onError: (erro) => {
                            setReservaExistente(null);
                            setAvisoTopo(erro.message);
                          },
                        },
                      )
                    }
                  >
                    {abandonar.isPending ? "Abandonando…" : "Abandonar e reservar este"}
                  </button>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Formato ────────────────────────────────────────────────────── */}
      <section className="mt-8">
        <TituloSecao>Escolha o formato</TituloSecao>
        <p className="mt-1 text-[13px] text-alo-muted">{AVISO_UM_FORMATO}</p>
        <div className="mt-3 grid gap-3">
          <button
            type="button"
            aria-pressed={modalidade === "ao_vivo"}
            onClick={() => setModalidade("ao_vivo")}
            className={cartao(modalidade === "ao_vivo")}
          >
            <span className="flex items-baseline justify-between gap-3">
              <span className="font-alo-display text-[19px] text-alo-gold">
                {FORMATOS.ao_vivo.nome}
              </span>
              <span className="font-bold text-alo-ink">
                R$ {formatBRL(apiMoneyToNumber(campanha.price_live))}
              </span>
            </span>
            <span className="block text-[12px] uppercase tracking-[0.12em] text-alo-muted">
              {FORMATOS.ao_vivo.detalhe}
            </span>
            <span className="mt-1 block text-[13px] text-alo-ink">
              A criança conversa ao vivo e pode mostrar a cartinha.
            </span>
          </button>

          <button
            type="button"
            aria-pressed={modalidade === "gravado"}
            disabled={gravadoEsgotado}
            onClick={() => setModalidade("gravado")}
            className={`${cartao(modalidade === "gravado")} disabled:cursor-not-allowed disabled:opacity-50`}
          >
            <span className="flex items-baseline justify-between gap-3">
              <span className="font-alo-display text-[19px] text-alo-gold">
                {FORMATOS.gravado.nome}
                {gravadoEsgotado && " · esgotado"}
              </span>
              <span className="font-bold text-alo-ink">
                R$ {formatBRL(apiMoneyToNumber(campanha.price_recorded))}
              </span>
            </span>
            <span className="block text-[12px] uppercase tracking-[0.12em] text-alo-muted">
              {FORMATOS.gravado.detalhe}
            </span>
            <span className="mt-1 block text-[13px] text-alo-ink">
              Um recado só para a sua criança, entregue em até {campanha.recorded_delivery_days}{" "}
              dias.
            </span>
          </button>
        </div>
      </section>

      {/* ── Horários ───────────────────────────────────────────────────── */}
      {modalidade === "ao_vivo" && (
        <section className="mt-8" ref={(el) => (refs.current.slot_id = el)} tabIndex={-1}>
          <TituloSecao>Escolha o dia e a hora</TituloSecao>
          {dias.length === 0 ? (
            <p className="mt-2 text-[14px] text-alo-muted">
              Nenhum horário livre agora. Fale com a gente pelo WhatsApp abaixo — ou escolha o
              vídeo gravado, que não tem hora marcada.
            </p>
          ) : (
            <>
              <p className="mt-1 text-[13px] text-alo-muted">Horário de Brasília.</p>
              <div className="mt-3 space-y-4">
                {dias.map(([dia, slots]) => (
                  <div key={dia}>
                    <p className="text-[14px] font-semibold text-alo-ink">{rotuloDoDia(dia)}</p>
                    <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
                      {slots.map((slot) => (
                        <button
                          key={slot.id}
                          type="button"
                          aria-pressed={slotId === slot.id}
                          onClick={() => setSlotId(slot.id)}
                          className={`min-h-[44px] rounded-lg border text-[15px] transition-colors ${
                            slotId === slot.id
                              ? "border-alo-gold bg-alo-gold font-bold text-alo-bg"
                              : "border-alo-line-strong bg-alo-surface text-alo-ink hover:border-alo-gold"
                          }`}
                        >
                          {horaDoHorario(slot.start_at)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          {erros.slot_id && <p className="mt-2 text-[13px] text-alo-error">{erros.slot_id}</p>}
        </section>
      )}

      {/* ── Presente 3D ────────────────────────────────────────────────── */}
      {campanha.gift_items.length > 0 && (
        <section className="mt-8">
          <TituloSecao>{CAMPANHA.presenteTitulo}</TituloSecao>
          <p className="mt-1 text-[13px] text-alo-muted">
            {CAMPANHA.presenteTexto} + R$ {formatBRL(apiMoneyToNumber(campanha.price_gift))}
          </p>
          {/* Acima de 10 peças, a grade viraria uma parede de miniaturas e o `Combobox`
              pesquisável é obrigatório (Princípio XII.1). Com poucas, a escolha visual direta é
              melhor no celular: a família vê o presente em vez de ler uma lista. */}
          {campanha.gift_items.length > 10 ? (
            <div className="mt-3">
              <Combobox
                options={campanha.gift_items.map((item) => ({
                  value: String(item.id),
                  label: item.name,
                  imageUrl: assetUrl(item.photo_url),
                  imageShape: "square" as const,
                }))}
                value={presenteId ? String(presenteId) : null}
                onChange={(valor) => setPresenteId(valor ? Number(valor) : null)}
                placeholder="Buscar um presente…"
                emptyMessage="Nenhum presente encontrado"
                clearable
              />
            </div>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2">
              {campanha.gift_items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={presenteId === item.id}
                  onClick={() => setPresenteId(presenteId === item.id ? null : item.id)}
                  className={`flex min-h-[44px] items-center gap-2 rounded-xl border px-2 py-1 ${
                    presenteId === item.id
                      ? "border-alo-gold bg-alo-surface-2 ring-1 ring-alo-gold"
                      : "border-alo-line bg-alo-surface"
                  }`}
                >
                  <AvatarThumb
                    src={assetUrl(item.photo_url)}
                    name={item.name}
                    shape="square"
                    size="sm"
                    fallbackIcon="🎁"
                  />
                  <span className="text-[14px] text-alo-ink">{item.name}</span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Ficha da criança ───────────────────────────────────────────── */}
      <section className="mt-8 space-y-4">
        <TituloSecao>{CAMPANHA.fichaTitulo}</TituloSecao>

        <div>
          <label className="text-[13px] text-alo-muted" htmlFor="child_name">
            Nome da criança
          </label>
          <input
            id="child_name"
            ref={(el) => (refs.current.child_name = el)}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            autoComplete="off"
            className={classeCampo(Boolean(erros.child_name))}
          />
          {erros.child_name && <p className="mt-1 text-[13px] text-alo-error">{erros.child_name}</p>}
        </div>

        <div>
          <label className="text-[13px] text-alo-muted" htmlFor="child_age">
            Idade
          </label>
          <input
            id="child_age"
            ref={(el) => (refs.current.child_age = el)}
            type="number"
            inputMode="numeric"
            min={0}
            value={idade}
            onChange={(e) => setIdade(e.target.value)}
            className={classeCampo(Boolean(erros.child_age))}
          />
          {erros.child_age && <p className="mt-1 text-[13px] text-alo-error">{erros.child_age}</p>}
        </div>

        <div>
          <label className="text-[13px] text-alo-muted" htmlFor="behavior_notes">
            {dicasDoFormato.rotulo}
          </label>
          <textarea
            id="behavior_notes"
            value={dicas}
            onChange={(e) => setDicas(e.target.value)}
            placeholder={dicasDoFormato.exemplo}
            rows={4}
            className={`${classeCampo(false)} py-2 leading-relaxed`}
          />
        </div>

        <div>
          <label className="text-[13px] text-alo-muted" htmlFor="contact_phone">
            Seu telefone (WhatsApp)
          </label>
          <input
            id="contact_phone"
            ref={(el) => (refs.current.contact_phone = el)}
            inputMode="tel"
            autoComplete="tel"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            className={classeCampo(Boolean(erros.contact_phone))}
          />
          {erros.contact_phone && (
            <p className="mt-1 text-[13px] text-alo-error">{erros.contact_phone}</p>
          )}
        </div>

        <div>
          <label className="text-[13px] text-alo-muted" htmlFor="contact_email">
            Seu e-mail
          </label>
          <input
            id="contact_email"
            ref={(el) => (refs.current.contact_email = el)}
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={classeCampo(Boolean(erros.contact_email))}
          />
          {erros.contact_email && (
            <p className="mt-1 text-[13px] text-alo-error">{erros.contact_email}</p>
          )}
          <p className="mt-1 text-[12px] text-alo-muted">
            É por aqui que mandamos a confirmação e a página do pedido.
          </p>
        </div>

        {presenteId && (
          <div ref={(el) => (refs.current.delivery_address = el)} tabIndex={-1}>
            <label className="text-[13px] text-alo-muted" htmlFor="delivery_address">
              Endereço de entrega do presente
            </label>
            <EnderecoInput
              id="delivery_address"
              value={endereco}
              onChange={setEndereco}
              invalid={Boolean(erros.delivery_address)}
            />
            {erros.delivery_address && (
              <p className="mt-1 text-[13px] text-alo-error">{erros.delivery_address}</p>
            )}
          </div>
        )}
      </section>

      {/* ── Total e envio ──────────────────────────────────────────────── */}
      <section className="mt-8 rounded-2xl border border-alo-gold/50 bg-alo-surface p-4">
        <div className="flex items-center justify-between">
          <span className="text-[15px] text-alo-muted">
            {modalidade === "ao_vivo" ? FORMATOS.ao_vivo.nome : FORMATOS.gravado.nome}
            {presenteId ? " + presente" : ""}
          </span>
          <span className="font-alo-display text-[24px] text-alo-gold">R$ {formatBRL(total)}</span>
        </div>

        {lockRestante && (
          <p className="mt-2 text-[13px] text-alo-muted">
            Horário guardado para você por mais <strong className="text-alo-ink">{lockRestante}</strong>.
          </p>
        )}

        <button
          type="button"
          onClick={enviar}
          disabled={reservar.isPending}
          className={`mt-4 ${BOTAO_PRINCIPAL}`}
        >
          {reservar.isPending ? "Reservando…" : "Reservar e pagar →"}
        </button>
        <p className="mt-2 text-center text-[12px] text-alo-muted">Cartão ou PIX, em link seguro.</p>

        {campanha.tolerance_terms && (
          <p className="mt-3 whitespace-pre-line border-t border-alo-line pt-3 text-[12px] leading-relaxed text-alo-muted">
            {campanha.tolerance_terms}
          </p>
        )}
      </section>

      {/* ── FAQ (somente no fim da página — FR-013) ────────────────────── */}
      {faq.length > 0 && (
        <section className="mt-10">
          <TituloSecao>Perguntas frequentes</TituloSecao>
          <div className="mt-3 divide-y divide-alo-line">
            {faq.map((item, i) => (
              <details key={i} className="group py-2">
                <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 text-[15px] text-alo-ink">
                  {item.pergunta}
                  <span aria-hidden="true" className="text-alo-gold transition-transform group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="pb-2 text-[14px] leading-relaxed text-alo-muted">{item.resposta}</p>
              </details>
            ))}
          </div>
        </section>
      )}

      <a
        href={whatsappLink(campanha.whatsapp_phone ?? undefined)}
        target="_blank"
        rel="noopener noreferrer"
        className={`mt-8 ${BOTAO_SECUNDARIO}`}
      >
        Ficou com dúvida? Fale com a gente no WhatsApp
      </a>
    </div>
  );
}
