# Modelo de dados — 353

Migration à mão `f353a1b2c3d4_gasto_parcelas.py`, `down_revision = "f352a1b2c3d4"` (a 353 sai da branch da 352).

## `gasto_parcelas` (nova — model `GastoParcela`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `special_expense_id` | Integer FK `special_expenses.id` **ON DELETE CASCADE**, NOT NULL, índice | a parcela só existe com o gasto |
| `numero` | Integer NOT NULL | 1..N na ordem da data (empate: a ordem em que veio); renumerada a cada gravação |
| `data` | Date NOT NULL | quando sai na Planilha de Pagamentos |
| `valor` | Numeric(10,2) NOT NULL, `> 0` | mesma precisão de `special_expenses.amount` |
| `payment_status` | String(20) NOT NULL default `nao_pago` | `nao_pago` \| `no_banco` \| `pago` — os mesmos valores do gasto |
| `created_at` / `updated_at` | DateTime NOT NULL | UTC |

Restrições: `UNIQUE(special_expense_id, numero)`; `CHECK (valor > 0)`.

Relação: `SpecialExpense.parcelas` (`order_by=numero`, `cascade="all, delete-orphan"`), `lazy="selectin"` para a lista
não virar N+1.

## `special_expenses` (existente) — sem coluna nova

- **Parcelado** = tem parcelas (`len(parcelas) >= 2`). Não há flag: a existência das parcelas é a verdade.
- `amount` = soma das parcelas (gravado pelo núcleo a cada gravação).
- `expense_date` = competência (DRE e custo do evento), inalterado.
- `payment_status` do gasto parcelado = derivado das parcelas, regravado sempre que uma parcela muda: `pago` se todas
  pagas; `no_banco` se nenhuma `nao_pago` e alguma `no_banco`; senão `nao_pago`. Quem já lê o campo (auditor, relatórios)
  continua certo.

## Invariantes

1. Gasto com parcelas ⇒ 2 ≤ N ≤ 24, `disbursement_type ∈ {reembolso, fornecedor}`, `paid_at_creation = false`.
2. `amount = Σ valor` das parcelas.
3. Parcela `pago`/`no_banco` não muda `data` nem `valor` e não é removida pela edição do gasto.
4. Na Planilha, o gasto parcelado nunca aparece como item do gasto inteiro — só as parcelas.

## Downgrade

Derruba `gasto_parcelas`. O `amount` dos gastos parcelados fica com a soma (correto), mas a Planilha volta a mostrá-los
inteiros na `expense_date`.
