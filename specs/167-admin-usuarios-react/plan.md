# Implementation Plan: Gestão de Usuários (Admin) em React (167)

**Branch**: `167-admin-usuarios-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/167-admin-usuarios-react/spec.md`

## Summary

Terceira fatia da US6 (Cauda Administrativa) da migração 144. Migra as 8 rotas de gestão de
usuários de `app/admin/routes.py` (lista, criar, editar, PIX, salário, conceder-acesso,
resetar-senha, excluir) para React + API JSON. Extrai o núcleo hoje embutido nas views para um
módulo novo `app/admin/user_ops.py` (mesmo padrão das fatias 154/162/165), reusado pela view
Jinja (mantida sem regressão) e pelos endpoints novos `/api/admin/users/*`.

## Technical Context

Igual às fatias 145–166: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: `_normalize_salary`/`_parse_salary_form` e a lógica de cada rota migram
  para `user_ops.py`, reusadas por Jinja e API sem duplicação; `parse_brl_int`
  (`app/money.py`) e `audit` (`app/utils.py`) continuam sendo a fonte única, só chamados a
  partir do módulo novo.
- **II (padrões de código)**: `user_ops.py` novo com type hints/docstrings Google-style, funções
  ≤30 linhas; endpoints novos em `app/api/admin_users_read.py`/`admin_users_write.py`.
- **III (API first)**: endpoints novos 100% JSON; views Jinja de `/admin/users*` continuam
  existindo em paralelo, sem mudança de comportamento (FR-007).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos dados gravados/
  mensagens de erro nos dois caminhos (Jinja e React), incluindo os bloqueios de exclusão.
- **V (feedback)**: loading/erro/sucesso via TanStack Query; confirmação via dialog antes de
  excluir usuário (ação destrutiva, `window.confirm` — mesmo padrão já usado em
  Talentos/Figurino/Clientes); erro de validação mantém os campos preenchidos e aponta o campo
  inválido (`react-hook-form`+`zod`).
- **VII (monetário)**: campo de salário usa `@manto/money` no frontend; API recebe/retorna
  inteiro (`parse_brl_int`), nunca string formatada.
- **VIII (mobile-first)**: telas seguem mobile-first por princípio geral de UI.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/167-admin-usuarios-react/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/admin-usuarios-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/admin/
├── routes.py                          # views Jinja passam a chamar user_ops.*, sem duplicar
└── user_ops.py                        # NOVO — núcleo: listar, criar, editar, pix, salário,
                                        #   conceder-acesso, resetar-senha, excluir
app/api/
├── admin_users_read.py                # NOVO — GET /api/admin/users, /api/admin/users/<id>
└── admin_users_write.py               # NOVO — POST/PATCH/DELETE de escrita
app/api/__init__.py                    # + import dos 2 módulos novos
frontend/apps/internal/src/
├── lib/adminUsers.ts                  # NOVO — hooks TanStack Query
├── pages/AdminUsersListPage.tsx       # NOVO
├── pages/AdminUserCreatePage.tsx      # NOVO
└── pages/AdminUserEditPage.tsx        # NOVO — identidade/papéis + PIX + salário + ações
App.tsx                                # + rotas /admin/usuarios, /admin/usuarios/novo,
                                        #   /admin/usuarios/:id
scripts/db/verify_167_admin_usuarios_react.py  # NOVO: paridade API×Jinja + RBAC 403
```

**Structure Decision**: núcleo extraído para `app/admin/user_ops.py` (mesmo padrão de extração
das fatias 154/162/165 — blueprint com lógica de negócio embutida nas views, sem separação
prévia). Endpoints de leitura/escrita divididos em dois arquivos `_read`/`_write`, mesmo padrão
de `financeiro`/`clientes`/`talents`.

## Design Decisions

1. **`app/admin/user_ops.py`** (novo): funções puras chamadas por `routes.py` (Jinja) e pelos
   endpoints de API — `list_users_with_salary()`, `create_user(...)`, `update_user_identity
   (user, ...)`, `update_pix(user, ...)`, `add_salary(user, ...)`, `grant_access(user, ...)`,
   `reset_password(user, ...)`, `delete_user(user, actor_id)`; mantém `_normalize_salary`/
   `_parse_salary_form` (adaptada para receber um dict em vez de `request.form` diretamente,
   reusada por ambos os lados). Erros de validação levantam `UserValidationError(field,
   message)` (mesmo padrão de `ClientValidationError` da 165).
2. **`GET /api/admin/users`**: gate SUPERADMIN/FINANCEIRO (`require_users_access`
   reimplementado como função) → `{"items": [{...usuário, "salary": {...} | null}]}`.
3. **`POST /api/admin/users`**: gate SUPERADMIN. Body `{"user_type": "access"|"payment_only",
   "name", "email"?, "temp_password"?, "role_ids"?, "pix_key"?, "pix_key_type"?, "salary"?:
   {"amount", "payment_type", "start_date"?, "notes"?}}` → 201 usuário criado; 400 com `fields`
   em erro de validação.
4. **`PATCH /api/admin/users/<id>`**: gate SUPERADMIN. Body `{"name", "email"?, "is_active",
   "receives_commission", "role_ids"?}` → 200 usuário atualizado; 400 em validação.
5. **`PATCH /api/admin/users/<id>/pix`**: gate SUPERADMIN/FINANCEIRO. Body `{"pix_key"?,
   "pix_key_type"?}` → 200.
6. **`POST /api/admin/users/<id>/salary`**: gate SUPERADMIN/FINANCEIRO. Body `{"amount",
   "payment_type", "start_date"?, "notes"?}` → 200/400.
7. **`POST /api/admin/users/<id>/grant-access`**: gate SUPERADMIN. Body `{"email",
   "temp_password"}` → 200/400.
8. **`POST /api/admin/users/<id>/reset-password`**: gate SUPERADMIN. Body `{"temp_password"}` →
   200/400.
9. **`DELETE /api/admin/users/<id>`**: gate SUPERADMIN. 204 em sucesso; 400 com a lista de
   bloqueios (`{"error": {"message": "...", "blockers": [...]}}`) quando há histórico
   financeiro; 400 em auto-exclusão.
10. **Frontend**: 3 telas — lista (`AdminUsersListPage`), criação (`AdminUserCreatePage`, os 3
    sub-formulários: identidade/PIX/salário) e edição (`AdminUserEditPage`, identidade+papéis
    para Superadmin, PIX+salário+histórico para Superadmin/Financeiro, ações de conceder-
    acesso/resetar-senha/excluir só para Superadmin, condicionadas no cliente por
    `is_superadmin` vindo de `/api/auth/me`).

## Complexity Tracking

Nenhuma violação nova.
