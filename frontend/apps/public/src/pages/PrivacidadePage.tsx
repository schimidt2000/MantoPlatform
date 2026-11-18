import { useEffect, type ReactNode } from "react";
import { whatsappLink } from "../lib/lojaTema";

/**
 * Política de privacidade do atendimento (feature 354): as conversas pelo WhatsApp e pelo Direct
 * do Instagram e o que nasce delas — ficha, orçamento, contrato e evento.
 *
 * O endereço (`/privacidade`, superfície de raiz) está gravado no cadastro do app "Manto
 * Plataforma" na Meta, que só recebe mensagem de verdade com a política publicada: não renomear.
 *
 * O texto diz o que o sistema faz HOJE. Mudou uma regra? Confira antes de publicar:
 * - o que a conversa guarda: `Conversa`, mensagens, mídias e `ConversaAnuncio` (`app/models.py`);
 * - a ficha: `Client` (nome, telefone, e-mail, CPF/CNPJ, endereço);
 * - quem vê: `pode_conversas` (`app/conversas/acesso.py`, Comercial e Superadmin);
 * - o apagado no Instagram que some do sistema: `instagram_ops._apagar`;
 * - não há prazo automático de exclusão nem botão para excluir a pedido (dívida no `docs/05`).
 * A loja de conversas tem o aviso próprio (`PrivacidadeLojaPage`, feature 344).
 */
export function PrivacidadePage() {
  useEffect(() => {
    const tituloAnterior = document.title;
    document.title = "Política de privacidade · Manto Produções";
    return () => {
      document.title = tituloAnterior;
    };
  }, []);

  return (
    <div className="min-h-screen bg-bg">
      <div className="mx-auto max-w-lg px-4 pb-12 pt-10">
        <p className="text-[13px] uppercase tracking-wide text-muted">Manto Produções</p>
        <h1 className="mt-2 font-display text-[30px] leading-tight text-accent-dark">
          Política de privacidade
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-muted">
          Esta política vale para o nosso atendimento: as conversas pelo WhatsApp e pelo Direct do
          Instagram e tudo o que nasce delas — o orçamento, o contrato e o seu evento. Aqui está, sem
          letra miúda, o que a gente faz com os seus dados.
        </p>

        <Bloco titulo="Quem cuida dos seus dados">
          A Manto Produções. Qualquer pedido sobre os seus dados é pelo{" "}
          <LinkWhatsapp>nosso WhatsApp</LinkWhatsapp>.
        </Bloco>

        <Bloco titulo="O que guardamos e para quê">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">A conversa</strong> — o nome do seu perfil, o seu
              telefone (no WhatsApp) ou o seu @ (no Instagram), as mensagens, fotos, áudios e
              arquivos trocados com a gente. Servem para te atender, montar o orçamento e acompanhar
              o seu evento.
            </li>
            <li>
              <strong className="text-ink">De onde você veio</strong> — se você chegou por um
              anúncio ou por uma publicação nossa no Facebook ou no Instagram, guardamos qual foi.
              Assim a gente sabe quais anúncios funcionam.
            </li>
            <li>
              <strong className="text-ink">Os dados do contrato</strong> — nome, telefone, e-mail,
              CPF ou CNPJ e endereço, quando você nos passa (por exemplo, no formulário de
              pré-contrato). Servem para o orçamento, o contrato, a nota fiscal e o dia da festa.
            </li>
            <li>
              <strong className="text-ink">Anotações da equipe</strong> — quem te atende pode deixar
              anotações internas na conversa para organizar o atendimento.
            </li>
          </ul>
        </Bloco>

        <Bloco titulo="Quem vê">
          Só a nossa equipe comercial e a administração da Manto, com login e senha. Os avisos de
          mensagem nova que chegam ao celular da equipe vão cifrados.
        </Bloco>

        <Bloco titulo="Com quem dividimos">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <strong className="text-ink">Meta</strong> (WhatsApp, Instagram e Facebook): é por
              onde a conversa acontece, então as mensagens passam por lá e seguem também as regras
              da Meta.
            </li>
            <li>
              <strong className="text-ink">Render</strong>, a empresa que hospeda o nosso sistema,
              com servidores nos Estados Unidos.
            </li>
            <li>
              <strong className="text-ink">Google</strong>, onde fica a agenda da equipe com os
              eventos.
            </li>
            <li>
              <strong className="text-ink">ClickSign</strong>, para você assinar o contrato pela
              internet.
            </li>
            <li>
              <strong className="text-ink">Quem processa o pagamento</strong> (o banco ou o meio de
              pagamento que você escolher).
            </li>
          </ul>
          <p className="mt-2">Não vendemos nem emprestamos os seus dados.</p>
        </Bloco>

        <Bloco titulo="Por quanto tempo">
          Guardamos o histórico da conversa enquanto ele ajuda a te atender — muita gente volta para
          a festa do ano seguinte. Os dados do contrato e da nota fiscal ficam pelo tempo que a lei
          pede. No Instagram, quando você apaga uma mensagem, ela some também do nosso sistema.
        </Bloco>

        <Bloco titulo="Seus direitos">
          Você pode pedir para ver, corrigir ou apagar os seus dados, saber com quem foram divididos e
          parar de receber mensagens nossas a qualquer momento. É só falar com a gente no{" "}
          <LinkWhatsapp>WhatsApp</LinkWhatsapp>. O que a lei nos obriga a manter (como o contrato e a
          nota fiscal) fica guardado só pelo prazo dela.
        </Bloco>

        <Bloco titulo="Loja de conversas">
          Comprou uma chamada ou um vídeo na nossa loja de conversas? Ela tem um{" "}
          <a
            href="/catalogo/v/privacidade"
            className="text-accent underline underline-offset-2"
          >
            aviso de privacidade próprio
          </a>
          .
        </Bloco>

        <p className="mt-8 text-[12px] text-muted">Atualizado em 17 de novembro de 2026.</p>
      </div>
    </div>
  );
}

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="font-display text-[19px] text-ink">{titulo}</h2>
      <div className="mt-2 text-[15px] leading-relaxed text-muted">{children}</div>
    </section>
  );
}

function LinkWhatsapp({ children }: { children: ReactNode }) {
  return (
    <a
      href={whatsappLink()}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent underline underline-offset-2"
    >
      {children}
    </a>
  );
}
