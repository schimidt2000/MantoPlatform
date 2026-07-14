# Implementation Plan: Gasto Extra Já Nasce Pago (128)

**Branch**: `128-gasto-ja-pago` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

`SpecialExpense` ganha uma coluna `paid_at_creation` (bool). No formulário de novo gasto,
uma checkbox nova (visível junto do bloco "Como será pago?", para os dois tipos de
desembolso) marca o pagamento como já feito — a rota `novo()` grava
`payment_status="pago"` e `paid_at_creation=True` direto na criação. A Planilha de
Pagamentos (`financeiro/routes.py::pagamentos()`) passa a excluir explicitamente
qualquer gasto com `paid_at_creation=True` da query que alimenta os itens do mês — nunca
aparece lá, em nenhuma situação. A distinção de `payment_status="pago"` normal (que
continua aparecendo na planilha como histórico) fica só nesse flag novo.

## Technical Context

**Stack**: o existente. **Storage**: 1 coluna nova em `special_expenses`.

**Arquivos**:
- `app/models.py` — `SpecialExpense.paid_at_creation`.
- `migrations/versions/<novo>_special_expense_paid_at_creation.py`.
- `app/gastos/routes.py::novo()` — lê a checkbox, só grava quando há `disbursement_type`.
- `app/templates/gastos/index.html` — checkbox nova no formulário (mostrada junto dos
  dois blocos de desembolso via `toggleDisb()`); badge "Pago (direto)" na lista quando
  `paid_at_creation`.
- `app/financeiro/routes.py::pagamentos()` — filtro da query de `expenses` ganha
  `SpecialExpense.paid_at_creation.is_(False)`.

**Testing**: verificação funcional vs `manto_local` — registrar gasto com "já pago"
marcado, aprovar, confirmar ausência na planilha do mês; registrar gasto normal
(sem marcar), aprovar, confirmar presença na planilha (garante que não quebrou o caso
existente); balanço financeiro soma os dois igual.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Usa o `payment_status="pago"` já existente para o badge (não cria um estado novo de status) — só o flag `paid_at_creation` é novo, e serve puramente para a exclusão da planilha e a distinção visual. |
| II. Padrões Python | ✅ Migration manual, type hints/docstring na coluna nova, sem strings mágicas fora do já padronizado (`payment_status` já é string livre no projeto). |
| IV. Não quebrar | ✅ Gastos existentes (`paid_at_creation` nulo/False por padrão) continuam se comportando exatamente como hoje — a mudança na query da planilha é aditiva (exclui só quem tem a flag `True`, nunca existente antes desta feature). Aprovação, balanço e custo de evento continuam calculados pelos mesmos campos de sempre (`status`, `amount`, `expense_date`, `event_id`) — nenhum desses muda. |
| V. UI/UX | ✅ Badge deixa claro visualmente por que o gasto não está na planilha (FR-004); checkbox nova segue o mesmo padrão visual dos demais campos do formulário. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A — não mexe em formatação de valor. |

**Gate: PASS.**

## Decisões

1. **Flag novo (`paid_at_creation`) em vez de um valor extra de `payment_status`**:
   `payment_status="pago"` já significa "pago" para tudo que passa pela planilha
   (inclusive o histórico de itens já pagos por lá) — reaproveitar esse mesmo valor para
   o badge mantém uma única fonte de "isso está pago", e o flag novo é só o critério de
   inclusão/exclusão da planilha, sem duplicar semântica de status.
2. **Sem edição posterior**: não existe tela de editar gasto hoje; corrigir uma marcação
   errada de "já pago" segue excluir + recriar, mesmo caminho já usado para qualquer
   outro erro de cadastro (Assumption do spec).
