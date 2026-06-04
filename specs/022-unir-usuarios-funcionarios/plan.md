# Implementation Plan: Unir Usuários + Funcionários

**Branch**: `022-unir-usuarios-funcionarios` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Concentrar identidade + PIX + salário na seção **Usuários** (Admin). A lista e a edição passam a ser
acessíveis ao Financeiro (além do Superadmin), com seções controladas: identidade/papéis/senha/
exclusão = Superadmin; PIX + salário = Superadmin + Financeiro. O salário (histórico) é gerenciado
na própria página do usuário. "Funcionários" some do menu e suas URLs redirecionam para Usuários.
Sem migration (PIX e histórico de salário já existem). Ambas as páginas já usam `base.html`.

## Constitution Check
- **I. Reutilizar / IV. Não quebrar** ✅ — reaproveita admin users + lógica de salário do financeiro;
  cálculos financeiros intactos; redirects preservam links; verificação no app.
- **V. UI/UX** ✅ — uma seção só; seções escondidas conforme permissão.
- **VI. Planejar antes de codar** ✅ — este plano; RBAC confirmado com o usuário.

## Project Structure

```text
app/admin/routes.py                 # require_users_access; list_users/edit_user liberam Financeiro;
                                    #   edit_user(identidade=superadmin); novas rotas update_pix e add_salary
app/templates/admin_users.html      # coluna "Salário atual"; ações de criar/excluir só superadmin
app/templates/admin_user_edit.html  # 3 blocos: identidade (superadmin), PIX (ambos), salário+histórico (ambos)
app/templates/base.html             # nav "Funcionários" -> "Usuários" (/admin/users)
app/financeiro/routes.py            # funcionarios/funcionario_detail -> redirect p/ admin
app/templates/financeiro/funcionarios.html, funcionario_detail.html  # apagar (não usados)
```

## Design Detalhado

### Permissões (admin/routes.py)
- `_is_sa()` = tem SUPERADMIN. `require_users_access` = SUPERADMIN ou FINANCEIRO (senão `abort(403)`).
- `list_users` e `edit_user`: decorator `require_users_access`.
- `edit_user` POST: **só superadmin** atualiza nome/email/ativo/recebe_comissão/papéis. PIX sai
  daqui.
- `update_pix` POST `/users/<id>/pix` (require_users_access): atualiza `pix_key`/`pix_key_type`.
- `add_salary` POST `/users/<id>/salario` (require_users_access): valida salário/tipo/início, encerra
  o vigente, cria `SalaryHistory`, audita (lógica vinda do financeiro).
- `create_user`, `reset_password`, `delete_user`: continuam `require_superadmin`.

### Templates
- `admin_users.html`: nova coluna "Salário atual" (atual ou —); botões "+ Novo"/"Identidade"/
  "Excluir" só `{% if is_superadmin %}` (Financeiro vê lista + "Editar").
- `admin_user_edit.html`: subtítulo com email/papéis; bloco **Identidade** (form, reset senha) só
  superadmin; bloco **PIX** (form → update_pix) para ambos; bloco **Salário** (form → add_salary +
  tabela de histórico) para ambos.

### Nav (base.html)
- Item "Funcionários" (seção Financeiro) → "Usuários" apontando para `/admin/users` (gate atual
  FINANCEIRO/SUPERADMIN mantém).

### Financeiro (redirect)
- `funcionarios()` → `redirect(url_for('admin.list_users'))`.
- `funcionario_detail(id)` → `redirect(url_for('admin.edit_user', user_id=id))`.

### Verificação
- Superadmin: edita identidade, papéis, PIX, salário, exclui; lista com salário.
- Financeiro: acessa Usuários; edita PIX e salário; NÃO vê papéis/senha/excluir; salário grava.
- `/financeiro/funcionarios` e `/financeiro/funcionarios/<id>` redirecionam.
- Painel financeiro (custo de pessoal) inalterado. ruff limpo.

### Fora de escopo
- Mudanças de cálculo financeiro; migration (nenhuma).
