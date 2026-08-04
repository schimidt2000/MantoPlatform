import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AvatarThumb, Combobox } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { EnderecoInput } from "../components/EnderecoInput";
import {
  apiMoneyToNumber,
  fieldErrorsFrom,
  getClientToken,
  useCampanhaVirtual,
  useHorariosVirtuais,
  useReservar,
  type VirtualModality,
  type VirtualSlotPublic,
} from "../lib/virtuais";

/**
 * Landing e checkout da Loja de Interações Virtuais (feature 205, US2).
 *
 * Mobile-first de verdade (Princípio X): coluna única, alvos de toque ≥ 44px, nada de texto
 * informativo abaixo de 12px, e nenhuma largura fixa que force rolagem horizontal em 320px.
 *
 * O FAQ fica **apenas no fim da página** (FR-013): quem chegou pelo Instagram quer ver preço e
 * horário primeiro; a dúvida vem depois, e o que o FAQ não resolve vira WhatsApp.
 */

const CAMPOS_ROLAVEIS = [
  "child_name",
  "child_age",
  "contact_phone",
  "contact_email",
  "delivery_address",
  "slot_id",
] as const;

function formatarHorario(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Conta o tempo restante do soft lock (FR-019). */
function useContagemRegressiva(ate: string | null): string | null {
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

  const refs = useRef<Record<string, HTMLElement | null>>({});
  const lockRestante = useContagemRegressiva(reservar.data?.locked_until ?? null);

  const precoInteracao = useMemo(() => {
    if (!campanha) return 0;
    return apiMoneyToNumber(
      modalidade === "ao_vivo" ? campanha.price_live : campanha.price_recorded,
    );
  }, [campanha, modalidade]);

  const precoPresente = presenteId ? apiMoneyToNumber(campanha?.price_gift ?? null) : 0;
  const total = precoInteracao + precoPresente;
  const gravadoEsgotado = (campanha?.recorded_available ?? 0) <= 0;

  const enviar = () => {
    setErros({});
    setAvisoTopo(null);
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
              erro.message || "Esse horário acabou de ser reservado. Escolha outro, por favor.",
            );
            setSlotId(null);
            void recarregarHorarios();
          } else if (status === 429) {
            setAvisoTopo(erro.message);
          } else if (status === 502) {
            setAvisoTopo(erro.message);
          }
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-3 px-4 py-6">
        <div className="h-40 animate-pulse rounded-xl bg-surface-2" />
        <div className="h-6 w-2/3 animate-pulse rounded bg-surface-2" />
        <div className="h-24 animate-pulse rounded bg-surface-2" />
      </div>
    );
  }

  if (error || !campanha) {
    const status = (error as { status?: number } | null)?.status;
    return (
      <div className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="font-display text-xl text-ink">
          {status === 410 ? "Campanha encerrada por ora" : "Campanha não encontrada"}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {status === 410
            ? "As vendas desta campanha estão pausadas. Fique de olho nas nossas redes!"
            : "Confira o link que você recebeu — talvez tenha faltado um pedaço."}
        </p>
      </div>
    );
  }

  const campoInvalido = (campo: string) => (erros[campo] ? "border-red" : "border-line");

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      {campanha.cover_url && (
        <img
          src={assetUrl(campanha.cover_url) ?? undefined}
          alt={campanha.title}
          className="mb-4 w-full rounded-xl object-cover"
        />
      )}

      <h1 className="font-display text-2xl text-ink">{campanha.title}</h1>
      {campanha.character && (
        <p className="text-sm text-muted">com {campanha.character.name}</p>
      )}
      {campanha.intro_html && (
        <p className="mt-3 whitespace-pre-line text-sm text-ink">{campanha.intro_html}</p>
      )}

      <AnimatePresence>
        {avisoTopo && (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-4 rounded-lg border border-gold bg-gold-soft p-3 text-sm text-ink"
            role="status"
          >
            {avisoTopo}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Modalidade ─────────────────────────────────────────────────── */}
      <section className="mt-6">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted">O que você quer</h2>
        <div className="mt-2 grid gap-2">
          <button
            type="button"
            onClick={() => setModalidade("ao_vivo")}
            className={`min-h-[44px] rounded-xl border p-3 text-left ${
              modalidade === "ao_vivo" ? "border-accent bg-accent-soft" : "border-line"
            }`}
          >
            <span className="block font-medium text-ink">Chamada ao vivo · 10 minutos</span>
            <span className="block text-[13px] text-muted">
              R$ {formatBRL(apiMoneyToNumber(campanha.price_live))}
            </span>
          </button>

          <button
            type="button"
            disabled={gravadoEsgotado}
            onClick={() => setModalidade("gravado")}
            className={`min-h-[44px] rounded-xl border p-3 text-left disabled:opacity-50 ${
              modalidade === "gravado" ? "border-accent bg-accent-soft" : "border-line"
            }`}
          >
            <span className="block font-medium text-ink">
              Vídeo gravado {gravadoEsgotado && "· esgotado"}
            </span>
            <span className="block text-[13px] text-muted">
              R$ {formatBRL(apiMoneyToNumber(campanha.price_recorded))} · entrega em até{" "}
              {campanha.recorded_delivery_days} dias
            </span>
          </button>
        </div>
      </section>

      {/* ── Horários ───────────────────────────────────────────────────── */}
      {modalidade === "ao_vivo" && (
        <section className="mt-6" ref={(el) => (refs.current.slot_id = el)} tabIndex={-1}>
          <h2 className="text-sm font-bold uppercase tracking-wide text-muted">Escolha o horário</h2>
          {(horarios?.slots.length ?? 0) === 0 ? (
            <p className="mt-2 text-[13px] text-muted">
              Nenhum horário disponível agora. Fale com a gente pelo WhatsApp abaixo.
            </p>
          ) : (
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {horarios?.slots.map((slot: VirtualSlotPublic) => (
                <button
                  key={slot.id}
                  type="button"
                  onClick={() => setSlotId(slot.id)}
                  className={`min-h-[44px] rounded-lg border px-2 text-[13px] ${
                    slotId === slot.id ? "border-accent bg-accent-soft" : "border-line"
                  }`}
                >
                  {formatarHorario(slot.start_at)}
                </button>
              ))}
            </div>
          )}
          {erros.slot_id && <p className="mt-1 text-[12px] text-red">{erros.slot_id}</p>}
        </section>
      )}

      {/* ── Presente 3D ────────────────────────────────────────────────── */}
      {campanha.gift_items.length > 0 && (
        <section className="mt-6">
          <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
            Quer levar um presente?
          </h2>
          <p className="text-[13px] text-muted">
            + R$ {formatBRL(apiMoneyToNumber(campanha.price_gift))}
          </p>
          {/* Acima de 10 peças, a grade viraria uma parede de miniaturas e o `Combobox`
              pesquisável é obrigatório (Princípio XII.1). Com poucas, a escolha visual direta é
              melhor no celular: a mãe vê o presente em vez de ler uma lista. */}
          {campanha.gift_items.length > 10 ? (
            <div className="mt-2">
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
            <div className="mt-2 flex flex-wrap gap-2">
              {campanha.gift_items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={presenteId === item.id}
                  onClick={() => setPresenteId(presenteId === item.id ? null : item.id)}
                  className={`flex min-h-[44px] items-center gap-2 rounded-lg border px-2 py-1 ${
                    presenteId === item.id ? "border-accent bg-accent-soft" : "border-line"
                  }`}
                >
                  <AvatarThumb
                    src={assetUrl(item.photo_url)}
                    name={item.name}
                    shape="square"
                    size="sm"
                    fallbackIcon="🎁"
                  />
                  <span className="text-[13px] text-ink">{item.name}</span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Ficha da criança ───────────────────────────────────────────── */}
      <section className="mt-6 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted">Sobre a criança</h2>

        <div>
          <label className="text-[13px] text-muted" htmlFor="child_name">
            Nome da criança
          </label>
          <input
            id="child_name"
            ref={(el) => (refs.current.child_name = el)}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            className={`min-h-[44px] w-full rounded-lg border bg-surface px-3 text-[15px] text-ink ${campoInvalido("child_name")}`}
          />
          {erros.child_name && <p className="mt-1 text-[12px] text-red">{erros.child_name}</p>}
        </div>

        <div>
          <label className="text-[13px] text-muted" htmlFor="child_age">
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
            className={`min-h-[44px] w-full rounded-lg border bg-surface px-3 text-[15px] text-ink ${campoInvalido("child_age")}`}
          />
          {erros.child_age && <p className="mt-1 text-[12px] text-red">{erros.child_age}</p>}
        </div>

        <div>
          <label className="text-[13px] text-muted" htmlFor="behavior_notes">
            Dicas para o personagem (o que ela adora, quem são os irmãos…)
          </label>
          <textarea
            id="behavior_notes"
            value={dicas}
            onChange={(e) => setDicas(e.target.value)}
            className="min-h-24 w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink"
          />
        </div>

        <div>
          <label className="text-[13px] text-muted" htmlFor="contact_phone">
            Telefone (WhatsApp)
          </label>
          <input
            id="contact_phone"
            ref={(el) => (refs.current.contact_phone = el)}
            inputMode="tel"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            className={`min-h-[44px] w-full rounded-lg border bg-surface px-3 text-[15px] text-ink ${campoInvalido("contact_phone")}`}
          />
          {erros.contact_phone && (
            <p className="mt-1 text-[12px] text-red">{erros.contact_phone}</p>
          )}
        </div>

        <div>
          <label className="text-[13px] text-muted" htmlFor="contact_email">
            E-mail
          </label>
          <input
            id="contact_email"
            ref={(el) => (refs.current.contact_email = el)}
            type="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={`min-h-[44px] w-full rounded-lg border bg-surface px-3 text-[15px] text-ink ${campoInvalido("contact_email")}`}
          />
          {erros.contact_email && (
            <p className="mt-1 text-[12px] text-red">{erros.contact_email}</p>
          )}
          <p className="mt-1 text-[12px] text-muted">
            É por aqui que mandamos a confirmação e o acesso.
          </p>
        </div>

        {presenteId && (
          <div ref={(el) => (refs.current.delivery_address = el)} tabIndex={-1}>
            <label className="text-[13px] text-muted" htmlFor="delivery_address">
              Endereço de entrega do presente
            </label>
            <EnderecoInput
              id="delivery_address"
              value={endereco}
              onChange={setEndereco}
              invalid={Boolean(erros.delivery_address)}
            />
            {erros.delivery_address && (
              <p className="mt-1 text-[12px] text-red">{erros.delivery_address}</p>
            )}
          </div>
        )}
      </section>

      {/* ── Total e envio ──────────────────────────────────────────────── */}
      <section className="mt-6 rounded-xl border border-line p-4">
        <div className="flex items-center justify-between">
          <span className="text-[15px] text-ink">Total</span>
          <span className="text-lg font-bold text-ink">R$ {formatBRL(total)}</span>
        </div>

        {lockRestante && (
          <p className="mt-2 text-[13px] text-muted">
            Horário reservado para você por mais <strong>{lockRestante}</strong>.
          </p>
        )}

        <button
          type="button"
          onClick={enviar}
          disabled={reservar.isPending}
          className="mt-3 min-h-[48px] w-full rounded-xl bg-accent px-4 text-[15px] font-bold text-white disabled:opacity-60"
        >
          {reservar.isPending ? "Reservando…" : "Reservar e pagar"}
        </button>

        {campanha.tolerance_terms && (
          <p className="mt-3 text-[12px] text-muted">{campanha.tolerance_terms}</p>
        )}
      </section>

      {/* ── FAQ (somente no fim da página — FR-013) ────────────────────── */}
      {campanha.faq.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
            Perguntas frequentes
          </h2>
          <div className="mt-2 divide-y divide-line">
            {campanha.faq.map((item, i) => (
              <details key={i} className="py-2">
                <summary className="min-h-[44px] cursor-pointer text-[15px] text-ink">
                  {item.pergunta}
                </summary>
                <p className="mt-1 text-[13px] text-muted">{item.resposta}</p>
              </details>
            ))}
          </div>
        </section>
      )}

      {campanha.whatsapp_phone && (
        <a
          href={`https://wa.me/${campanha.whatsapp_phone.replace(/\D/g, "")}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 flex min-h-[44px] items-center justify-center rounded-xl border border-line text-[15px] text-ink"
        >
          Ficou com dúvida? Fale com a gente
        </a>
      )}
    </div>
  );
}
