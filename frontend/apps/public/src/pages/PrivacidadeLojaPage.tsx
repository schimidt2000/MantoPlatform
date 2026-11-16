import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Ornamento, TituloSecao } from "../components/loja/LojaLayout";
import { whatsappLink } from "../lib/lojaTema";
import { esquecerConsentimento, lerConsentimento } from "../lib/pixel";
import { useRastreamento } from "../lib/virtuais";

/**
 * Aviso de privacidade da loja de conversas (feature 344, LGPD).
 *
 * Linguagem de gente, sem letra miúda: quem cuida, o que pedimos e para quê, com quem dividimos,
 * por quanto tempo, e como a pessoa exerce os direitos (pelo WhatsApp). O trecho dos cookies da
 * Meta só aparece quando o pixel está ligado. Mudou uma regra aqui? Confira `virtuais_ops` (o que
 * vai para a InfinitePay, a retenção das dicas) — o texto tem de dizer o que o sistema faz.
 */
export function PrivacidadeLojaPage() {
  const { data } = useRastreamento();
  const pixelLigado = Boolean(data?.meta_pixel_id);
  const escolha = lerConsentimento();

  return (
    <div className="mx-auto max-w-lg px-4 pb-6 pt-10">
      <Link to="/v" className="text-[14px] text-alo-gold underline underline-offset-2">
        ← Voltar para a loja
      </Link>

      <h1 className="mt-6 font-alo-display text-[30px] leading-tight text-alo-ink">
        Privacidade na loja
      </h1>
      <Ornamento className="mt-4" />
      <p className="mt-4 text-[15px] leading-relaxed text-alo-muted">
        Esta é a loja de conversas da Manto Produções. Aqui está, sem letra miúda, o que fazemos com
        os dados que você nos dá.
      </p>

      <Bloco titulo="Quem cuida dos seus dados">
        A Manto Produções, que organiza a chamada e o vídeo. Qualquer pedido sobre os seus dados é
        pelo{" "}
        <a
          href={whatsappLink()}
          target="_blank"
          rel="noopener noreferrer"
          className="text-alo-gold underline underline-offset-2"
        >
          nosso WhatsApp
        </a>
        .
      </Bloco>

      <Bloco titulo="O que pedimos e para quê">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-alo-ink">Sobre quem vai receber</strong> — nome, idade e as dicas
            que você escrever. Servem só para a conversa ou o vídeo sair do jeito certo. Nunca são
            usados para divulgação.
          </li>
          <li>
            <strong className="text-alo-ink">Sobre você</strong> — nome, telefone (WhatsApp) e e-mail,
            para a confirmação, a página do pedido, o pagamento e para falarmos com você se algo
            mudar.
          </li>
          <li>
            <strong className="text-alo-ink">Sobre a visita</strong> — de qual canal você chegou
            (Instagram, WhatsApp, Google…), contado só no total, sem saber quem é você. Para evitar
            abuso nas reservas, guardamos também uma marca embaralhada da rede e do aparelho, que não
            permite chegar ao seu endereço.
          </li>
        </ul>
      </Bloco>

      <Bloco titulo="Com quem dividimos">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong className="text-alo-ink">InfinitePay</strong>, que processa o pagamento: recebe
            o seu e-mail e o seu telefone — nada sobre quem vai receber.
          </li>
          <li>
            <strong className="text-alo-ink">Google</strong>, onde ficam a agenda da equipe e a sala
            da chamada (Google Meet).
          </li>
          {pixelLigado && (
            <li>
              <strong className="text-alo-ink">Meta</strong> (Facebook e Instagram), só se você
              aceitar os cookies — veja abaixo.
            </li>
          )}
        </ul>
        <p className="mt-2">Não vendemos nem emprestamos os seus dados.</p>
      </Bloco>

      <Bloco titulo="Novidades da Manto">
        Só mandamos novidades (festas, personagens, datas especiais) para quem marcou a caixinha
        "Quero receber novidades" na reserva. Mudou de ideia? Peça no WhatsApp e paramos.
      </Bloco>

      <Bloco titulo="Por quanto tempo">
        As dicas sobre quem vai receber são apagadas 30 dias depois da chamada (ou do prazo do
        vídeo). O registro da compra — valor, data e contato — fica guardado pelo tempo que a lei
        pede para vendas.
      </Bloco>

      <Bloco titulo="Seus direitos">
        Você pode pedir para ver, corrigir ou apagar os seus dados, saber com quem foram divididos e
        retirar o "sim" das novidades a qualquer momento. É só falar com a gente no WhatsApp.
      </Bloco>

      <Bloco titulo="Cookies">
        {pixelLigado ? (
          <>
            <p>
              Com o seu ok no aviso de cookies, a loja usa o Pixel da Meta para saber se um anúncio
              trouxe visitas e compras. Não mandamos o seu nome, e-mail ou telefone para a Meta. Sem
              o ok, nada da Meta é carregado.
            </p>
            {escolha && (
              <button
                type="button"
                onClick={esquecerConsentimento}
                className="mt-3 min-h-[44px] text-alo-gold underline underline-offset-2"
              >
                Você {escolha === "aceito" ? "aceitou" : "recusou"} os cookies. Mudar minha escolha
              </button>
            )}
          </>
        ) : (
          "A loja não usa cookies de propaganda — só o necessário para a página funcionar."
        )}
      </Bloco>

      <p className="mt-8 text-[12px] text-alo-muted">Atualizado em 16 de novembro de 2026.</p>
    </div>
  );
}

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <TituloSecao>{titulo}</TituloSecao>
      <div className="mt-2 text-[15px] leading-relaxed text-alo-muted">{children}</div>
    </section>
  );
}
