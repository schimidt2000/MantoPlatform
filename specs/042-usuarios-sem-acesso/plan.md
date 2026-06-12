# Implementation Plan: Usuários sem acesso + limpeza da tela de Usuários

**Branch**: `042-usuarios-sem-acesso` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

1. **Banco** (migration manual `n0c1d2e3f4a5`): `users.has_access` (Boolean, NOT NULL, default 1) +
   `users.email` e `users.password_hash` passam a nullable (pessoa sem acesso não tem login).
2. **Modelo**: campos atualizados; `check_password` retorna False se não houver hash.
3. **Login**: recusa explícita de `has_access=False` (mesma mensagem genérica).
4. **Novo usuário**: form com toggle de tipo (Com acesso / Apenas pagamento) + seções PIX e
   salário opcionais; POST cria User (+SalaryHistory/PIX) conforme o tipo.
5. **Lista**: selo "sem acesso", email "—".
6. **Edição**: pessoa sem acesso esconde cargos/reset; painel "Conceder acesso" (superadmin) com
   email + senha temporária (`must_change_password=True`).
7. **Identidade visual**: botão removido de admin_users.html; rótulos "Identidade (Visual)" →
   "Configurações" em admin_layout.html e admin_dashboard.html. `/admin/settings` permanece.

## Constitution Check
- **I. Reutilizar** ✅ — mesma lógica de PIX/salário do edit_user; padrão de migrations manuais.
- **IV. Não quebrar** ✅ — usuários existentes ficam `has_access=True` (server_default); fluxos de
  login/edição atuais inalterados para quem tem acesso.
- **V. UI/UX** ✅ — toggle de tipo com mostrar/ocultar via JS, flash de sucesso/erro, selo na lista.

## Design Detalhado

### 1. Migration `n0c1d2e3f4a5_users_sem_acesso.py`
```python
with op.batch_alter_table("users") as b:
    b.add_column(sa.Column("has_access", sa.Boolean(), nullable=False, server_default="1"))
    b.alter_column("email", existing_type=sa.String(120), nullable=True)
    b.alter_column("password_hash", existing_type=sa.String(255), nullable=True)
```
(downgrade reverte; emails NULL múltiplos são permitidos pelo UNIQUE em SQLite/Postgres)

### 2. `app/models.py` — User
- `email`/`password_hash` nullable=True; `has_access = db.Column(Boolean, nullable=False,
  default=True, server_default="1")`.
- `check_password`: `if not self.password_hash: return False`.

### 3. `app/auth/routes.py` — login
- Após buscar o usuário: `if not user or not user.has_access or not user.check_password(...)` →
  mesma mensagem "Email ou senha inválidos".

### 4. `app/admin/routes.py`
- `create_user` POST reescrito:
  - `user_type = form["user_type"]` ∈ {"access", "payment_only"}.
  - access: exige name/email/senha; valida email único; roles.
  - payment_only: exige só name; email opcional (único se preenchido); sem roles/senha;
    `has_access=False`.
  - Comum: `pix_key`/`pix_key_type`; salário opcional (mesma validação de `add_salary`: valor>0,
    tipo ∈ {semanal, quinzenal, comissao}, data) → cria `SalaryHistory`.
  - Sucesso: redirect para a lista com flash (em vez de re-render com msg).
- `edit_user` POST: para `not user.has_access`, email opcional e roles ignoradas.
- Nova rota `grant_access` POST (`/users/<id>/grant-access`, superadmin): valida email
  obrigatório/único + senha temporária; seta `email`, `set_password`, `has_access=True`,
  `must_change_password=True`; audit + flash.

### 5. Templates
- `admin_users.html`: remove botão "Identidade visual"; `{{ u.email or '—' }}`; selo
  `badge-gray "sem acesso"` ao lado do nome quando `not u.has_access`.
- `admin_create_user.html`: radio do tipo; JS esconde bloco credenciais/cargos no tipo
  payment_only (required dinâmico em email/senha); seções "PIX (opcional)" e
  "Salário (opcional)" (valor + tipo + início + obs).
- `admin_user_edit.html`: subtítulo `{{ user.email or 'sem acesso ao sistema' }}`; painéis de
  cargos/reset/email só para `user.has_access` (cargo some, campo email vira opcional de contato);
  painel "Conceder acesso" quando `not user.has_access and is_superadmin`.
- `admin_layout.html` "Identidade" → "Configurações"; `admin_dashboard.html` card "Identidade
  Visual" → "Configurações" (texto "Comissão padrão, logo, datas do sistema").

### 6. Verificação
- ruff (sem novos) + boot + migration aplicada local.
- Test client: criar payment_only (nome+pix+salário) → User has_access=False, SalaryHistory
  vigente, lista com selo e "—"; login com email vazio/None falha; conceder acesso → login ok com
  troca de senha; criar com acesso completo (email+senha+pix+salário) ok; financeiro/pagamentos
  renderiza com pessoa sem acesso; botão "Identidade visual" ausente.

## Project Structure
```text
migrations/versions/n0c1d2e3f4a5_users_sem_acesso.py
app/models.py                      # User: has_access, nullable email/password_hash
app/auth/routes.py                 # login recusa sem acesso
app/admin/routes.py                # create_user, edit_user, grant_access
app/templates/admin_users.html
app/templates/admin_create_user.html
app/templates/admin_user_edit.html
app/templates/admin_layout.html
app/templates/admin_dashboard.html
```

## Fora de escopo
- Excluir `/admin/settings` (mantida — funções críticas; ver Assumptions da spec).
- Foto de perfil / data de nascimento no cadastro (continuam no perfil próprio).
