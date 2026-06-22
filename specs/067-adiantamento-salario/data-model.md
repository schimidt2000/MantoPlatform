# Data Model: Adiantamento de salário (067)

## Mudança no modelo (migration manual `u7d8e9f0a1b2`, down_revision `t6c7d8e9f0a1`)

### Colunas novas em `salary_payments`

| Campo | Tipo | Notas |
|---|---|---|
| advance_amount | Numeric(12,2) nullable | valor já pago antecipadamente (R$) |
| advance_proof | String(300) nullable | caminho do comprovante (`/uploads/payments/...`) |

## Regras (derivadas)

```
liquido_a_pagar(salario)   = salario.amount − (salario.advance_amount ou 0)
comprovante_obrigatorio    ⇔ advance_amount > 0
advance_amount             ≤ salario.amount   (senão recusa)
custo_salario_periodo (DRE) = Σ SalaryPayment.amount   (INALTERADO — não desconta adiantamento)
```

## Não altera

- `_salary_cost` / DRE: continua somando `amount` cheio (adiantamento é caixa, não custo).
- Ações de pagamento (marcar pago/no banco/não pago) e demais tipos de item: inalteradas.
- `EventPayment` (comprovante de cachê) e fluxo de salários: inalterados.

## Migração

Manual: `batch_alter_table("salary_payments").add_column(advance_amount)` + `add_column(advance_proof)`.
Downgrade: drop das duas colunas.
