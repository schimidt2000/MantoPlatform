import { Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { apiMoneyToNumber, useVitrineVirtual } from "../lib/virtuais";

/**
 * Landing da Loja de Interações Virtuais — o que `alo.mantoproducoes.com.br` abre (feature 224e).
 *
 * Antes a raiz do host caía na vitrine do catálogo de eventos: quem entrava pelo endereço da loja
 * de conversas recebia a grade de personagens para festa, que é outro produto.
 *
 * A ordem da página segue a da landing de campanha (FR-013) e o mesmo motivo: quem chega pelo
 * Instagram quer entender em três segundos e ver preço; dúvida vem depois, e o que o FAQ não
 * resolve vira WhatsApp. Mobile-first (Princípio X): coluna única, alvos ≥ 44px, nada abaixo de
 * 12px em texto informativo.
 *
 * O texto é fixo no código de propósito — é copy de marca, não configuração de campanha (essa
 * fica na tela de gestão, por campanha). Mudar exige deploy; se virar rotina, vira campo.
 */

/** Perguntas sobre o produto em geral. As específicas de cada personagem ficam na campanha. */
const FAQ = [
  {
    pergunta: "Como funciona a chamada?",
    resposta:
      "É uma videochamada pelo Google Meet. No dia, você abre o link que enviamos e o " +
      "personagem já está esperando. Não precisa instalar nada nem criar conta.",
  },
  {
    pergunta: "Quanto tempo dura?",
    resposta:
      "Dez minutos ao vivo, só para a sua criança. É tempo de conversar, cantar e ouvir " +
      "aquela história que ela quer contar.",
  },
  {
    pergunta: "O personagem sabe mesmo o nome dela?",
    resposta:
      "Sabe. Antes da chamada você conta o nome, a idade e o que ela mais gosta — o " +
      "brinquedo preferido, o irmão, o cachorro. O personagem chega sabendo de tudo.",
  },
  {
    pergunta: "E se ela travar de vergonha?",
    resposta:
      "Acontece muito, e é justamente aí que o personagem trabalha: ele puxa conversa, " +
      "pergunta, brinca. Quase sempre a criança solta antes do primeiro minuto.",
  },
  {
    pergunta: "Posso gravar?",
    resposta:
      "Pode, e a gente recomenda — mas com um segundo celular filmando o rosto dela. A " +
      "reação vale mais do que a tela da chamada.",
  },
  {
    pergunta: "Qual a diferença do vídeo gravado?",
    resposta:
      "No vídeo gravado o personagem grava uma mensagem só para a sua criança, com o nome " +
      "dela e o que você contar, e você recebe o arquivo para guardar e reassistir. Não é ao " +
      "vivo, então não tem hora marcada — e costuma ser a saída quando os horários acabam.",
  },
  {
    pergunta: "Como faço o pagamento?",
    resposta:
      "Por cartão ou PIX, num link seguro que aparece logo depois da reserva. O horário fica " +
      "guardado no seu nome enquanto você paga.",
  },
  {
    pergunta: "E se eu não puder no horário que reservei?",
    resposta:
      "Fale com a gente pelo WhatsApp o quanto antes. Cada personagem tem uma regra de " +
      "tolerância, que fica escrita na página dele — vale a pena ler antes de fechar.",
  },
];

const PASSOS = [
  {
    titulo: "Escolha quem vai ligar",
    texto: "Cada personagem tem seus horários e seu preço. Você escolhe o dia e a hora.",
  },
  {
    titulo: "Conte sobre a criança",
    texto:
      "Nome, idade e o que ela ama. Quanto mais você contar, mais a conversa parece mágica.",
  },
  {
    titulo: "No dia, é só atender",
    texto: "O link chega no seu e-mail. Abre, deixa ela na frente da tela e assiste.",
  },
];

function brl(valor: string | null): string {
  return valor ? `R$ ${formatBRL(apiMoneyToNumber(valor))}` : "—";
}

export function VitrineVirtualPage() {
  const { data, isLoading, isError } = useVitrineVirtual();
  const campanhas = data?.campanhas ?? [];

  return (
    <div className="mx-auto max-w-lg px-4 py-8">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <h1 className="font-display text-[28px] leading-tight text-ink">
        O personagem preferido dela liga. E sabe o nome dela.
      </h1>
      <p className="mt-3 text-[15px] text-ink">
        Dez minutos de conversa ao vivo, por vídeo. A gente prepara tudo antes — o nome, a idade,
        o brinquedo que ela não larga, o apelido do irmão. Ela só precisa atender.
      </p>

      {/* ── Como funciona ────────────────────────────────────────────────── */}
      <section className="mt-8">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted">Como funciona</h2>
        <ol className="mt-3 space-y-3">
          {PASSOS.map((passo, i) => (
            <li key={passo.titulo} className="flex gap-3">
              <span
                aria-hidden="true"
                className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold-soft text-[13px] font-bold text-gold-ink"
              >
                {i + 1}
              </span>
              <div>
                <p className="font-medium text-ink">{passo.titulo}</p>
                <p className="text-[13px] text-muted">{passo.texto}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ── Quem está disponível ─────────────────────────────────────────── */}
      <section className="mt-9">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
          Quem está disponível
        </h2>

        {isLoading && (
          <div className="mt-3 space-y-4">
            <div className="h-56 animate-pulse rounded-xl bg-surface-2" />
            <div className="h-56 animate-pulse rounded-xl bg-surface-2" />
          </div>
        )}

        {isError && (
          <p className="mt-3 text-sm text-muted">
            Não conseguimos carregar agora. Atualize a página em instantes — ou fale com a gente
            pelo WhatsApp, que a gente resolve por lá.
          </p>
        )}

        {!isLoading && !isError && campanhas.length === 0 && (
          // O endereço vai em story e bio: alguém vai cair aqui entre uma campanha e outra.
          <div className="mt-3 rounded-xl border border-line bg-surface-2 p-6 text-center">
            <p className="text-[15px] font-medium text-ink">
              Nenhuma conversa aberta no momento.
            </p>
            <p className="mt-1 text-[13px] text-muted">
              Estamos preparando as próximas datas. Volte em breve — ou chame a gente no WhatsApp
              para avisarmos quando abrir.
            </p>
          </div>
        )}

        {campanhas.length > 0 && (
          <ul className="mt-3 space-y-4">
            {campanhas.map((campanha) => {
              const esgotada = !campanha.tem_horario && !campanha.tem_gravado;
              return (
                <li key={campanha.slug}>
                  <Link
                    to={`/v/${campanha.slug}`}
                    className="block overflow-hidden rounded-xl border border-line transition-shadow hover:shadow-md"
                  >
                    {campanha.cover_url && (
                      <img
                        src={assetUrl(campanha.cover_url)}
                        alt={campanha.title}
                        loading="lazy"
                        className="h-48 w-full object-cover"
                      />
                    )}
                    <div className="p-4">
                      <h3 className="font-display text-lg text-ink">{campanha.title}</h3>
                      {campanha.character_name && (
                        <p className="text-sm text-muted">com {campanha.character_name}</p>
                      )}
                      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-[13px]">
                        {campanha.tem_horario && (
                          <span className="text-ink">
                            Ao vivo · <strong>{brl(campanha.price_live)}</strong>
                          </span>
                        )}
                        {campanha.tem_gravado && (
                          <span className="text-ink">
                            Vídeo gravado · <strong>{brl(campanha.price_recorded)}</strong>
                          </span>
                        )}
                      </div>
                      {esgotada ? (
                        // Não some da lista: quem recebeu o link e voltou depois precisa
                        // entender o que houve, em vez de achar que errou o endereço.
                        <p className="mt-2 text-[13px] text-muted">
                          Sem vagas no momento — abra para ver os detalhes.
                        </p>
                      ) : (
                        <p className="mt-3 text-[15px] font-medium text-gold-ink">
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
      <section className="mt-10">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
          Perguntas frequentes
        </h2>
        <div className="mt-2 divide-y divide-line">
          {FAQ.map((item) => (
            <details key={item.pergunta} className="py-2">
              <summary className="min-h-[44px] cursor-pointer text-[15px] text-ink">
                {item.pergunta}
              </summary>
              <p className="mt-1 text-[13px] text-muted">{item.resposta}</p>
            </details>
          ))}
        </div>
      </section>

      <p className="mt-8 text-center text-[13px] text-muted">
        Manto Produções · personagens vivos desde sempre
      </p>
    </div>
  );
}
