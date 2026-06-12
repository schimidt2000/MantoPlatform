# Tasks: Usuários sem acesso + limpeza da tela de Usuários

**Input**: `specs/042-usuarios-sem-acesso/`
**Tests**: boot + ruff + migration + test client.

## Phase 1: Banco e modelo
- [x] T001 Migration `n0c1d2e3f4a5`: `users.has_access` + email/password_hash nullable; aplicar local.
- [x] T002 `models.py`: User com `has_access`, nullables, guard em `check_password`.

## Phase 2: Login
- [x] T003 `auth/routes.py`: recusar login de `has_access=False`.

## Phase 3: Admin
- [x] T004 `create_user` POST: dois tipos + PIX + salário; redirect com flash.
- [x] T005 `edit_user` POST: email opcional p/ sem acesso; rota `grant_access`.
- [x] T006 `admin_create_user.html`: toggle de tipo + seções PIX/salário.
- [x] T007 `admin_users.html`: sem botão identidade visual; selo "sem acesso"; email "—".
- [x] T008 `admin_user_edit.html`: painéis condicionais + "Conceder acesso".
- [x] T009 Rótulos: `admin_layout.html` e `admin_dashboard.html` → "Configurações".

## Phase 4: Verificação
- [x] T010 ruff + boot + test client (US1–US4); commit.

## Dependencies
- T001 → T002 → demais; T010 por último.
