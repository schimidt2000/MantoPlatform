# Tasks: Lista de adiantamentos de salário (089)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: Dados

- [X] T001 Modelo `SalaryAdvance` + relação `advances`/property `advance_total` em `app/models.py`.
- [X] T002 Migração manual (`down_revision='x0a1b2c3d4e5'`): cria `salary_advances` e importa os
  adiantamentos únicos existentes (`advance_amount` não nulo).

## Phase 2: US1 — Adicionar vários sem perder histórico (P1) 🎯 MVP

- [X] T003 [US1] `salary_advance` passa a **adicionar** um `SalaryAdvance` (valida > 0, comprovante
  obrigatório, `total + novo ≤ salário`) em `app/financeiro/routes.py`.
- [X] T004 [US1] `_build_payment_items`: total via `advance_total`; incluir lista `advances`
  (`{id, amount, date, proof}`) e `amount = salário − total`.
- [X] T005 [US1] Ajustar a preservação na regeneração (feature 068) para não apagar salários **com
  adiantamentos** (subquery em `salary_advances`).
- [X] T006 [US1] Modal em `pagamentos.html`: lista de adiantamentos + total + líquido + form de
  adicionar; linha mostra o total adiantado.

## Phase 3: US2 — Remover um adiantamento (P2)

- [X] T007 [US2] Rota `salary_advance_delete` (remove item + arquivo) + botão "Remover" por item no modal.

## Phase 4: Verificação

- [X] T008 Verificar contra `manto_local`: migração importa existentes; 2 adiantamentos coexistem; total/
  líquido corretos; soma > salário bloqueada; remover mantém os demais; regeneração preserva. `ruff` ok.

## Dependencies

- T001→T002→(T003..T007). T008 por último.

## MVP

US1 (lista que adiciona sem sobrescrever + total/líquido + preservação) é o essencial.
