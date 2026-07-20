/** Tipos dos recursos da API consumidos pela Fundação (data-model.md). */

/** Usuário autenticado — resposta de /api/auth/me e /api/auth/login. */
export interface AuthUser {
  id: number;
  name: string;
  email: string;
  roles: string[];
  is_superadmin: boolean;
  impersonating: string | null;
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
