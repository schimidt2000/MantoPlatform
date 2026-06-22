# Research: Adiantamento de salário com comprovante (067)

Decisões técnicas. Sem `NEEDS CLARIFICATION`. Migration manual.

## 1. Estado atual

- `SalaryPayment` (models.py): item de salário por pessoa/`due_date`, `amount` (Numeric),
  `payment_status`, `paid_at`, `month_ref`. É o que aparece na tela de pagamentos como
  `type="salary"` (`_build_payment_items`).
- Pagamentos: `financeiro/routes.py` — `_build_payment_items` monta os itens; ação individual
  (marcar pago) trata `item_type == "salary"`; ação em lote idem. Acesso `require_financeiro`.
- Uploads: `app.config["UPLOAD_PAYMENTS"]` (`instance/uploads/payments`), servidos via
  `/uploads/payments/<arquivo>`. Há `parse_brl` (máscara BR) e `audit`.
- Migration head: **`t6c7d8e9f0a1`**.

## 2. Modelo — adiantamento no próprio salário

- **Decisão**: adicionar a `SalaryPayment`:
  - `advance_amount` Numeric(12,2) nullable — valor já pago antecipadamente.
  - `advance_proof` String(300) nullable — caminho do comprovante (`/uploads/payments/...`).
- **Rationale**: o adiantamento pertence ao salário que será pago; um valor acumulado + um
  comprovante (substituível). Migration manual (autogenerate quebrado).

## 3. Líquido a pagar (sem mudar custo)

- **Decisão**: em `_build_payment_items`, o item de salário passa a ter
  `amount = sp.amount - (sp.advance_amount or 0)` (líquido) e expõe `gross_amount`,
  `advance_amount`, `advance_proof` para a UI.
- **Importante**: `_salary_cost` (DRE) continua somando `SalaryPayment.amount` (cheio) — **não
  alterar**. O adiantamento é caixa, não custo (FR-008).

## 4. Rota de edição do adiantamento

- **Decisão**: `POST /financeiro/pagamentos/salary/<int:sp_id>/advance` (`require_financeiro`):
  lê `advance_amount` (`parse_brl`) e o arquivo `advance_proof`.
  - `advance > sp.amount` → erro (não excede o salário).
  - `advance > 0` e sem comprovante novo **nem** existente → erro (comprovante obrigatório).
  - `advance == 0`/vazio → zera `advance_amount` e dispensa comprovante (mantém ou limpa o
    arquivo; mantemos o arquivo antigo sem exibir, simplicidade).
  - Salva, `audit("payment","salary_payment",...,"Adiantamento R$X")`, redireciona à tela de
    pagamentos (mantendo o mês).
- **Rationale**: rota dedicada multipart; reusa `parse_brl`, `UPLOAD_PAYMENTS`, `audit`.

## 5. UI — editar salário

- **Decisão**: na linha de salário (`pagamentos.html`), botão **"Editar"** que abre um **modal
  único** preenchido por `data-*` da linha (id, pessoa, salário cheio, adiantamento atual, link do
  comprovante). O form do modal (multipart) posta na rota acima. A linha mostra o **líquido** e,
  se houver adiantamento, uma nota "(adiantado R$X)".
- **Rationale**: um modal reutilizável evita repetir markup por linha; `brl-input` no valor.

## 6. Migration

- Nova revisão `u7d8e9f0a1b2` (down_revision `t6c7d8e9f0a1`): add `advance_amount`,
  `advance_proof` em `salary_payments`. Aplicar `flask db upgrade` no `manto_local`.
