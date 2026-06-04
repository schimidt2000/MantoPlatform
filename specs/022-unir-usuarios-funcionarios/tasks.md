# Tasks: Unir Usuários + Funcionários

**Input**: `specs/022-unir-usuarios-funcionarios/`
**Tests**: boot + ruff + render + RBAC manual.

## Phase 1: Backend (admin)
- [ ] T001 admin/routes.py: `require_users_access` (SUPERADMIN|FINANCEIRO); imports (abort,
      SalaryHistory, date).
- [ ] T002 list_users/edit_user → `require_users_access`; passar `is_superadmin` + salário atual;
      edit_user POST atualiza identidade só superadmin (tira PIX daqui).
- [ ] T003 novas rotas `update_pix` e `add_salary` (require_users_access); add_salary replica a
      lógica de salário (encerra vigente + novo SalaryHistory + audit).

## Phase 2: Templates
- [ ] T004 admin_users.html: coluna "Salário atual"; ações criar/identidade/excluir só superadmin.
- [ ] T005 admin_user_edit.html: identidade (superadmin) / PIX (ambos→update_pix) / salário+histórico
      (ambos→add_salary) / reset senha (superadmin).

## Phase 3: Nav + redirects
- [ ] T006 base.html: "Funcionários" → "Usuários" (/admin/users).
- [ ] T007 financeiro/routes.py: funcionarios/funcionario_detail → redirect p/ admin; apagar os 2
      templates de funcionários.

## Phase 4: Verificação
- [ ] T008 boot + ruff; superadmin edita tudo; financeiro edita só PIX+salário (sem papéis/senha/
      excluir); /financeiro/funcionarios* redireciona; custo de pessoal inalterado.

## Dependencies
- T001→T002→T003. T004/T005 após backend. T006/T007. T008 ao fim.

## Notes
- Sem migration. Cálculos financeiros inalterados.
