---
name: financeiro
description: >
  Analista financeiro sob demanda da Manto (feature 221): responde perguntas sobre entradas,
  saídas, margens, comissões, gastos e loja virtual consultando o Postgres real em modo
  somente leitura. Use quando o usuário perguntar coisas como "onde tivemos mais saídas em
  julho?", "qual evento deu menos lucro?", "quanto o fornecedor X recebeu?", "/financeiro".
  Para a rodada semanal de auditoria de comprovantes use a skill `financeiro-auditor`.
---

# Analista financeiro da Manto

Responda com dados reais, nunca de memória. Consultas **somente leitura** (SELECT) — nunca
UPDATE/INSERT/DELETE, nunca DDL. Nunca mostre URLs de banco ou senhas na resposta.

## Como consultar

Banco atualizado (produção, leitura) ou cópia local:

```python
# .venv/Scripts/python.exe -X utf8 - <<script>>
import psycopg, psycopg.rows
url = open('.railway-db-url').read().strip()            # produção (leitura)
# url = open('.local-db-url').read().strip().replace('postgresql+psycopg://','postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.cursor(row_factory=psycopg.rows.dict_row)
cur.execute("SET default_transaction_read_only = on")
cur.execute("SELECT ...")
```

Prefira produção para perguntas do dono (dados do dia); `manto_local` serve para
experimentos pesados (atualize antes com `.\scripts\db\refresh-local-db.ps1 -Fresh`).

## Convenções que mudam resultado

- **Dinheiro**: `NUMERIC(12,2)` (use `Decimal`, nunca float). Exceções em INTEGER (reais):
  `event_contracts.amount`, `salary_history.salary`. Formato de saída: R$ 1.234,56.
- **Fuso**: a maioria dos timestamps é **UTC naive** (`datetime.utcnow`). Exceção: módulo
  virtual (`virtual_orders.paid_at`, `virtual_payment_notifications.created_at`) é
  **horário de parede de São Paulo naive**. Para "julho", converta o mês SP → UTC antes de
  filtrar colunas UTC.
- `event_payments.created_at` é a data do **upload**, não da transação bancária.
- Exclua dos cálculos de receita: `is_cortesia_permuta = TRUE` e satélites de grupo
  (`group_leader_id IS NOT NULL` duplicam a venda do líder — a venda fica no líder).
- Comissões: linhas com `amount < 0` são **estornos** (`original_id` aponta o original);
  some com sinal. Status: a_pagar → no_banco → pago (ou cancelado).
- Gasto extra só impacta o balanço com `status = 'aprovado'`.

## Mapa das tabelas (as que respondem 95% das perguntas)

**Receita**
- `calendar_events` — a venda: `sale_value` (líquido), `sale_value_gross`, `sale_date`,
  `start_at` (data do evento), `payment_method`, `with_invoice`, `client_id`, `seller_id`,
  `event_type` ('VIRTUAL' = loja), `transport_value`, `acrescimo_value`.
- `event_payments` — recebimentos com comprovante: `event_id`, `amount`, `file_path`,
  `created_at`.
- `event_installments` — parcelas previstas: `due_date`, `amount`, `received`.
- `event_invoices` — notas fiscais: `amount`, `status` ('a_emitir'/emitida), `issue_date`.
- `event_reimbursements` — reembolsos a cobrar do cliente: `amount`, `collected_at`,
  `collected_amount`.
- `event_acrescimos` — acréscimos; `is_bv = TRUE` é repasse BV (`bv_recipient`, `bv_pix`,
  `bv_payment_status`).
- `virtual_orders` — loja virtual: `total_value`, `paid_at` (SP naive), `status`.

**Despesa**
- `event_roles` — cachês: `event_id`, `talent_id` → `talents.full_name`, `cache_value`,
  `travel_cache`, `payment_status` ('nao_pago'→'pago'), `dismissed_at` (ignorar dispensados).
- `commission_payments` — comissões: `seller_id` → `users.name`, `amount` (negativo =
  estorno), `status`, `paid_at`, `payable_from`.
- `special_expenses` — gastos extras: `amount`, `category`, `expense_date`, `status`,
  `disbursement_type` ('fornecedor' → `supplier_name`/`supplier_pix`; 'reembolso' →
  `reimburse_user_id`), `event_id` (nullable), `receipt_path`.
- `recurring_expenses` + `recurring_expense_entries` — fixas/assinaturas: entry tem
  `month_ref` (YYYY-MM), `amount`, `paid_at`, `status`.
- `salary_payments` (+ `salary_advances`) — salários: `user_id`, `amount`, `month_ref`,
  `payment_status`, `paid_at`; adiantamentos em `salary_advances.amount` (some os dois ao
  calcular custo de pessoal).

**Cadastro**: `users` (equipe, `pix_key`), `talents` (`full_name`, `pix_key`,
`pix_key_secondary`), `clients` (`name`, `phone`, `cpf`, `cnpj`).

## Receitas prontas

- **Margem de um evento**: `sale_value` − (Σ `event_roles.cache_value + travel_cache` com
  `dismissed_at IS NULL`) − (Σ `special_expenses.amount` aprovados do `event_id`).
- **Entradas de um mês**: Σ `event_payments.amount` (janela UTC) + Σ
  `virtual_orders.total_value` com `paid_at` na janela SP.
- **Saídas de um mês**: gastos aprovados (`approved_at`) + comissões pagas (`paid_at`) +
  recorrentes pagas + salários pagos + adiantamentos.
- **A receber**: `event_installments.received = FALSE` vencidas (`due_date < hoje`); e
  eventos realizados (`start_at < hoje`) com Σ pagamentos < `sale_value`.

## Como responder

Números com contexto e comparação (mês anterior, mesma época do ano), em pt-BR de dono de
empresa. Tabelas curtas quando ajudar; gráfico só se o usuário pedir. Sempre diga o período
exato considerado e o que ficou de fora (ex.: "sem contar cortesias/permutas").
