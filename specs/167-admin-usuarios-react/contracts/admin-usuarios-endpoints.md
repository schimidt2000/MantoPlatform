# Contrato de API — Gestão de Usuários (Admin) (167)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md`.

## `GET /api/admin/users`

- Gate: SUPERADMIN ou FINANCEIRO.
- 200: `{"items": [{"id", "name", "email", "has_access", "is_active", "receives_commission",
  "pix_key", "pix_key_type", "role_names": [...], "role_ids": [...], "salary": {"amount",
  "payment_type", "start_date", "notes"} | null}, ...], "all_roles": [{"id", "name"}, ...]}`
  (`all_roles` reaproveitado pelas telas de criação/edição para o seletor de papéis).

## `POST /api/admin/users`

- Gate: SUPERADMIN.
- Body: `{"user_type": "access"|"payment_only", "name", "email"?, "temp_password"?,
  "role_ids"?: number[], "pix_key"?, "pix_key_type"?, "salary"?: {"amount": number,
  "payment_type": "semanal"|"quinzenal"|"comissao", "start_date"?, "notes"?}}`.
- 201: usuário criado (mesmo shape do item de `GET /api/admin/users`).
- 400: `{"error": {"message": "...", "fields": {"name"|"email"|"temp_password"|"salary": "..."}}}`.

## `GET /api/admin/users/<id>`

- Gate: SUPERADMIN ou FINANCEIRO.
- 200: usuário (mesmo shape do item de lista) + `"salary_history": [...]` (todos os registros,
  mais recente primeiro).
- 404: usuário não encontrado.

## `PATCH /api/admin/users/<id>`

- Gate: SUPERADMIN.
- Body: `{"name", "email"?, "is_active": bool, "receives_commission": bool, "role_ids"?:
  number[]}`.
- 200: usuário atualizado.
- 400: email ausente com `has_access=true`, ou email duplicado.

## `PATCH /api/admin/users/<id>/pix`

- Gate: SUPERADMIN ou FINANCEIRO.
- Body: `{"pix_key"?, "pix_key_type"?}`.
- 200: usuário atualizado.

## `POST /api/admin/users/<id>/salary`

- Gate: SUPERADMIN ou FINANCEIRO.
- Body: `{"amount": number, "payment_type": "semanal"|"quinzenal"|"comissao", "start_date"?,
  "notes"?}`.
- 200: novo registro de salário; o vigente anterior (se houver) é encerrado.
- 400: tipo de pagamento inválido ou valor ausente (fora de "comissao").

## `POST /api/admin/users/<id>/grant-access`

- Gate: SUPERADMIN.
- Body: `{"email", "temp_password"}`.
- 200: usuário atualizado (`has_access=true`).
- 400: já tem acesso, campos ausentes, ou email duplicado.

## `POST /api/admin/users/<id>/reset-password`

- Gate: SUPERADMIN.
- Body: `{"temp_password"}`.
- 200: `{"ok": true}`.
- 400: senha ausente.

## `DELETE /api/admin/users/<id>`

- Gate: SUPERADMIN.
- 204: usuário excluído.
- 400 (auto-exclusão): `{"error": {"message": "Você não pode excluir seu próprio usuário."}}`.
- 400 (bloqueado): `{"error": {"message": "...", "blockers": ["comissões", "orçamentos", ...]}}`.
