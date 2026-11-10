import { useClientDetail } from "./clientes";

/**
 * A nota pedida (feature 323): os dados que a emissão precisa, que a vendedora informa ao ligar
 * "Precisa de nota fiscal". São da VENDA — o cliente pede uma vez — e vão no corpo das três portas
 * da venda como a chave `nota`. Contrato: `specs/323-nota-pedida-ao-superadmin/contracts/api.md`.
 */

/** Os dados como a tela os edita (texto vazio = não informado). */
export interface DadosDaNota {
  tomador_doc: string;
  iss_retido: boolean;
  municipio: string;
  referencia: string;
  observacoes: string;
  /** Feature 342: para onde a nota é enviada (vazio = o e-mail do cadastro). */
  email: string;
}

/** O que a cliente respondeu sobre a nota no formulário público (feature 342). */
export interface NotaDoFormulario {
  response_id: number;
  /** Só dígitos. */
  doc: string | null;
  email: string | null;
  /** O texto da resposta: "Sim", "Não", "Não sei"; nulo quando a pergunta não foi feita (CPF). */
  iss: string | null;
  referencia: string | null;
}

/** `venda.nota` do detalhe do evento — opcional: servidor antigo não manda. */
export interface DadosDaNotaDoEvento {
  tomador_doc: string | null;
  /** O CNPJ (ou CPF) do cadastro do cliente contratante — vale quando o campo fica em branco. */
  doc_do_cliente: string | null;
  iss_retido: boolean;
  municipio: string | null;
  referencia: string | null;
  observacoes: string | null;
  /** Feature 342 — chaves novas, opcionais: servidor de antes do deploy não manda. */
  email?: string | null;
  /** A cidade tirada do formulário ou do endereço do evento; só vira dado quando alguém salva. */
  municipio_sugerido?: string | null;
  do_formulario?: NotaDoFormulario | null;
}

/** Corpo da chave `nota` nas portas da venda. */
export interface NotaInput {
  tomador_doc: string;
  iss_retido: boolean;
  municipio: string;
  referencia: string;
  observacoes: string;
  email: string;
}

/** Os campos que o servidor aponta num 400 (`fields`). */
export type CampoDaNota =
  | "nota_tomador_doc"
  | "nota_municipio"
  | "nota_observacoes"
  | "nota_email";
export type ErrosDaNota = Partial<Record<CampoDaNota, string>>;

export const OBSERVACOES_MAX = 1000;

export const DADOS_DA_NOTA_VAZIOS: DadosDaNota = {
  tomador_doc: "",
  iss_retido: false,
  municipio: "",
  referencia: "",
  observacoes: "",
  email: "",
};

/**
 * Hidrata a tela a partir do detalhe do evento. Sem município gravado, o campo abre com a sugestão
 * (feature 342): salvar o bloco é o que a confirma.
 */
export function dadosDoEvento(nota?: DadosDaNotaDoEvento | null): DadosDaNota {
  if (!nota) return DADOS_DA_NOTA_VAZIOS;
  return {
    tomador_doc: formatarDoc(nota.tomador_doc),
    iss_retido: nota.iss_retido,
    municipio: nota.municipio ?? nota.municipio_sugerido ?? "",
    referencia: nota.referencia ?? "",
    observacoes: nota.observacoes ?? "",
    email: nota.email ?? "",
  };
}

/** O corpo da chave `nota`. Desde a 342 o município vai sempre: é onde o ISS é devido. */
export function notaInput(dados: DadosDaNota): NotaInput {
  return {
    tomador_doc: dados.tomador_doc.trim(),
    iss_retido: dados.iss_retido,
    municipio: dados.municipio.trim(),
    referencia: dados.referencia.trim(),
    observacoes: dados.observacoes.trim(),
    email: dados.email.trim(),
  };
}

/** Máscara de CNPJ (00.000.000/0000-00) ou CPF (000.000.000-00); outro tamanho volta como veio. */
export function formatarDoc(doc: string | null | undefined): string {
  const d = (doc ?? "").replace(/\D/g, "");
  if (d.length === 14) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
  if (d.length === 11) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
  return doc ?? "";
}

/** Mesma regra do servidor: vazio, 11 dígitos (CPF) ou 14 (CNPJ). */
export function docValido(doc: string): boolean {
  const n = doc.replace(/\D/g, "").length;
  return n === 0 || n === 11 || n === 14;
}

const PESOS_CNPJ_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
const PESOS_CNPJ_2 = [6, ...PESOS_CNPJ_1];

/**
 * Feature 342: os dígitos verificadores, como `app/documentos.py`. Vazio e tamanho errado passam
 * aqui (o tamanho é de `docValido`, com a mensagem dele).
 */
export function digitosDoDocValidos(doc: string): boolean {
  const d = doc.replace(/\D/g, "");
  if (d.length !== 11 && d.length !== 14) return true;
  if (new Set(d).size === 1) return false;
  if (d.length === 11) {
    return [9, 10].every((posicao) => {
      let soma = 0;
      for (let i = 0; i < posicao; i += 1) soma += Number(d[i]) * (posicao + 1 - i);
      return ((soma * 10) % 11) % 10 === Number(d[posicao]);
    });
  }
  return [PESOS_CNPJ_1, PESOS_CNPJ_2].every((pesos, i) => {
    const resto = pesos.reduce((soma, peso, j) => soma + Number(d[j]) * peso, 0) % 11;
    return (resto < 2 ? 0 : 11 - resto) === Number(d[12 + i]);
  });
}

export const MENSAGEM_DOC_DIGITO = "CNPJ ou CPF inválido. Confira os números.";
export const MENSAGEM_DOC_INVALIDO = "Informe o CNPJ com 14 dígitos ou o CPF com 11.";
export const MENSAGEM_MUNICIPIO = "Informe o município onde o serviço é prestado.";

/** Uma linha do painel "Notas a emitir" da tela inicial do Superadmin (contracts §3). */
export interface NotaAEmitir {
  id: number;
  event_id: number;
  event_title: string;
  event_start_at: string | null;
  amount: number | null;
  issue_date: string | null;
  tomador: { nome: string | null; doc: string | null; email: string | null; endereco: string | null };
  iss_retido: boolean;
  municipio: string | null;
  /** Feature 342: a cidade pelo endereço, enquanto ninguém confirmou o município. */
  municipio_sugerido?: string | null;
  referencia: string | null;
  observacoes: string | null;
  /** Quem ligou o chip; nota antiga: o vendedor da venda. */
  pedida_por: string | null;
  /** Horário de São Paulo, sem fuso (recorte de string — nunca `new Date().toISOString()`). */
  pedida_em: string | null;
  vencimento: string | null;
  discriminacao: string;
  cancelado: boolean;
}

export interface NotasAEmitirSummary {
  itens: NotaAEmitir[];
}

/**
 * O CNPJ (senão o CPF) do cliente contratante escolhido no formulário — a sugestão do campo do
 * tomador. Lê a ficha de quem está na tela, não a gravada: trocar o contratante troca a sugestão.
 * Mesma escolha do servidor: o vínculo "Contratante"; sem ele, o primeiro cliente.
 */
export function useDocDoContratante(
  clientes: readonly { client_id: number; relation: string }[],
): string | null {
  const id =
    clientes.find((c) => c.relation === "Contratante")?.client_id ?? clientes[0]?.client_id;
  const ficha = useClientDetail(id ?? Number.NaN);
  if (id == null || !ficha.data) return null;
  return ficha.data.cnpj?.trim() || ficha.data.cpf?.trim() || null;
}
