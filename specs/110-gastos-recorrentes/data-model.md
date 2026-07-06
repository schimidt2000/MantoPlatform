# Data Model — Gastos Recorrentes (110)

## `recurring_expenses` (cadastro)

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| name | String(200) NOT NULL | ex.: "Conta de Luz" |
| expense_type | String(20) NOT NULL | "variavel" \| "debito_automatico" \| "assinatura" |
| amount | Numeric(10,2) NULL | valor fixo (débito automático/assinatura) |
| amount_min | Numeric(10,2) NULL | faixa esperada (variável) |
| amount_max | Numeric(10,2) NULL | faixa esperada (variável) |
| due_day | Integer NOT NULL | dia esperado (variável) / dia do débito/cobrança (1–31; clampado no mês) |
| default_pix | String(120) NULL | PIX padrão (pré-preenche o formulário do mês) |
| card_name | String(100) NULL | cartão (assinaturas) |
| notes | Text NULL | |
| is_active | Boolean NOT NULL default true | inativa não gera alerta/lançamento |
| created_by_id | Integer FK users NOT NULL | |
| created_at | DateTime NOT NULL | |

## `recurring_expense_entries` (lançamento mensal)

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| recurring_id | Integer FK recurring_expenses NOT NULL | ON DELETE via app (excluir conta só sem lançamentos) |
| month_ref | String(7) NOT NULL | "YYYY-MM"; UNIQUE (recurring_id, month_ref) |
| amount | Numeric(10,2) NULL | NULL só em "pulado" |
| pix | String(120) NULL | PIX do boleto do mês |
| due_date | Date NULL | vencimento informado (data do item na planilha) |
| status | String(20) NOT NULL | "a_pagar" \| "pago" \| "registrado" \| "pulado" |
| filled_by_id | Integer FK users NULL | quem preencheu/pulou |
| filled_at | DateTime NULL | |
| paid_at | Date NULL | |
| created_at | DateTime NOT NULL | |

Índices: `(recurring_id, month_ref)` unique; `month_ref`; `status`.

## Máquina de estados (por conta/mês)

```text
VARIÁVEL:  (sem linha = aguardando valor; alerta a partir do due_day)
    preencher(valor, pix, venc.) → a_pagar  → pagar → pago
    pular mês                   → pulado   (sem valor; encerra alerta)
    reabrir (a_pagar → excluir lançamento) → volta a "aguardando"

FIXO (débito automático / assinatura):
    ensure_recurring_entries(mês) → registrado   (automático, nunca pendência)
```

## Regras derivadas

- Alerta home (variável ativa): `today.day >= min(due_day, último dia do mês)` e lançamento
  do mês ausente ("aguardando valor") ou `a_pagar` ("a pagar").
- Fora da faixa: `amount < amount_min or amount > amount_max` (quando faixa definida) —
  só destaque visual.
- Balanço do período: soma de `amount` dos lançamentos com `month_ref` entre o mês de
  início e o de fim do período e `status != 'pulado'`.

## Migration (manual — autogenerate quebrado)

`f6a7b8c9d0e1_recurring_expenses.py`, `down_revision = "e5f6a7b8c9d0"`:
`op.create_table("recurring_expenses", ...)` + `op.create_table("recurring_expense_entries",
...)` com unique constraint e índices acima. Downgrade: drop nas duas (entries primeiro).
Revision id verificado como único em `migrations/versions/`.
