/**
 * Copy de marca da Loja de Interações Virtuais — a estação atual (feature 304: Natal).
 *
 * A loja é sazonal e o dono escolheu um tema para ela inteira, não por campanha: no Natal tudo em
 * `alo.*` fala do Papai Noel; quando as princesas entrarem, troca-se ESTE arquivo e a paleta
 * `alo.*` do `tailwind.config.ts`. As páginas não carregam texto de estação nenhum — só o que é
 * mecânica da loja (rótulos de campo, estados de pagamento).
 *
 * O que é de cada campanha (título, apresentação, termos, FAQ específico, preços) continua na tela
 * de gestão. Aqui mora o que vale para a loja toda.
 *
 * Três regras de redação que valem para qualquer estação:
 * - **não é só para criança** (feature 341): a maioria compra para a criança da casa, mas a avó, o
 *   padrinho e um adulto também recebem. O sujeito é "quem vai receber" / "quem você escolher"; a
 *   criança aparece como o caso comum ("se for uma criança…"), nunca como o único;
 * - **nunca presumir menina ou menino** (a 205 dizia "o personagem preferido dela" e deixava fora
 *   metade das famílias);
 * - **cada pedido é de um formato só** — chamada ao vivo OU vídeo gravado (decisão do dono).
 */

/** WhatsApp da empresa — o mesmo dos formulários públicos (`DEFAULT_WHATSAPP_NUMBER`). */
export const WHATSAPP_LOJA = "5511970570577";

export const whatsappLink = (numero: string = WHATSAPP_LOJA) =>
  `https://wa.me/${numero.replace(/\D/g, "")}`;

/** `<title>` das páginas da loja (a prévia de link vem do servidor, `frontend/server.js`). */
export const TITULO_LOJA = "Uma chamada com o Papai Noel · Manto Produções";

export const HERO = {
  sobretitulo: "Manto Produções apresenta",
  linha1: "Uma chamada com o",
  destaque: "Papai Noel",
  subtitulo: "Um encontro mágico, sem sair de casa.",
  texto:
    "O Papai Noel liga por vídeo para quem você quer surpreender — a criança da casa, a vovó, o " +
    "padrinho —, chama pelo nome e já chega sabendo dos pedidos, da família e de como foi o ano. " +
    "É só atender.",
  cta: "Ver horários",
};

/** Os dois formatos da loja. Os nomes batem com os botões da página da campanha. */
export const FORMATOS = {
  ao_vivo: {
    nome: "Chamada ao vivo",
    detalhe: "10 minutos · dia e hora marcados",
    texto:
      "O Papai Noel liga pelo Google Meet no horário que você escolher, conversa e relembra o ano. " +
      "Se for uma criança, ela pode mostrar a cartinha para ele ler na hora.",
  },
  gravado: {
    nome: "Vídeo do Papai Noel",
    detalhe: "Recado gravado · sem hora marcada",
    texto:
      "Um vídeo gravado só para quem você escolher, com o nome da pessoa e o recado que você " +
      "pedir. Chega pronto para guardar, reassistir e mostrar para a família inteira.",
  },
} as const;

export const AVISO_UM_FORMATO =
  "Cada reserva é de um formato: ou a chamada ao vivo, ou o vídeo gravado.";

export const PASSOS = [
  {
    titulo: "Escolha o formato",
    texto:
      "Chamada ao vivo, com dia e hora marcados, ou um vídeo gravado só para quem você escolher.",
  },
  {
    titulo: "Conte tudo para o Papai Noel",
    texto:
      "Nome, idade, o que pediu de presente, quem são os irmãos, os netos ou o cachorro. Quanto " +
      "mais você contar, mais mágico fica.",
  },
  {
    titulo: "No dia, é só atender",
    texto:
      "Mandamos por e-mail a página do seu pedido. É nela que aparece o link da chamada — ou o " +
      "vídeo, quando ficar pronto.",
  },
];

/** Perguntas sobre a loja. As específicas de cada campanha ficam na tela de gestão. */
export const FAQ_LOJA = [
  {
    pergunta: "Como funciona a chamada?",
    resposta:
      "É uma videochamada pelo Google Meet. No horário marcado, você abre o link que aparece na " +
      "página do seu pedido e o Papai Noel já está esperando. Não precisa instalar nada nem criar " +
      "conta.",
  },
  {
    pergunta: "É só para criança?",
    resposta:
      "Não! A maioria das chamadas é para crianças, mas o Papai Noel também liga para a vovó, o " +
      "vovô, os pais, os padrinhos — para qualquer pessoa que você queira emocionar neste Natal. " +
      "Conte no formulário quem é e o que ele precisa saber.",
  },
  {
    pergunta: "Quanto tempo dura?",
    resposta:
      "Dez minutos ao vivo, só para quem vai receber a chamada. Dá tempo de conversar, contar " +
      "como foi o ano, mostrar a cartinha e até cantar uma música de Natal.",
  },
  {
    pergunta: "A criança pode mostrar a cartinha?",
    resposta:
      "Pode, e é um dos momentos mais bonitos. Deixe a cartinha por perto: a criança mostra na " +
      "câmera e o Papai Noel lê junto. Se você contar no formulário o que está escrito, ele já " +
      "chega sabendo.",
  },
  {
    pergunta: "O Papai Noel sabe mesmo o nome de quem vai atender?",
    resposta:
      "Sabe. Na reserva você conta o nome, a idade e o que for especial — o que pediu de presente, " +
      "o nome dos irmãos ou dos netos, do bichinho, uma conquista do ano. Ele chega sabendo de tudo.",
  },
  {
    pergunta: "E se a pessoa ficar com vergonha?",
    resposta:
      "Acontece muito, com criança e com adulto, e é aí que o Papai Noel trabalha: puxa conversa, " +
      "pergunta, brinca. Quase sempre a timidez passa antes do primeiro minuto.",
  },
  {
    pergunta: "Posso gravar a chamada?",
    resposta:
      "Pode, e a gente recomenda — de preferência com um segundo celular filmando o rosto de quem " +
      "está conversando com o Papai Noel. A reação vale mais do que a tela da chamada.",
  },
  {
    pergunta: "Como é o vídeo do Papai Noel?",
    resposta:
      "O Papai Noel grava um recado só para quem você escolher, com o nome da pessoa e o que você " +
      "pedir no formulário. Não é ao vivo, então não tem hora marcada: você recebe um aviso por " +
      "e-mail e assiste na página do pedido. Costuma ser a saída quando os horários acabam.",
  },
  {
    pergunta: "Posso pedir a chamada e o vídeo juntos?",
    resposta: `${AVISO_UM_FORMATO} Escolha o que faz mais sentido para quem vai receber.`,
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
      "Fale com a gente pelo WhatsApp o quanto antes. As regras de remarcação ficam escritas na " +
      "página da reserva, logo abaixo do botão de pagar — vale a pena ler antes de fechar.",
  },
];

/** Textos da página da campanha que dependem da estação. */
export const CAMPANHA = {
  presenteTitulo: "Quer um presente do Papai Noel?",
  presenteTexto: "Uma peça impressa em 3D, entregue no seu endereço.",
  fichaTitulo: "Conte para o Papai Noel",
  dicas: {
    ao_vivo: {
      rotulo: "O que o Papai Noel precisa saber?",
      exemplo:
        "Ex.: pediu uma bicicleta na cartinha, a irmã se chama Bia, o cachorro é o Thor. Para a " +
        "vovó: os netos são Ana e Leo, e ela faz o melhor panetone da família.",
    },
    gravado: {
      rotulo: "O que o Papai Noel deve dizer no vídeo?",
      exemplo:
        "Ex.: dar parabéns por ter tirado a fralda, lembrar de escovar os dentes. Para um adulto: " +
        "agradecer pelo ano e mandar um abraço dos netos.",
    },
  },
};

/** Dicas para a família depois do pagamento da chamada ao vivo. */
export const DICAS_DO_DIA = [
  "Abra o link alguns minutos antes, para testar câmera e som.",
  "Se for uma criança, deixe a cartinha por perto para ela mostrar ao Papai Noel.",
  "Um segundo celular filmando o rosto de quem está na chamada guarda a melhor parte.",
];

export const RODAPE = "Manto Produções · personagens vivos desde sempre";
