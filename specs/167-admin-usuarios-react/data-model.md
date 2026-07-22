# Data Model: Gestão de Usuários (Admin) em React (167)

Nenhuma tabela/campo novo — reaproveita `User`/`SalaryHistory`/`Role` já existentes.

## Entidades

| Entidade         | Uso                                                                          |
|------------------|-------------------------------------------------------------------------------|
| `User`           | listar/criar/editar identidade/papéis/PIX/status; conceder acesso; resetar senha; excluir |
| `SalaryHistory`  | histórico de salário — no máximo um registro vigente (`end_date=null`) por usuário |
| `Role`           | papéis atribuíveis a um usuário com acesso                                    |

## Valores computados (movidos para `user_ops.py`, sem duplicar regra)

- `list_users_with_salary()` — todos os usuários (ordenados por id), cada um com o salário
  vigente (`end_date IS NULL`), se houver.
- `_normalize_salary(value, payment_type)` — `comissao` → sempre 0; `semanal`/`quinzenal` →
  exige valor > 0; tipo vazio/desconhecido → erro. Mesma regra de hoje, movida sem alteração.
- `create_user(...)` — cria `User` (com ou sem acesso), valida email único, aplica papéis (só
  se `has_access`), PIX e salário opcionais; registra auditoria (`audit`).
- `update_user_identity(user, ...)` — nome/email/status/comissão/papéis; exige email se
  `has_access`; valida email único (excluindo o próprio usuário).
- `update_pix(user, ...)` / `add_salary(user, ...)` — mesmas regras de hoje, sem mudança.
- `grant_access(user, email, temp_password)` — recusa se já tem acesso; valida email único.
- `reset_password(user, temp_password)` — define nova senha temporária, `must_change_password`.
- `delete_user(user, actor_id)` — recusa auto-exclusão; recusa se houver `CommissionPayment`
  (seller), `OrcamentoHistory`, `SpecialExpense` (criado por) ou `CalendarEvent` (seller)
  vinculados — lista os bloqueios encontrados; caso contrário desfaz vínculos opcionais
  (`SalaryPayment`, `SalaryHistory`, `EnsaioMaterial.user_id`,
  `SpecialExpense.approved_by_id`/`reimburse_user_id`, `SiteSetting.educamanto_seller_id`) e
  exclui.
- `UserValidationError(field, message)` — exceção nova, única forma de erro de validação de
  negócio nesta fatia; `routes.py` (Jinja) converte em `flash`, endpoints de API convertem em
  400 `{"error": {"message", "fields": {field: message}}}`.
- `UserDeletionBlockedError(blockers: list[str])` — exceção nova para o caso de exclusão
  bloqueada por histórico financeiro; API converte em 400
  `{"error": {"message", "blockers": [...]}}`.
