# Tasks: CPF do talento editável no site (apenas admin)

**Feature**: `066-cpf-editavel-admin` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Reusa `only_digits` e `audit`. Sem migration. Verificação contra **`manto_local` (Postgres)**.

---

## Fase 1 — Backend

- [X] T001 [US1/US2] `app/talents/routes.py::edit_talent`: calcular `is_superadmin`; no POST, processar `cpf` **apenas** se super admin — `only_digits`, exigir 11 dígitos (senão flash+re-render), recusar duplicado em outro talento (flash+re-render), vazio mantém o atual; ao mudar, registrar `audit` "CPF alterado" (sem o número). Passar `is_superadmin` ao `render_template` (GET e re-renders).

## Fase 2 — UI

- [X] T002 [US1/US2] `app/templates/talent_edit.html`: se `is_superadmin`, CPF vira input editável (`name="cpf"`, placeholder "somente números"); senão, mantém `disabled` ("não editável").

## Fase 3 — Verificação

- [X] T003 Verificar contra **`manto_local`**: super admin altera CPF (válido persiste; inválido e duplicado recusados; vazio mantém); não-admin → servidor ignora alteração; auditoria gravada. `ruff check` sem erros novos (comparar `git stash`).

---

## Dependências

- T001 antes de T002 (contexto `is_superadmin`). T003 ao final.

## MVP

T001 + T002 entregam o pedido (CPF editável por admin, bloqueado para os demais).
