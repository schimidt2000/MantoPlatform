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
}

/** Corpo da chave `nota` nas portas da venda. */
export interface NotaInput {
  tomador_doc: string;
  iss_retido: boolean;
  municipio: string;
  referencia: string;
  observacoes: string;
}

/** Os campos que o servidor aponta num 400 (`fields`). */
export type CampoDaNota = "nota_tomador_doc" | "nota_municipio" | "nota_observacoes";
export type ErrosDaNota = Partial<Record<CampoDaNota, string>>;

export const OBSERVACOES_MAX = 1000;

export const DADOS_DA_NOTA_VAZIOS: DadosDaNota = {
  tomador_doc: "",
  iss_retido: false,
  municipio: "",
  referencia: "",
  observacoes: "",
};

/** Hidrata a tela a partir do detalhe do evento. */
export function dadosDoEvento(nota?: DadosDaNotaDoEvento | null): DadosDaNota {
  if (!nota) return DADOS_DA_NOTA_VAZIOS;
  return {
    tomador_doc: formatarDoc(nota.tomador_doc),
    iss_retido: nota.iss_retido,
    municipio: nota.municipio ?? "",
    referencia: nota.referencia ?? "",
    observacoes: nota.observacoes ?? "",
  };
}

/** O corpo da chave `nota`. O município só vai com ISS retido (sem ele, o servidor apaga). */
export function notaInput(dados: DadosDaNota): NotaInput {
  return {
    tomador_doc: dados.tomador_doc.trim(),
    iss_retido: dados.iss_retido,
    municipio: dados.iss_retido ? dados.municipio.trim() : "",
    referencia: dados.referencia.trim(),
    observacoes: dados.observacoes.trim(),
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
