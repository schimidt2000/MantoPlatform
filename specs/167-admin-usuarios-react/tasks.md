# Tasks: Gestão de Usuários (Admin) em React (167)

**Input**: Design documents from `specs/167-admin-usuarios-react/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/admin-usuarios-endpoints.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_167_admin_usuarios_react.py`
contra `manto_local`, gerado na Phase de Polish.

**Organização**: 4 user stories — US1 listar (P1), US2 criar (P2), US3 editar identidade (P3),
US4 PIX/salário/conceder-acesso/resetar-senha/excluir (P4).

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado — sem migration nova nesta fatia.

## Phase 2: Foundational

- [X] T002 Criar `app/admin/user_ops.py` (NOVO): mover `_normalize_salary`/`_parse_salary_form`
      e o núcleo de cada rota de `app/admin/routes.py` — `list_users_with_salary`,
      `create_user`, `update_user_identity`, `update_pix`, `add_salary`, `grant_access`,
      `reset_password`, `delete_user`; exceções `UserValidationError`/
      `UserDeletionBlockedError`. `routes.py` passa a chamar essas funções.
- [X] T003 [P] Criar `app/api/admin_users_read.py` (NOVO, esqueleto): gate
      `require_users_access` reimplementado como função (SUPERADMIN/FINANCEIRO).
- [X] T004 [P] Criar `app/api/admin_users_write.py` (NOVO, esqueleto): gate base +
      `require_superadmin` reimplementado para as ações restritas.
- [X] T005 Registrar os 2 módulos novos em `app/api/__init__.py`.
- [X] T006 [P] Criar `frontend/apps/internal/src/lib/adminUsers.ts` (NOVO, esqueleto): tipos
      TypeScript compartilhados.

## Phase 3: User Story 1 — Listar e consultar usuários (P1)

- [X] T007 [US1] Implementar `GET /api/admin/users` e `GET /api/admin/users/<id>` em
      `app/api/admin_users_read.py`.
- [X] T008 [P] [US1] Adicionar `useAdminUsers()`/`useAdminUser(id)` em `lib/adminUsers.ts`.
- [X] T009 [US1] Criar `frontend/apps/internal/src/pages/AdminUsersListPage.tsx` (NOVO).
- [X] T010 [US1] Adicionar rota `/admin/usuarios` em `App.tsx` (+ navegação).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: User Story 2 — Criar usuário (P2)

- [X] T011 [US2] Implementar `POST /api/admin/users` em `app/api/admin_users_write.py`.
- [X] T012 [P] [US2] Adicionar `useCreateAdminUser()` em `lib/adminUsers.ts`.
- [X] T013 [US2] Criar `frontend/apps/internal/src/pages/AdminUserCreatePage.tsx` (NOVO):
      formulário com acesso/só-pagamento + PIX + salário opcionais.
- [X] T014 [US2] Adicionar rota `/admin/usuarios/novo` em `App.tsx`.

**Checkpoint**: US2 completa e testável isoladamente.

---

## Phase 5: User Story 3 — Editar identidade e papéis (P3)

- [X] T015 [US3] Implementar `PATCH /api/admin/users/<id>` em `app/api/admin_users_write.py`.
- [X] T016 [P] [US3] Adicionar `useUpdateAdminUserIdentity(id)` em `lib/adminUsers.ts`.
- [X] T017 [US3] Criar `frontend/apps/internal/src/pages/AdminUserEditPage.tsx` (NOVO): seção
      de identidade/papéis (só Superadmin).
- [X] T018 [US3] Adicionar rota `/admin/usuarios/:id` em `App.tsx`.

**Checkpoint**: US3 completa e testável isoladamente.

---

## Phase 6: User Story 4 — PIX/salário/conceder-acesso/resetar-senha/excluir (P4)

- [X] T019 [US4] Implementar `PATCH /api/admin/users/<id>/pix`,
      `POST /api/admin/users/<id>/salary`, `POST /api/admin/users/<id>/grant-access`,
      `POST /api/admin/users/<id>/reset-password`, `DELETE /api/admin/users/<id>` em
      `app/api/admin_users_write.py`.
- [X] T020 [P] [US4] Adicionar `useUpdatePix`/`useAddSalary`/`useGrantAccess`/
      `useResetPassword`/`useDeleteAdminUser` em `lib/adminUsers.ts`.
- [X] T021 [US4] Completar `AdminUserEditPage.tsx`: seções de PIX/salário (Superadmin+
      Financeiro), botões de conceder-acesso/resetar-senha/excluir (só Superadmin,
      confirmação via `window.confirm` na exclusão).

**Checkpoint**: US4 completa e testável isoladamente.

---

## Phase 7: Polish & Verificação

- [X] T022 Criar `scripts/db/verify_167_admin_usuarios_react.py` (gitignored): paridade
      API×Jinja de todas as 8 ações + RBAC (SUPERADMIN vs. SUPERADMIN/FINANCEIRO) + bloqueios
      de exclusão.
- [X] T023 Rodar `ruff check app/` nos arquivos tocados.
- [X] T024 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T025 Conferência mobile (320–430px) — **não verificado nesta sessão** (sem Playwright/
      chromium-cli no ambiente).
- [X] T026 Atualizar `docs/changelog.html` e republicar no link existente.

## Dependencies

Setup → Foundational → US1 → US2 → US3 → US4 → Polish. US2/US3/US4 dependem só da Foundational,
não umas das outras.

## Implementation Strategy

MVP = US1 (listar) — pré-requisito de navegação para as demais. US2–US4 entregam valor
incremental sobre a mesma `user_ops.py`.
