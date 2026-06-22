# Tasks: Adiantamento de salário com comprovante

**Feature**: `067-adiantamento-salario` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Migration manual (head `t6c7d8e9f0a1`). DRE/custo de salário NÃO muda. Verificação contra
**`manto_local` (Postgres)**.

---

## Fase 1 — Modelo + migration

- [X] T001 `app/models.py`: em `SalaryPayment`, adicionar `advance_amount` (Numeric(12,2), nullable) e `advance_proof` (String(300), nullable).
- [X] T002 Migration manual `migrations/versions/u7d8e9f0a1b2_salary_advance.py` (down_revision `t6c7d8e9f0a1`): add as 2 colunas em `salary_payments`; downgrade reverte. Aplicar `flask db upgrade` no `manto_local`.

## Fase 2 — Backend

- [X] T003 [US1] `app/financeiro/routes.py`: rota `POST /financeiro/pagamentos/salary/<int:sp_id>/advance` (`require_financeiro`): `parse_brl(advance_amount)`; recusa se > `sp.amount`; recusa se >0 sem comprovante (novo ou existente); 0/vazio zera; salva arquivo em `UPLOAD_PAYMENTS` (`/uploads/payments/...`); `audit`; redirect à tela (mês).
- [X] T004 [US1] `_build_payment_items` (salário): `amount` = `sp.amount - (advance_amount or 0)`; expor `gross_amount`, `advance_amount`, `advance_proof`. **Não** alterar `_salary_cost`.

## Fase 3 — UI

- [X] T005 [US1/US2] `app/templates/financeiro/pagamentos.html`: na linha de salário, botão **"Editar"** com `data-*` (id, pessoa, salário cheio, adiantamento, comprovante); **modal único** (multipart) postando na rota; exibir **líquido** + nota "(adiantado R$X)" + link do comprovante.

## Fase 4 — Verificação

- [X] T006 Verificar contra **`manto_local`**: aplicar migration; adiantamento + comprovante → líquido reduzido; >0 sem comprovante recusado; > salário recusado; zerar volta ao cheio; custo de salário do período inalterado. `ruff check` sem erros novos (comparar `git stash`).

---

## Dependências

- T001→T002→(T003,T004)→T005. T006 ao final.

## MVP

T001–T005 entregam o pedido (adiantamento com comprovante reduzindo o líquido a pagar).
