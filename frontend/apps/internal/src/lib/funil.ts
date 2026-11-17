import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { Canal } from "./conversas";

/**
 * O funil das conversas (feature 335): as conversas cujo primeiro contato caiu no período e até
 * onde cada uma chegou. Cada etapa conta quem chegou nela ou além (o funil nunca cresce).
 */

export type EtapaDoFunil =
  "chegou" | "orcamento" | "formulario" | "evento" | "pagou" | "avaliou";
export type DivisaoDoFunil = "vendedor" | "campanha" | "canal";

export interface EtapaContada {
  chave: EtapaDoFunil;
  rotulo: string;
  quantidade: number;
  /** Porcentagem sobre "Chegou" (uma casa); `null` sem base. */
  sobre_chegou: number | null;
  /** Porcentagem sobre a etapa anterior; `null` na primeira ou sem base. */
  passagem: number | null;
}

export interface GrupoDoFunil {
  chave: string;
  rotulo: string;
  quantidades: Record<EtapaDoFunil, number>;
  /** Evento fechado ÷ chegou, em porcentagem. */
  conversao: number | null;
  /** Feature 349 (opcionais: backend velho não manda). */
  qualificadas?: number;
  perdidas?: number;
  mediana_minutos?: number | null;
  ate_15_min?: number | null;
}

/** Feature 349: o tempo da primeira resposta da coorte; a resposta sem autor (celular) contada à parte. */
export interface PrimeiraRespostaDoFunil {
  respondidas: number;
  sem_resposta: number;
  sem_autor: number;
  mediana_minutos: number | null;
  /** % das respondidas em até 15 min. */
  ate_15_min: number | null;
}

export interface MotivoContado {
  codigo: string;
  rotulo: string;
  quantidade: number;
}

export interface OpcaoDeCampanha {
  valor: string;
  rotulo: string;
  quantidade: number;
}

export interface Funil {
  periodo: { inicio: string; fim: string };
  total: number;
  etapas: EtapaContada[];
  dividir: DivisaoDoFunil;
  grupos: GrupoDoFunil[];
  campanhas: OpcaoDeCampanha[];
  primeira_resposta?: PrimeiraRespostaDoFunil;
  qualificadas?: number;
  perdidas?: number;
  motivos_de_perda?: MotivoContado[];
}

export interface ConversaParada {
  id: number;
  nome: string;
  canal: Canal;
  vendedor: string | null;
  primeiro_contato: string;
  campanha: string;
  /** Feature 349 (opcionais). */
  perdida?: { motivo: string; rotulo: string } | null;
  qualificada?: boolean;
  primeira_resposta_minutos?: number | null;
  primeira_resposta_sem_autor?: boolean;
  primeira_resposta_pendente?: boolean;
  lembrete_em?: string | null;
}

export interface Parados {
  etapa: EtapaDoFunil;
  rotulo: string;
  /** O número inteiro; a lista traz até 200. */
  total: number;
  conversas: ConversaParada[];
}

export interface FiltrosDoFunil {
  inicio: string;
  fim: string;
  canal: Canal | null;
  campanha: string | null;
}

function parametros(
  filtros: FiltrosDoFunil,
  extra: Record<string, string>,
): string {
  const params = new URLSearchParams({
    inicio: filtros.inicio,
    fim: filtros.fim,
    ...extra,
  });
  if (filtros.canal) params.set("canal", filtros.canal);
  if (filtros.campanha) params.set("campanha", filtros.campanha);
  return params.toString();
}

export function useFunil(filtros: FiltrosDoFunil, dividir: DivisaoDoFunil) {
  const query = parametros(filtros, { dividir });
  return useQuery<Funil>({
    queryKey: ["conversas-funil", query],
    queryFn: () => apiFetch<Funil>(`/api/conversas/funil?${query}`),
    // Trocar o filtro não pisca a tela: o funil anterior fica até o novo chegar.
    placeholderData: keepPreviousData,
  });
}

export function useParados(
  filtros: FiltrosDoFunil,
  etapa: EtapaDoFunil | null,
) {
  const query = parametros(filtros, etapa ? { etapa } : {});
  return useQuery<Parados>({
    queryKey: ["conversas-funil-parados", query],
    queryFn: () => apiFetch<Parados>(`/api/conversas/funil/parados?${query}`),
    enabled: etapa !== null,
  });
}

/** A data de hoje em São Paulo, `AAAA-MM-DD` (o período do funil é de datas de São Paulo). */
export function hojeEmSaoPaulo(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
  }).format(new Date());
}

function deslocar(iso: string, dias: number): string {
  const data = new Date(`${iso}T12:00:00Z`);
  data.setUTCDate(data.getUTCDate() + dias);
  return data.toISOString().slice(0, 10);
}

export type PresetDoPeriodo =
  "mes_atual" | "mes_passado" | "30_dias" | "90_dias" | "personalizado";

export const PRESETS_DO_PERIODO: { valor: PresetDoPeriodo; rotulo: string }[] =
  [
    { valor: "mes_atual", rotulo: "Mês atual" },
    { valor: "mes_passado", rotulo: "Mês passado" },
    { valor: "30_dias", rotulo: "Últimos 30 dias" },
    { valor: "90_dias", rotulo: "Últimos 90 dias" },
    { valor: "personalizado", rotulo: "Personalizado" },
  ];

/** As datas do preset (o personalizado devolve `null`: as datas vêm dos campos). */
export function datasDoPreset(
  preset: PresetDoPeriodo,
): { inicio: string; fim: string } | null {
  const hoje = hojeEmSaoPaulo();
  const inicioDoMes = `${hoje.slice(0, 8)}01`;
  switch (preset) {
    case "mes_atual":
      return { inicio: inicioDoMes, fim: hoje };
    case "mes_passado": {
      const fim = deslocar(inicioDoMes, -1);
      return { inicio: `${fim.slice(0, 8)}01`, fim };
    }
    case "30_dias":
      return { inicio: deslocar(hoje, -29), fim: hoje };
    case "90_dias":
      return { inicio: deslocar(hoje, -89), fim: hoje };
    default:
      return null;
  }
}
