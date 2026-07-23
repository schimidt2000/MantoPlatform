# Data Model: Redesenho e Fidelidade Visual das Telas Principais

Nenhum modelo SQLAlchemy novo. Esta feature só adiciona forma aos dados já existentes
(serialização adicional em `/api/dashboard`) e componentes de apresentação no frontend.

## `DashboardSummary` (extensão do tipo TS existente)

```ts
export interface DashboardSummary {
  casting: { pending: TaskRef[]; rejected_invites: TaskRef[]; total: number; done: number } | null;
  figurino: { pending: TaskRef[]; total: number; done: number } | null;
  comercial: { pending_payments: PendingPayment[] } | null; // NOVO
  financeiro: { recurring_expense_alerts: RecurringAlert[] } | null;
  dismissed_casting: TaskRef[];
  performance: PerformanceSummary | null; // NOVO — só para papel real SUPERADMIN
}

export interface PendingPayment {
  event_id: number;
  event_title: string;
  start_at: string | null;
  sale: number;
  received: number;
  saldo: number;
  severity: "atrasado" | "vencido" | "urgent" | "warn" | "info";
  due_date: string | null; // ISO date, só quando payment_method é futuro/faturado
}

export interface PerformanceSummary {
  range: "7" | "30" | "custom";
  start: string | null; // ISO date, eco do período efetivo usado
  end: string | null;
  casting_total: number;
  casting_done: number;
  figurino_total: number;
  figurino_done: number;
  money_total: number; // soma de EventRole.cache_value no período
}
```

- `comercial`/`performance` seguem a mesma regra de visibilidade RBAC dos campos já existentes:
  `null` quando o papel efetivo não tem acesso (mesma função `_effective_has_role`).
- `performance` NUNCA aparece durante impersonação (`is_superadmin = _is_real_superadmin(user)
  and not impersonate`), preservando a regra já usada para `dismissed_casting`.

## `EventoResumo` (sem mudança de campo — reclassificação visual apenas)

Já expõe `event_type`, `start_at`, `end_at`, `title`, `location`, `is_satellite`, `group_name`,
`confirmed` — suficiente para colorir/posicionar o bloco na grade de calendário. Nenhum campo
novo necessário.

## `TalentSummary` (sem mudança de campo)

Já expõe `photo_face_path`, `height_cm`, `clothing_size_top`, `shoe_size`, `warning_level`,
`character_matches` — suficiente para o mosaico. Nenhum campo novo necessário.

## Entidades de apresentação (sem persistência)

- **DonutSpec**: `{ label: string; done: number; total: number; tone: "gold" | "blue" }` — prop
  de entrada do componente `DonutChart`, derivada de `casting`/`figurino` na resposta.
- **CalendarCell**: `{ date: string; inCurrentMonth: boolean; isToday: boolean; events:
  EventoResumo[] }` — construída em memória por `CalendarGrid` a partir de `AgendaMes.events` +
  `ym`; nunca persistida ou enviada ao backend.
- **EventCategoryStyle**: `{ label: string; bg: string; fg: string }` — resultado de
  `eventCategory(event_type: string)`, mapa estático local ao frontend (ver research.md R4).
