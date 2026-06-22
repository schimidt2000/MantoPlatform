# Tasks: Corrigir adiantamento de salário + máscara BR

**Feature**: `068-corrigir-adiantamento-salario` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem migration. Verificação do **ciclo completo** contra **`manto_local`**.

---

## Fase 1 — Fix de persistência

- [X] T001 [US1] `app/financeiro/routes.py::_ensure_salary_payments`: no `delete()` dos `nao_pago` do mês, adicionar `SalaryPayment.advance_amount.is_(None)` ao filtro — assim lançamentos com adiantamento NÃO são apagados (preservados; a recriação não duplica pois já existem por user/due_date).

## Fase 2 — Máscara BR

- [X] T002 [US2] `app/templates/financeiro/pagamentos.html`: campo de adiantamento volta a ter `class="brl-input"` (placeholder "0,00"); no open do modal, voltar a chamar `MoneyMask.applyMask(amt)`. Backend já lê com `parse_brl`.

## Fase 3 — Verificação (ciclo completo)

- [X] T003 Contra **`manto_local`**: salvar adiantamento via rota → **GET `/financeiro/pagamentos`** (dispara `_ensure_salary_payments`) → conferir que o adiantamento PERSISTE e o item mostra o líquido. Conferir que um salário sem adiantamento ainda é regenerado. `ruff check` sem erros novos.

---

## Dependências

- T001 e T002 independentes. T003 ao final (precisa de T001).

## MVP

T001 (persistência) é o coração; T002 atende o pedido da máscara.
