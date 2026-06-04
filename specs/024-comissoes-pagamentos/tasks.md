# Tasks: Resumo de comissões nos Pagamentos (dia 5)

**Input**: `specs/024-comissoes-pagamentos/`
**Tests**: boot + ruff + verificação no app real.

## Phase 1: Backend
- [ ] T001 financeiro/routes.py: `_build_commission_items(period_start, period_end, due_date, today)`
      — soma por vendedor das comissões (a_pagar/pago) com sale_date no período; pula soma zero.
- [ ] T002 financeiro/routes.py `pagamentos()`: calcular mês anterior; incluir as linhas de comissão;
      reordenar por data.
- [ ] T003 financeiro/routes.py `set_payment_status()`: ramo `item_type=="commission"` — parse
      "sellerId:YYYY-MM"; marca as comissões do vendedor/período como pago/a_pagar; audita.

## Phase 2: Template
- [ ] T004 pagamentos.html: omitir o checkbox de seleção quando `item.type == 'commission'`.

## Phase 3: Verificação
- [ ] T005 boot + ruff; criar comissão (venda mês anterior) → linha por vendedor datada dia 5 com
      soma correta; marcar pago sincroniza com Comissões; soma zero não gera linha; bulk não quebra.

## Dependencies
- T001→T002. T003 independente. T004 após T002. T005 ao fim.

## Notes
- Sem migration. Reusa CommissionPayment + tabela genérica de pagamentos + endpoint de status.
