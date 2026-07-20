# Data Model — Fundação (144, User Story 1)

Nenhum modelo SQLAlchemy novo (a spec já registra isso em "Key Entities" — esta migração não
muda `app/models.py`). O que muda é a **forma de saída** de dois recursos já existentes,
agora como JSON em vez de contexto de template Jinja.

## Recurso: Usuário autenticado (`/api/auth/me`)

Espelha o `current_user` (Flask-Login, `app/models.py`) hoje usado nos templates:

| Campo | Tipo | Origem |
|---|---|---|
| `id` | int | `User.id` |
| `name` | string | `User.name` |
| `email` | string | `User.email` |
| `roles` | string[] | nomes dos papéis (`User.roles` → `Role.name`) — SUPERADMIN, CASTING, FIGURINO, COMERCIAL, FINANCEIRO, VENDAS, ENSAIO, RH |
| `is_superadmin` | bool | derivado — `any(r.name == SUPERADMIN)` |
| `impersonating` | string \| null | espelha `session["impersonate_role"]`, hoje só disponível a um SUPERADMIN real (`app/__init__.py:475-476`) |

## Recurso: Resumo do dashboard (`GET /api/dashboard`)

Espelha a agregação hoje feita na view `home()` (`app/__init__.py:399+`) — hoje ~150 linhas
de queries condicionadas por papel, renderizadas direto no template. Os campos exatos do
JSON MUST ser extraídos por leitura completa dessa função no momento da implementação (não
adivinhados nesta spec) — o que segue é a estrutura de alto nível já confirmada na leitura
parcial feita para este plano:

- `casting`: `{pending: EventRole[], rejected_invites: EventRole[], total: int, done: int}` —
  visível se `show_casting` (papel CASTING ou superadmin)
- `figurino`: `{pending: EventRole[], total: int, done: int}` — visível se `show_figurino`
  (cálculo já corrigido: roles COM talento e SEM `figurino_done_at`, excluindo rejeitados e
  papel "extra" — ver bug histórico documentado em memória, já corrigido no código atual)
- `ensaio`: `{pending: CalendarEvent[], scheduled: CalendarEvent[], orphans: CalendarEvent[], pending_presence: EventRole[]}` —
  visível se `show_ensaio`
- `financeiro.recurring_expense_alerts`: lista de alertas de gastos recorrentes do mês —
  visível se `show_financeiro`
- `dismissed_casting`: cargos dispensados (feature 108) — visível só para SUPERADMIN real
  (não durante impersonation)

Cada sub-recurso (`EventRole`, `CalendarEvent`) usado dentro do dashboard reaproveita o
mesmo formato JSON que será definido quando o blueprint `calendar` for migrado (US2) — a
Fundação define só o suficiente para o dashboard funcionar, não o contrato completo de
Agenda/Eventos (isso é escopo de US2, com seu próprio `/speckit-plan`).
