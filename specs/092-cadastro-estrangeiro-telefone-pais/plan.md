# Implementation Plan: Talento estrangeiro + telefone com país (092)

**Branch**: `092-cadastro-estrangeiro-telefone-pais` | **Date**: 2026-06-29 | **Spec**: [spec.md](spec.md)

## Summary

Permitir cadastro e acesso ao portal de talentos **estrangeiros sem CPF** (identidade por e-mail), e trocar
o campo de telefone por **seletor de país (DDI) + número**, prefixando `+55` em todos os telefones já
cadastrados. Sem quebrar o fluxo atual de quem tem CPF.

## Technical Context

### Modelo (`app/models.py`)
- `cpf`: passa a `nullable=True` (mantém `unique=True` — NULL repetível no Postgres).
- Novo `is_foreigner` (Boolean, default False, server_default "0").
- Novo `@property whatsapp_number`: dígitos do telefone **com** código de país; se o telefone não tiver `+`
  e tiver ≤ 11 dígitos, assume Brasil (`55` + dígitos) para compatibilidade.

### Migração (`migrations/versions/`) — revisão `a3d4e5f6a7b8`, down_revision `z2c3d4e5f6a7`
- `add_column talents.is_foreigner` (default False).
- `alter_column talents.cpf` → nullable.
- **Data**: `UPDATE talents SET phone = '+55 ' || phone WHERE phone IS NOT NULL AND phone <> '' AND phone NOT LIKE '+%'`.

### Cadastro público (`app/cadastro/routes.py` + `templates/cadastro/form.html`)
- Checkbox **"Sou estrangeiro(a) (não tenho CPF)"**; JS tira o `required` do CPF quando marcado.
- Telefone: `<select name="phone_ddi">` (Brasil +55 padrão) + `<input name="phone_national">`; combina em
  `+55 <número>`. Mantém compat: se vier só `phone` (sem os novos campos), usa como antes.
- `submit()`: se `is_foreigner`, CPF vira opcional (salvo `None`); exige documento (RG/doc) como substituto.
  Se não, CPF obrigatório + único (inalterado).

### Portal (`app/talent_portal/routes.py` + templates login/first_access/forgot_password)
- Helper `_talent_by_login(value)`: se tem `@` → busca por `email_contact` (case-insensitive); senão →
  dígitos como CPF. Usado em `login`, `first_access`, `forgot_password`.
- Templates: rótulo do campo passa a **"CPF ou e-mail"** (mantém `name="cpf"`).

### WhatsApp (`templates/event_detail.html`)
- `wa.me/55{{ talent.phone_digits }}` → `wa.me/{{ talent.whatsapp_number }}` (2 ocorrências), evitando `55`
  duplicado após a migração.

## Constitution Check

- **I. Qualidade**: type hints + docstrings nos helpers novos.
- **IV. Não quebrar**: fluxo CPF inalterado; lookup por e-mail é aditivo; `whatsapp_number` tem fallback.
- **Testes**: verificação contra `manto_local` (Postgres) — pega o `cpf` nullable e o UPDATE de telefone.

**Resultado**: PASS — com migração (schema + data).

## Testing

Contra **`manto_local`**:
1. Migração aplica (is_foreigner, cpf nullable, telefones com `+55`, sem duplicar `+`).
2. Cadastro estrangeiro sem CPF cria talento `is_foreigner=True`, `cpf=None`.
3. Cadastro brasileiro sem CPF → erro (obrigatório).
4. Login/first-access por e-mail acha o talento; por CPF continua achando.
5. `whatsapp_number` correto (com país, sem `55` duplicado).
6. `ruff` sem erros novos.

## Project Structure

```text
app/models.py                          — cpf nullable, is_foreigner, whatsapp_number
migrations/versions/a3d4e5f6a7b8_*.py  — schema + data (telefones +55)
app/cadastro/routes.py                 — estrangeiro + telefone DDI
app/templates/cadastro/form.html       — checkbox estrangeiro + seletor de país
app/talent_portal/routes.py            — login/first-access/forgot por CPF ou e-mail
app/templates/portal/login.html        — rótulo "CPF ou e-mail"
app/templates/portal/first_access.html — rótulo "CPF ou e-mail"
app/templates/portal/forgot_password.html — rótulo "CPF ou e-mail" (se aplicável)
app/templates/event_detail.html        — wa.me usa whatsapp_number
```

## Complexity Tracking

> Sem violações.
