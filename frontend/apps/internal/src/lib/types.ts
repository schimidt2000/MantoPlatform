/** Tipos dos recursos da API consumidos pela Fundação (data-model.md). */

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

/** Cobrança pendente (saldo em aberto) de um evento — feature 174. */
export interface PendingPayment {
  event_id: number;
  event_title: string;
  start_at: string | null;
  sale: number;
  received: number;
  saldo: number;
  severity: "atrasado" | "vencido" | "urgent" | "warn" | "info";
  due_date: string | null;
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
  comercial: { pending_payments: PendingPayment[] } | null;
  financeiro: { recurring_expense_alerts: RecurringExpenseAlert[] } | null;
  performance: PerformanceSummary | null;
  dismissed_casting: DashboardTaskRef[];
  /** URL raiz do portal do artista (PORTAL_URL), ou `null` quando a env var não está setada. */
  portal_url: string | null;
}
