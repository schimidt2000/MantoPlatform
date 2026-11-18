import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

/**
 * Cadastro de fornecedores dos gastos extras (feature 352).
 *
 * `gastos`, `total_aprovado` e `ultimo_gasto` só vêm para Financeiro/Superadmin (`can_manage`);
 * para os demais (e nas respostas de escrita) chegam `null`.
 */
export interface Fornecedor {
  id: number;
  nome: string;
  pix: string | null;
  categoria_padrao: string | null;
  ativo: boolean;
  gastos?: number | null;
  total_aprovado?: number | null;
  ultimo_gasto?: string | null;
}

export interface FornecedoresResponse {
  fornecedores: Fornecedor[];
  /** As categorias que podem ser padrão (sem devolução e multa, que nascem do cancelamento). */
  categorias: string[];
  can_manage: boolean;
}

export const FORNECEDORES_KEY = ["gastos-fornecedores"] as const;

/**
 * Mesma regra de `fornecedor_ops.normalizar_nome` no servidor: sem acento, minúsculas, pontuação
 * e espaço viram um espaço. Só decide o aviso "fornecedor novo" — quem liga de fato é o servidor.
 */
export function normalizarNomeFornecedor(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** "2026-11-06" → "06/11/2026", recortando a string (sem `Date`, que desloca o fuso). */
export function dataCurta(iso: string | null | undefined): string {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/** Lista uma vez por abertura da tela; o filtro das sugestões roda no navegador (sem requisição por tecla). */
export function useFornecedores() {
  return useQuery<FornecedoresResponse>({
    queryKey: FORNECEDORES_KEY,
    queryFn: () => apiFetch<FornecedoresResponse>("/api/gastos/fornecedores"),
    staleTime: 5 * 60 * 1000,
  });
}

export interface FornecedorInput {
  nome: string;
  pix: string;
  categoria_padrao: string;
}

/** Renomear e juntar reescrevem o nome dos gastos: a lista de gastos relê junto. */
function useInvalidarFornecedoresEGastos() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: FORNECEDORES_KEY });
    void queryClient.invalidateQueries({ queryKey: ["gastos-extras"] });
  };
}

export function useCadastrarFornecedor() {
  const invalidar = useInvalidarFornecedoresEGastos();
  return useMutation({
    mutationFn: (input: FornecedorInput) =>
      apiFetch<Fornecedor>("/api/gastos/fornecedores", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidar,
  });
}

export type AlterarFornecedorInput = { id: number } & Partial<FornecedorInput & { ativo: boolean }>;

export function useAlterarFornecedor() {
  const invalidar = useInvalidarFornecedoresEGastos();
  return useMutation({
    mutationFn: ({ id, ...input }: AlterarFornecedorInput) =>
      apiFetch<Fornecedor>(`/api/gastos/fornecedores/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidar,
  });
}

export function useJuntarFornecedores() {
  const invalidar = useInvalidarFornecedoresEGastos();
  return useMutation({
    mutationFn: ({ origemId, destinoId }: { origemId: number; destinoId: number }) =>
      apiFetch<{ fornecedor: Fornecedor; gastos_movidos: number }>(`/api/gastos/fornecedores/${origemId}/juntar`, {
        method: "POST",
        body: JSON.stringify({ destino_id: destinoId }),
      }),
    onSuccess: invalidar,
  });
}
