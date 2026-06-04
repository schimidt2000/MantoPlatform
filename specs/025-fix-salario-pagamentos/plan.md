# Implementation Plan: Corrigir salário desatualizado nos Pagamentos

**Branch**: `025-fix-salario-pagamentos` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Corrigir `_ensure_salary_payments`: hoje só **cria** lançamentos de salário (`if not exists`),
nunca atualiza — por isso o valor antigo persiste. Passar a **recompor os lançamentos NÃO pagos** do
mês a partir do salário vigente (apagar os não pagos e recriar do histórico atual), **preservando**
os já pagos / "no banco". Isso corrige valor, frequência (semanal/quinzenal) e quem virou só
comissão. Sem migration.

## Constitution Check
- **IV. Não quebrar** ✅ — pagos preservados; recomposição idempotente a cada carga; verificação no
  app. Sem migration.
- **V. UI/UX** ✅ — Pagamentos passa a refletir o salário atual sem ação manual.
- **VI. Planejar antes de codar** ✅ — causa raiz identificada; correção mínima e direcionada.

## Project Structure

```text
app/financeiro/routes.py   # _ensure_salary_payments(): recompor lançamentos não pagos do mês
```

## Design Detalhado

### Causa raiz
`_ensure_salary_payments` faz `exists = SalaryPayment.query.filter_by(user_id, due_date).first()` e
`if not exists: add(...)`. Se existe (criado com salário antigo), nunca é atualizado → valor velho.

### Correção
No início (após calcular `month_ref`/datas do mês):
1. **Apagar** os `SalaryPayment` do mês com `payment_status == "nao_pago"` (serão recriados do salário
   vigente). Pagos / "no banco" são preservados.
2. Recriar a partir das histories vigentes (lógica atual de `user_history` + due_dates), mas pulando
   uma data se já houver um lançamento **pago** ali (respeita a constraint `user_id+due_date` e o
   histórico real).

Pseudocódigo:
```text
SalaryPayment.query.filter(month_ref==ref, payment_status=="nao_pago").delete()
for user_id, history in user_history.items():
    due_dates = (semanal→segundas | quinzenal→[5,20] | comissao→[])
    for due in due_dates:
        if SalaryPayment com (user_id, due) já existe (pago/no_banco): continue
        add SalaryPayment(amount=history.salary, salary_history_id=history.id, due, nao_pago, ref)
commit
```
- Quem não tem history vigente (ou virou comissão) não recria nada → some dos não pagos.

### Verificação (app real)
- Criar salário X; abrir Pagamentos (gera lançamento). Atualizar salário p/ Y; abrir Pagamentos →
  lançamento não pago passa a Y.
- Marcar um lançamento como pago; atualizar salário → o pago mantém o valor; os não pagos atualizam.
- Trocar quinzenal→semanal → datas não pagas ajustam; sem órfãos/duplicados.

### Fora de escopo
- Histórico de observações em lançamentos não pagos (podem ser recompostos). Sem migration.
