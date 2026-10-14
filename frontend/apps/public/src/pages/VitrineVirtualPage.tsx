import { Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { apiMoneyToNumber, useVitrineVirtual } from "../lib/virtuais";
import {
  AVISO_UM_FORMATO,
  FAQ_LOJA,
  FORMATOS,
  HERO,
  PASSOS,
  whatsappLink,
} from "../lib/lojaTema";
import {
  BOTAO_PRINCIPAL,
  BOTAO_SECUNDARIO,
  Ornamento,
  TituloSecao,
} from "../components/loja/LojaLayout";
import noelHero from "../assets/noel-hero.webp";

/**
 * Landing da Loja de Interações Virtuais — o que `alo.mantoproducoes.com.br` abre (feature 224e;
 * tema e copy da estação na 304).
 *
 * Antes a raiz do host caía na vitrine do catálogo de eventos: quem entrava pelo endereço da loja
 * de conversas recebia a grade de personagens para festa, que é outro produto.
 *
 * A ordem segue a da landing de campanha (FR-013) e o mesmo motivo: quem chega pelo Instagram quer
 * entender em três segundos e ver preço; dúvida vem depois, e o que o FAQ não resolve vira
 * WhatsApp. Mobile-first (Princípio X): coluna única, alvos ≥ 44px, nada abaixo de 12px em texto
 * informativo.
 *
 * A copy é da estação e mora em `lib/lojaTema.ts` — mudar exige deploy de propósito: é texto de
 * marca, não configuração de campanha (essa fica na tela de gestão, por campanha).
 */

function brl(valor: string | null): string {
  return valor ? `R$ ${formatBRL(apiMoneyToNumber(valor))}` : "—";
}

export function VitrineVirtualPage() {
  const { data, isLoading, isError } = useVitrineVirtual();
  const campanhas = data?.campanhas ?? [];
  // Com uma campanha só (o Natal tem uma), o botão do topo leva direto aos horários dela em vez
  // de rolar até uma lista de um item.
  const unica = campanhas.length === 1 ? campanhas[0] : null;

  return (
    <div className="mx-auto max-w-lg px-4 pt-8">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <header className="text-center">
        <p className="text-[12px] uppercase tracking-[0.3em] text-alo-muted">{HERO.sobretitulo}</p>
        <Ornamento className="mt-3" />
        <h1 className="mt-4 font-alo-display text-alo-ink">
          <span className="block text-[26px] leading-tight">{HERO.linha1}</span>
          <span className="block bg-gradient-to-b from-[#f6e2ad] to-alo-gold-deep bg-clip-text text-[52px] italic leading-[1.05] text-transparent">
            {HERO.destaque}
          </span>
        </h1>
        <p className="mt-3 text-[15px] tracking-wide text-alo-muted">{HERO.subtitulo}</p>
      </header>

      <div className="relative mt-6 overflow-hidden rounded-2xl border border-alo-line">
        <img
          src={noelHero}
          alt="O Papai Noel sorrindo, de braços abertos, ao lado da árvore de Natal"
          width={960}
          height={732}
          className="block h-auto w-full"
        />
        {/* Esfuma a base da foto no verde da página, como nas artes. */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-alo-bg to-transparent" />
      </div>

      <p className="mt-5 text-center text-[15px] leading-relaxed text-alo-ink">{HERO.texto}</p>

      <div className="mt-5">
        {unica ? (
          <Link to={`/v/${unica.slug}`} className={BOTAO_PRINCIPAL}>
            {HERO.cta} →
          </Link>
        ) : (
          <a href="#reservas" className={BOTAO_PRINCIPAL}>
            {HERO.cta} →
          </a>
        )}
      </div>

      {/* ── Os dois formatos ─────────────────────────────────────────────── */}
      <section className="mt-12">
        <TituloSecao>Duas formas de encontrar o Papai Noel</TituloSecao>
        <div className="mt-4 grid gap-3">
          {(["ao_vivo", "gravado"] as const).map((chave) => (
            <div key={chave} className="rounded-2xl border border-alo-line bg-alo-surface p-4">
              <p className="font-alo-display text-[20px] text-alo-gold">{FORMATOS[chave].nome}</p>
              <p className="text-[12px] uppercase tracking-[0.15em] text-alo-muted">
                {FORMATOS[chave].detalhe}
              </p>
              <p className="mt-2 text-[14px] leading-relaxed text-alo-ink">{FORMATOS[chave].texto}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-[13px] text-alo-muted">{AVISO_UM_FORMATO}</p>
      </section>

      {/* ── Como funciona ────────────────────────────────────────────────── */}
      <section className="mt-12">
        <TituloSecao>Como funciona</TituloSecao>
        <ol className="mt-4 space-y-4">
          {PASSOS.map((passo, i) => (
            <li key={passo.titulo} className="flex gap-3">
              <span
                aria-hidden="true"
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-alo-gold/70 font-alo-display text-[15px] text-alo-gold"
              >
                {i + 1}
              </span>
              <div>
                <p className="font-semibold text-alo-ink">{passo.titulo}</p>
                <p className="text-[14px] text-alo-muted">{passo.texto}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ── Reservas ─────────────────────────────────────────────────────── */}
      <section id="reservas" className="mt-12 scroll-mt-4">
        <TituloSecao>Reservas abertas para o Natal</TituloSecao>

        {isLoading && (
          <div className="mt-4 space-y-4">
            <div className="h-64 animate-pulse rounded-2xl bg-alo-surface" />
          </div>
        )}

        {isError && (
          <p className="mt-4 text-[14px] text-alo-muted">
            Não conseguimos carregar agora. Atualize a página em instantes — ou fale com a gente
            pelo WhatsApp, que a gente resolve por lá.
          </p>
        )}

        {!isLoading && !isError && campanhas.length === 0 && (
          // O endereço vai em story e bio: alguém vai cair aqui antes de a agenda abrir.
          <div className="mt-4 rounded-2xl border border-alo-line bg-alo-surface p-6 text-center">
            <p className="font-alo-display text-[20px] text-alo-gold">
              A agenda do Papai Noel abre em breve
            </p>
            <p className="mt-2 text-[14px] text-alo-muted">
              Estamos acertando os horários. Volte em alguns dias — ou chame a gente no WhatsApp
              para avisarmos quando abrir.
            </p>
          </div>
        )}

        {campanhas.length > 0 && (
          <ul className="mt-4 space-y-4">
            {campanhas.map((campanha) => {
              const esgotada = !campanha.tem_horario && !campanha.tem_gravado;
              return (
                <li key={campanha.slug}>
                  <Link
                    to={`/v/${campanha.slug}`}
                    className="block overflow-hidden rounded-2xl border border-alo-line bg-alo-surface transition-colors hover:border-alo-gold/60"
                  >
                    {campanha.cover_url && (
                      <img
                        src={assetUrl(campanha.cover_url)}
                        alt={campanha.title}
                        loading="lazy"
                        className="h-56 w-full object-cover object-[50%_35%]"
                      />
                    )}
                    <div className="p-4">
                      <h3 className="font-alo-display text-[22px] leading-tight text-alo-ink">
                        {campanha.title}
                      </h3>
                      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-[14px]">
                        {campanha.tem_horario && (
                          <span className="text-alo-muted">
                            {FORMATOS.ao_vivo.nome} ·{" "}
                            <strong className="text-alo-ink">{brl(campanha.price_live)}</strong>
                          </span>
                        )}
                        {campanha.tem_gravado && (
                          <span className="text-alo-muted">
                            {FORMATOS.gravado.nome} ·{" "}
                            <strong className="text-alo-ink">{brl(campanha.price_recorded)}</strong>
                          </span>
                        )}
                      </div>
                      {esgotada ? (
                        // Não some da lista: quem recebeu o link e voltou depois precisa
                        // entender o que houve, em vez de achar que errou o endereço.
                        <p className="mt-2 text-[13px] text-alo-muted">
                          Sem vagas no momento — abra para ver os detalhes.
                        </p>
                      ) : (
                        <p className="mt-3 text-[15px] font-semibold text-alo-gold">
                          Ver horários →
                        </p>
                      )}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* ── FAQ, só no fim (mesma regra da landing de campanha) ──────────── */}
      <section className="mt-12">
        <TituloSecao>Perguntas frequentes</TituloSecao>
        <div className="mt-3 divide-y divide-alo-line">
          {FAQ_LOJA.map((item) => (
            <details key={item.pergunta} className="group py-2">
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

      <a
        href={whatsappLink()}
        target="_blank"
        rel="noopener noreferrer"
        className={`mt-8 ${BOTAO_SECUNDARIO}`}
      >
        Ficou com dúvida? Fale com a gente no WhatsApp
      </a>
    </div>
  );
}
