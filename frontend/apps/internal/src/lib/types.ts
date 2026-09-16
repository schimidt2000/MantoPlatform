/** Tipos dos recursos da API consumidos pela Fundação (data-model.md). */

import type { StatusCounts } from "./formulariosAdmin";
import type { Severidade } from "./homeListas";

/** Usuário autenticado — resposta de /api/auth/me e /api/auth/login. */
export interface AuthUser {
  id: number;
  name: string;
  email: string;
  roles: string[];
  /** SUPERADMIN efetivo (falso enquanto uma impersonação está ativa). */
  is_superadmin: boolean;
  /** SUPERADMIN real, independente de impersonação — controla o "Ver como". */
  is_real_superadmin: boolean;
  impersonating: string | null;
  /** Responsável EducaManto (feature 109) — afeta visibilidade de Pipeline/Comissões. */
  is_educamanto_responsavel: boolean;
}

/** Referência enxuta de um evento/cargo dentro do resumo do dashboard. */
export interface DashboardTaskRef {
  role_id: number | null;
  event_id: number;
  event_title: string;
  character_name: string | null;
  start_at: string | null;
}

/**
 * Escalação futura em que a pessoa ainda não confirmou (feature 231).
 *
 * `invite_status`: `"pending"` = convite enviado e sem resposta (cobrar a pessoa) · `null` =
 * convite **nunca enviado** (quem tem que agir é o casting). São ações diferentes, por isso o
 * painel separa as duas.
 */
export interface UnconfirmedInviteRef extends DashboardTaskRef {
  talent_id: number | null;
  talent_name: string;
  invite_status: string | null;
  /** Já com DDI — vira link de WhatsApp direto na linha. */
  whatsapp: string | null;
  /** Quantos lembretes automáticos já saíram para este convite (teto de 2). */
  reminder_count: number;
  reminder_at: string | null;
}

export interface CastingSummary {
  pending: DashboardTaskRef[];
  rejected_invites: DashboardTaskRef[];
  unconfirmed: UnconfirmedInviteRef[];
  total: number;
  done: number;
}

export interface FigurinoSummary {
  pending: DashboardTaskRef[];
  total: number;
  done: number;
}

export interface RecurringExpenseAlert {
  name: string;
  due_day: number;
  amount: number | null;
}

/** A marca "grupo de N eventos" (feature 299): o grupo é uma venda só, na linha do principal. */
export interface GrupoComercial {
  nome: string;
  /** Eventos não cancelados do grupo. */
  eventos: number;
}

/**
 * Uma cobrança (saldo em aberto) — feature 174, refeita na 299 (o grupo é uma venda só). As chaves
 * antigas continuam com o mesmo nome e tipo; as novas são **todas opcionais**, porque servidor e
 * site ficam alguns instantes em versões diferentes em todo deploy.
 */
export interface PendingPayment {
  event_id: number;
  event_title: string;
  start_at: string | null;
  sale: number;
  received: number;
  saldo: number;
  severity: "atrasado" | "vencido" | "urgent" | "warn" | "info";
  due_date: string | null;
  titulo?: string;
  /** Contratante > 1ª cliente; `null` → a tela mostra o título. */
  cliente?: string | null;
  /** Data do grupo (1º evento não cancelado e que não é compromisso interno). */
  data_evento?: string | null;
  vencimento?: string | null;
  vencimento_origem?: "data_combinada" | "parcela" | "politica" | null;
  /** Negativo = venceu. */
  dias_ate_vencimento?: number;
  sinal_pendente?: boolean;
  severidade?: Severidade;
  /** Pronto, em pt-BR ("Atrasado", "Vence hoje", "Vence em N dias", "Sinal pendente"). */
  selo?: string;
  /** "sem sinal" na linha vermelha com sinal pendente. */
  nota?: string | null;
  grupo_comercial?: GrupoComercial | null;
}

/** Contagem por cor de uma lista comercial e o `para_agir` (vermelho + amarelo). */
export interface ResumoPorCor {
  por_cor: Record<Severidade, number>;
  para_agir: number;
}

/** `comercial.cobrancas_resumo` (feature 299): o número do card e o dinheiro em aberto. */
export interface CobrancasResumo extends ResumoPorCor {
  /** Saldo de TODAS as linhas de Cobranças, inclusive as cinza. */
  total_em_aberto: number;
}

/** Uma linha de "Evento sem valor de venda" (feature 299). */
export interface LinhaSemValor {
  event_id: number;
  titulo: string;
  cliente: string | null;
  grupo_comercial: GrupoComercial | null;
  data_evento: string | null;
  /** 0 = hoje; negativo = já aconteceu. */
  dias_ate_o_evento: number;
  valor: number | null;
  /** Vazio ou zero → "a definir". */
  a_definir: boolean;
  /** Entre R$ 0,01 e R$ 0,99 → o valor com "(valor simbólico)". */
  valor_simbolico: boolean;
  recebido: number;
  severidade: Severidade;
}

/** `comercial.sem_valor` (feature 299): os dois grupos, na ordem do servidor. */
export interface SemValorSummary extends ResumoPorCor {
  a_acontecer: LinhaSemValor[];
  ja_aconteceu: LinhaSemValor[];
}

/**
 * Bloco `comercial` do `/api/dashboard` — contrato em
 * `specs/299-sem-valor-cobrancas/contracts/dashboard-comercial.md`.
 *
 * Nas listas novas, `undefined` é o servidor antigo (não desenha painel nem card) e `null` é a
 * lista que falhou (desenha o aviso com "Tentar de novo", nunca o "✓").
 */
export interface ComercialSummary {
  pending_payments: PendingPayment[];
  cobrancas_resumo?: CobrancasResumo | null;
  sem_valor?: SemValorSummary | null;
  /** Data de início (AAAA-MM-DD). */
  corte?: string | null;
  /** Papel efetivo edita a venda (senão a ação da linha "sem valor" é "Abrir"). */
  pode_editar_venda?: boolean;
}

/** Painel Performance (SUPERADMIN real, nunca durante impersonação) — feature 174. */
export interface PerformanceSummary {
  range: "7" | "30" | "custom";
  start: string | null;
  end: string | null;
  casting_total: number;
  casting_done: number;
  figurino_total: number;
  figurino_done: number;
  money_total: number;
}

/** Referência enxuta de um evento (sem cargo) no painel de Ensaio. */
export interface EnsaioEventRef {
  event_id: number;
  event_title: string;
  start_at: string | null;
}

/**
 * Painel da equipe de ensaio — as quatro listas restauradas da home Jinja (pós-206):
 * shows a agendar, agendados, ensaios órfãos e a vaga de presença sem talento.
 */
export interface EnsaioSummary {
  pending: EnsaioEventRef[];
  scheduled: (EnsaioEventRef & { ensaios: (string | null)[] })[];
  orphans: EnsaioEventRef[];
  pending_presence: DashboardTaskRef[];
}

/** Resumo do dashboard — resposta de /api/dashboard. Seções ausentes = sem permissão. */
/** Uma peça de figurino nos painéis da home (feature 225 / 225b). */
export interface MinhaPecaRef {
  id: number;
  title: string;
  status: string;
  status_label: string;
  /** `producao` (peça nova) ou `manutencao` (conserto/ajuste do que já existe). */
  kind: string;
  kind_label: string;
  /** True quando a peça não pode ir para evento até o conserto. */
  impede_uso: boolean;
  figurino_sheet_name: string | null;
  event_title: string | null;
  /** Prazo informado, ou a data do evento quando não houve prazo. */
  prazo: string | null;
  dias_para_prazo: number | null;
  is_late: boolean;
}

/** Painel pessoal "Minhas peças" — `null` quando a pessoa não é responsável por nada. */
export interface MinhasPecasSummary {
  pending: number;
  atrasados: number;
  items: MinhaPecaRef[];
}

/** Caixa de entrada do setor: pedidos abertos que ninguém assumiu (feature 225b). */
export interface OficinaFilaSummary {
  pending: number;
  impedem_uso: number;
  items: MinhaPecaRef[];
}

/** Um formulário dentro de uma linha da Home (a linha junta os do mesmo telefone). */
export interface FormularioDaLinha {
  id: number;
  tipo_rotulo?: string;
  data_informada?: string | null;
  chegou_em?: string | null;
  dias_desde_chegada?: number;
}

/** Evento da cliente a até 3 dias da data informada — "parece ser este evento, é?". */
export interface SugestaoDeEvento {
  event_id: number;
  titulo?: string;
  data?: string | null;
  dias_diferenca?: number;
}

/**
 * Uma linha de "Formulários sem evento na agenda" (feature 298). Tudo além do id é opcional:
 * servidor e site sobem separados e ficam ~1 min em versões diferentes em todo deploy.
 */
export interface LinhaFormulario {
  representante_id: number;
  chave?: string;
  cliente?: { id: number; nome: string } | null;
  nome_no_formulario?: string;
  tipo?: "comum" | "corporativo";
  tipo_rotulo?: string;
  data_informada?: string | null;
  /** Negativo quando a data informada já passou; `null` sem data. */
  dias_ate_a_data?: number | null;
  dias_desde_chegada?: number;
  grupo?: "a_chegar" | "ja_passou";
  severidade?: Severidade;
  data_suspeita?: boolean;
  repetido?: boolean;
  outro_com_evento?: boolean;
  formularios?: FormularioDaLinha[];
  sugestao?: SugestaoDeEvento | null;
}

/** Motivo de encerramento servido pelo servidor — a tela não tem cópia da lista. */
export interface MotivoEncerramento {
  codigo: string;
  rotulo: string;
  /** Este motivo exige a frase ("Outro") — a tela não conhece os códigos. */
  pede_frase?: boolean;
}

/** Bloco `formularios` do `/api/dashboard` (feature 298) — contrato em `contracts/dashboard-formularios.md`. */
export interface FormulariosSummary {
  contagens?: StatusCounts;
  /** Papel efetivo pode criar evento (senão a ação da linha é "Abrir"). */
  pode_criar_evento?: boolean;
  motivos_encerramento?: MotivoEncerramento[];
  a_chegar?: LinhaFormulario[];
  ja_passou?: LinhaFormulario[];
  /** Feature 299 — linhas vermelhas e amarelas: o número do card e da parte do total. */
  para_agir?: number;
}

export interface DashboardSummary {
  casting: CastingSummary | null;
  figurino: FigurinoSummary | null;
  /**
   * Único painel da home cujo gate é a IDENTIDADE, não o papel: quem tem peça sob sua
   * responsabilidade vê, seja qual for o papel (feature 225).
   */
  figurino_producao: MinhasPecasSummary | null;
  /** Fila do setor de figurino: pedidos sem dono. Gate por PAPEL (FIGURINO/SA). */
  figurino_oficina: OficinaFilaSummary | null;
  ensaio: EnsaioSummary | null;
  comercial: ComercialSummary | null;
  /**
   * Formulários que chegaram desde o corte e ainda não têm destino (feature 298). Mesmo gate do
   * bloco comercial; `null` = sem permissão ou painel que falhou.
   */
  formularios: FormulariosSummary | null;
  financeiro: { recurring_expense_alerts: RecurringExpenseAlert[] } | null;
  performance: PerformanceSummary | null;
  dismissed_casting: DashboardTaskRef[];
  /** URL raiz do portal do artista (PORTAL_URL), ou `null` quando a env var não está setada. */
  portal_url: string | null;
}
