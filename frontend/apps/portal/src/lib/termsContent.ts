/**
 * Texto do Termo de Consentimento do Portal do Artista.
 *
 * Transcrição fiel de `app/templates/portal/terms.html` — o mesmo termo que os talentos já
 * aceitaram na versão Jinja, para que o aceite registrado em `Talent.terms_accepted_at` continue
 * se referindo ao MESMO documento antes e depois da migração. Não altere o conteúdo sem decisão
 * jurídica: mudar o texto invalida a equivalência dos aceites antigos.
 */

export interface TermsSection {
  title: string;
  paragraphs?: string[];
  bullets?: string[];
}

export const TERMS_TITLE = "TERMO DE CONSENTIMENTO, RESPONSABILIDADE E USO DE IMAGEM";

export const TERMS_SUBTITLE = "MANTO PRODUÇÕES";

export const TERMS_PREAMBLE =
  "Pelo presente instrumento, de um lado Manto Produções, doravante denominada CONTRATANTE, " +
  "e de outro lado o(a) artista abaixo identificado(a), doravante denominado(a) CONTRATADO(A), " +
  "firmam o presente termo mediante as condições abaixo:";

export const TERMS_SECTIONS: TermsSection[] = [
  {
    title: "1. Objeto",
    paragraphs: [
      "O presente termo tem como objetivo formalizar o consentimento do(a) CONTRATADO(A) para " +
        "participação em eventos, apresentações, ativações e demais serviços realizados pela " +
        "CONTRATANTE.",
    ],
  },
  {
    title: "2. Consentimento para Prestação de Serviços",
    paragraphs: [
      "O(a) CONTRATADO(A) declara estar ciente das características do trabalho artístico " +
        "envolvido, incluindo apresentações com público, interação, uso de figurinos, " +
        "caracterização e possíveis ensaios ou orientações prévias.",
    ],
  },
  {
    title: "3. Responsabilidade e Compromisso",
    paragraphs: ["O(a) CONTRATADO(A) declara que:"],
    bullets: [
      "Aceitará apenas os compromissos para os quais tenha disponibilidade real",
      "Uma vez confirmado um trabalho, compromete-se a cumpri-lo integralmente, respeitando " +
        "horários, orientações e conduta profissional",
      "O não comparecimento ou descumprimento injustificado poderá impactar futuras convocações " +
        "e parcerias com a CONTRATANTE",
    ],
  },
  {
    title: "4. Conduta Profissional",
    paragraphs: ["O(a) CONTRATADO(A) compromete-se a:"],
    bullets: [
      "Manter postura profissional, respeitosa e adequada durante todo o evento",
      "Seguir orientações da equipe da CONTRATANTE",
      "Zelar pelos figurinos, acessórios e materiais fornecidos",
    ],
  },
  {
    title: "5. Pagamento",
    paragraphs: ["Fica acordado que:"],
    bullets: [
      "O pagamento pelos serviços prestados será realizado em até 3 (três) dias úteis após a " +
        "realização do evento",
      "O pagamento será feito por meio previamente acordado entre as partes",
    ],
  },
  {
    title: "6. Uso de Imagem, Voz e Conteúdo",
    paragraphs: [
      "O(a) CONTRATADO(A) autoriza, de forma gratuita, irrevogável e por prazo indeterminado, a " +
        "utilização de:",
    ],
    bullets: [
      "Imagem (fotos e vídeos)",
      "Voz e áudio",
      "Nome artístico ou imagem caracterizada",
    ],
  },
  {
    title: "",
    paragraphs: [
      "captados durante ensaios, eventos ou atividades relacionadas à CONTRATANTE.",
      "A autorização inclui o uso para quaisquer finalidades, incluindo, mas não se limitando a:",
    ],
    bullets: [
      "Divulgação em redes sociais",
      "Materiais publicitários e promocionais",
      "Portfólio e apresentações comerciais",
      "Campanhas digitais e institucionais",
    ],
  },
  {
    title: "7. Natureza da Relação",
    paragraphs: [
      "O presente termo não estabelece vínculo empregatício entre as partes, tratando-se de " +
        "prestação de serviço eventual/autônoma.",
    ],
  },
  {
    title: "8. Disposições Gerais",
    bullets: [
      "Este termo entra em vigor na data de sua assinatura",
      "O descumprimento das cláusulas poderá resultar na interrupção da parceria",
    ],
  },
  {
    title: "9. Declaração Final",
    paragraphs: [
      "O(a) CONTRATADO(A) declara que leu, compreendeu e concorda com todos os termos acima, " +
        "prestando seu consentimento de forma livre e esclarecida.",
    ],
  },
];

export const TERMS_CONSENT_LABEL =
  "Li e concordo com todos os termos acima, prestando meu consentimento de forma livre e " +
  "esclarecida.";
