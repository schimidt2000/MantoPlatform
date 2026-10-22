import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { Severidade } from "./homeListas";

/**
 * Contratos da ClickSign ligados à venda (feature 317).
 *
 * O servidor decide tudo — situação, cor, se dá para cobrar e por quê não. A tela só mostra e
 * chama as quatro ações: cobrar (registra quem copiou a mensagem), ligar, desligar e descartar.
 * Toda chave aqui é opcional nos tipos de quem a recebe (`EventoDetalhe.contrato?`,
 * `ComercialSummary.contratos?`): o bundle em cache não conhece estes campos na janela do deploy.
 */

export type SituacaoContrato =
  | "assinado"
  | "assinado_manual"
  | "aguardando"
  | "vencido"
  | "recusado"
  | "sem_contrato";

export interface DocumentoClickSign {
  id: number;
  nome: string;
  status: string;
  prazo: string | null;
  assinado_em: string | null;
  canal: string | null;
  vinculo_origem: string | null;
}

export interface SugestaoDeVenda {
  event_id: number;
  titulo: string;
  data_evento: string | null;
  cliente: string | null;
  mesmo_telefone: boolean;
}

export interface ContratoAConferir {
  documento_id: number;
  nome: string;
  data_lida: string | null;
  telefone_lido: string | null;
  motivo: string | null;
  motivo_texto: string | null;
  status: string;
  criado_em: string | null;
  sugestoes: SugestaoDeVenda[];
}

export interface UltimaCobranca {
  por: string;
  em: string;
}

/** O bloco `contrato` do detalhe do evento (contracts/api.md). */
export interface ContratoDaVenda {
  integracao_ligada: boolean;
  situacao: SituacaoContrato;
  rotulo: string;
  cor: Severidade | "verde";
  escopo: "evento" | "grupo_principal" | "grupo_outro";
  documento: DocumentoClickSign | null;
  outros_documentos: DocumentoClickSign[];
  pode_cobrar: boolean;
  motivo_bloqueio: string | null;
  ultima_cobranca: UltimaCobranca | null;
  pode_conferir: boolean;
  a_conferir: ContratoAConferir[];
}

/** Uma linha do painel "Contratos" da Home. */
export interface LinhaContrato {
  event_id: number;
  titulo: string;
  cliente: string | null;
  data_evento: string;
  dias_ate_o_evento: number;
  situacao: SituacaoContrato;
  rotulo: string;
  severidade: Severidade;
  selo: string;
  documento_id: number | null;
  prazo: string | null;
  canal: string | null;
  ultima_cobranca: UltimaCobranca | null;
  mensagem: { characters: string; date_line: string; location: string } | null;
}

export interface ContratosResumo {
  integracao_ligada: boolean;
  para_cobrar: LinhaContrato[];
  vencidos: LinhaContrato[];
  sem_contrato: LinhaContrato[];
  a_conferir: ContratoAConferir[];
  ja_aconteceu: LinhaContrato[];
  resumo: { por_cor: Record<Severidade, number>; para_agir: number };
  pode_cobrar: boolean;
}

/** "26/10" a partir do prazo ISO da ClickSign (horário de SP, sem fuso). */
export function prazoCurto(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const [data] = iso.split("T");
  const [, mes, dia] = data.split("-");
  return dia && mes ? `${dia}/${mes}` : null;
}

/** Invalida o que mostra a situação do contrato: o evento aberto e a Home. */
function useInvalidarContrato(eventId?: number) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["contratos-a-conferir"] });
    if (eventId !== undefined) void queryClient.invalidateQueries({ queryKey: ["event", eventId] });
    else void queryClient.invalidateQueries({ queryKey: ["event"] });
  };
}

/** Registra o "Cobrar contrato" (a mensagem já foi copiada pela tela). */
export function useCobrarContrato(eventId?: number) {
  const invalidar = useInvalidarContrato(eventId);
  return useMutation<{ ultima_cobranca: UltimaCobranca }, Error, number>({
    mutationFn: (documentoId) =>
      apiFetch(`/api/contratos/${documentoId}/cobranca`, { method: "POST" }),
    onSuccess: invalidar,
  });
}

/** Liga um contrato a conferir à venda do evento informado ("é esse mesmo"). */
export function useLigarContrato(eventId?: number) {
  const invalidar = useInvalidarContrato(eventId);
  return useMutation<unknown, Error, { documentoId: number; eventId: number }>({
    mutationFn: ({ documentoId, eventId: alvo }) =>
      apiFetch(`/api/contratos/${documentoId}/ligar`, {
        method: "POST",
        body: JSON.stringify({ event_id: alvo }),
      }),
    onSettled: invalidar,
  });
}

/** Desliga o contrato da venda; o sistema não religa sozinho nesta venda. */
export function useDesligarContrato(eventId?: number) {
  const invalidar = useInvalidarContrato(eventId);
  return useMutation<unknown, Error, number>({
    mutationFn: (documentoId) =>
      apiFetch(`/api/contratos/${documentoId}/desligar`, { method: "POST" }),
    onSettled: invalidar,
  });
}

/** "Não é de nenhuma venda": tira o contrato da conferência para sempre. */
export function useDescartarContrato(eventId?: number) {
  const invalidar = useInvalidarContrato(eventId);
  return useMutation<unknown, Error, number>({
    mutationFn: (documentoId) =>
      apiFetch(`/api/contratos/${documentoId}/descartar`, { method: "POST" }),
    onSettled: invalidar,
  });
}

/** Lista completa de contratos a conferir (o diálogo "Ligar contrato da ClickSign" do evento). */
export function useContratosAConferir(ativo: boolean) {
  return useQuery<{ integracao_ligada: boolean; itens: ContratoAConferir[] }>({
    queryKey: ["contratos-a-conferir"],
    queryFn: () => apiFetch("/api/contratos/a-conferir"),
    enabled: ativo,
  });
}
