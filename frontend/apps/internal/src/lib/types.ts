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

export interface CastingSummary {
  pending: DashboardTaskRef[];
  rejected_invites: DashboardTaskRef[];
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

/** Resumo do dashboard — resposta de /api/dashboard. Seções ausentes = sem permissão. */
export interface DashboardSummary {
  casting: CastingSummary | null;
  figurino: FigurinoSummary | null;
  financeiro: { recurring_expense_alerts: RecurringExpenseAlert[] } | null;
  dismissed_casting: DashboardTaskRef[];
}
