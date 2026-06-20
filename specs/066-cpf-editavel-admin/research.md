# Research: CPF do talento editável (apenas admin) (066)

Decisões técnicas. Sem `NEEDS CLARIFICATION`. Sem migration.

## 1. Estado atual

- `talent_edit.html` (linhas 107-108): CPF `disabled`, rótulo "(não editável)".
- `talents/routes.py::edit_talent` (gate `_can_edit_talent` = SUPERADMIN ou CASTING) **não**
  processa CPF no POST.
- CPF é armazenado como **apenas dígitos** (`importer.only_digits`); validação na importação =
  `len(cpf) >= 11`; unicidade via `Talent.query.filter_by(cpf=...)`. Coluna `Talent.cpf`
  unique/not null.

## 2. Edição restrita a super admin

- **Decisão**: no `edit_talent` POST, processar `cpf` **somente** se o usuário for SUPERADMIN.
  Normalizar com `only_digits`; exigir 11 dígitos; recusar duplicado (outro talento com mesmo
  CPF); vazio mantém o atual. CASTING (não-admin) nunca altera (servidor ignora o campo).
- **Rationale**: o gate do form já permite CASTING editar talento; o CPF precisa de uma checagem
  **adicional** de SUPERADMIN no servidor (FR-002), não basta esconder no template.
- **Validação**: reusa `only_digits` (fonte única do formato). Sem dígito verificador (fora do
  escopo, como a importação).

## 3. UI

- **Decisão**: no template, se `is_superadmin`, renderizar o CPF como input editável
  (`name="cpf"`); senão, manter `disabled` (como hoje). Passar `is_superadmin` ao template no GET
  e nos re-renders de erro.

## 4. Auditoria

- **Decisão**: ao alterar o CPF, registrar via `audit("edit", "talent", ...)` com nota "CPF
  alterado" — **sem** o número no texto (PII). Reusa o helper `app.utils.audit` já usado na
  edição.

## 5. Erros

- **Decisão**: CPF inválido (≠11 dígitos) ou duplicado → `flash(... "error")` e re-render do form
  sem persistir (validação feita no início do POST, antes de mutar os demais campos).

## 6. Sem migration

- Coluna `cpf` já existe; só muda quem edita e a validação na edição.
