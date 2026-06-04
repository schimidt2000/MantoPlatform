# Tasks: Corrigir salário desatualizado nos Pagamentos

**Input**: `specs/025-fix-salario-pagamentos/`
**Tests**: boot + ruff + verificação no app real.

## Phase 1: Correção
- [ ] T001 financeiro/routes.py `_ensure_salary_payments`: apagar lançamentos do mês com
      `payment_status == "nao_pago"` e recriá-los a partir do salário vigente; ao recriar, pular
      datas que já tenham um lançamento pago/no_banco (preserva histórico + constraint).

## Phase 2: Verificação
- [ ] T002 boot + ruff; cenários no app real:
      (a) atualizar salário → lançamento não pago reflete o novo valor;
      (b) lançamento pago não muda após atualização;
      (c) troca de frequência ajusta datas sem órfãos/duplicados.

## Dependencies
- T001 → T002.

## Notes
- Sem migration. Recomposição roda ao abrir Pagamentos. Pagos/"no banco" preservados.
