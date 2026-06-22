# Research: Corrigir adiantamento de salário + máscara (068)

Diagnóstico e decisões. Sem migration.

## 1. Causa raiz (confirmada)

- `financeiro/routes.py::_ensure_salary_payments(year, month)` é chamado no GET de
  `/financeiro/pagamentos`. Ele **apaga** os `SalaryPayment` `nao_pago` do mês
  (`.filter(month_ref==, payment_status=="nao_pago").delete()`) e recria a partir do salário
  vigente.
- A rota `salary_advance` salva `advance_amount` e **redireciona** para a tela de pagamentos →
  `_ensure_salary_payments` **apaga o lançamento recém-editado** (estava `nao_pago`) e recria sem
  adiantamento. Resultado: "salvo" verdadeiro, mas adiantamento perdido no reload (DB de produção
  confirmou 0 adiantamentos).

## 2. Fix — preservar lançamentos com adiantamento

- **Decisão**: no `_ensure_salary_payments`, o `delete()` dos não pagos passa a **excluir** os que
  têm `advance_amount IS NOT NULL`:
  ```
  .filter(month_ref==, payment_status=="nao_pago", SalaryPayment.advance_amount.is_(None)).delete()
  ```
  Assim, lançamentos com adiantamento não são apagados; como já existem, a recriação (que checa
  `exists` por user/due_date) não os duplica → adiantamento preservado.
- **Rationale**: mínimo e seguro; preserva a regeneração para salários sem adiantamento (FR-005).
  Trade-off aceito: se o salário mudou e há adiantamento, o valor do lançamento preservado não é
  atualizado (integridade do adiantamento > refresh do valor) — caso raro.

## 3. Máscara BR no campo

- **Decisão**: restaurar a máscara padrão no input de adiantamento (classe `brl-input`,
  feature 059) e voltar a normalizar no open (`MoneyMask.applyMask`). O backend já lê com
  `parse_brl` (aceita o formato mascarado). Placeholder "0,00".
- **Rationale**: pedido do cliente (padrão do site). O bug nunca foi a máscara — era a regeneração.

## 4. Verificação (fluxo completo — essencial)

- Reproduzir o ciclo real: salvar adiantamento via rota → **GET /financeiro/pagamentos** (dispara
  `_ensure_salary_payments`) → conferir que o adiantamento **persiste** e o item mostra o líquido.
  (O teste da 067 falhou em pegar isso por não recarregar a tela.)

## 5. Sem modelo/migration

- Colunas `advance_amount`/`advance_proof` já existem (067).
