# Tasks: Corrigir soma das parcelas (072)

**Feature**: `072-fix-parcela-soma-parse` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem backend/migration. Verificação de render contra **`manto_local`**.

---

## Fase 1 — Helpers BR-seguros

- [X] T001 `app/templates/event_detail.html`: adicionar `_brlSum(inp)` (extrai dígitos → /100, igual à máscara calculadora) e `_brlSumFmt(n)` (formata em pt-BR), **sem** depender de `window.MoneyMask`.

## Fase 2 — Usar nos cálculos (US1)

- [X] T002 [US1] `recompParcelas()`: somar com `_brlSum` e exibir com `_brlSumFmt` (remover `window.MoneyMask ? MoneyMask.parseNumber : parseFloat` e `sum.toFixed(2)`).
- [X] T003 [US1] `recompNotas()`: idem (mesma regra), para evitar o mesmo erro nas notas (069).

## Fase 3 — Verificação

- [X] T004 Contra **`manto_local`**: render de `event_detail` para evento com 2 parcelas de R$ 9.400,00 → soma R$ 18.800,00, sem alerta falso; conferir lógica do parser (9.400,00→9400). `ruff` sem erros (sem .py alterado).

---

## Dependências

- T001 → (T002, T003) → T004.

## MVP

T001+T002 corrigem o caso do print; T003 previne o mesmo nas notas.
