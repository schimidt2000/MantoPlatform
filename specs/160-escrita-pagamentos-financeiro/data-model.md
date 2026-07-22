# Data Model: Escrita da Planilha de Pagamentos em React (160)

Nenhuma tabela/campo novo — reaproveita entidades já existentes (mesmas da 159). Esta fatia só
adiciona rotas de escrita sobre elas.

## Entidades escritas (já existentes)

| Entidade               | Escrita nesta fatia                                                              |
|-------------------------|-----------------------------------------------------------------------------------|
| `EventRole`              | `payment_status` (marcar status individual/em massa); exclusão em massa          |
| `SalaryPayment`          | `payment_status`, `paid_at` (marcar status individual/em massa)                  |
| `SalaryAdvance`          | criação (`salary_advance`) e exclusão (`salary_advance_delete`), com arquivo     |
| `SpecialExpense`         | `payment_status` (marcar status individual/em massa)                             |
| `EventAcrescimo`         | `bv_payment_status` (marcar status individual, só BV)                            |
| `CommissionPayment`      | `status`, `paid_at`, em lote por vendedor/período (marcar status individual/massa)|

## Regras de validação reaproveitadas (sem duplicar, ver `app/financeiro/routes.py`)

- **Status válido por tipo**: `nao_pago`/`pago`/`no_banco` para cachê/salário/gasto/BV;
  `recurring` e `commission` só aceitam `pago`/`nao_pago` (sem "no banco").
- **Adiantamento de salário**: valor > 0; soma de todos os adiantamentos do lançamento não pode
  ultrapassar `SalaryPayment.amount`; comprovante obrigatório, ≤ 10 MB; data customizável
  (`advance_date`), com fallback para hoje se ausente/inválida.
- **Ação em massa — exclusão**: só `EventRole`/`SalaryPayment` são excluídos; gastos e comissões
  selecionados são ignorados (pertencem a outros módulos) e reportados como `skipped`.
- **Ação em massa — status**: comissões não aceitam `no_banco` em lote (mesma regra do individual);
  reportadas como `skipped` quando essa combinação ocorre.
- **Auditoria**: toda mudança grava uma entrada via `app.utils.audit(...)`, mesma chamada e mesmo
  texto da rota Jinja equivalente — nenhuma trilha nova nem perdida.

## Resposta do export (sem mudança de forma, só de transporte)

- CSV com colunas `Data, Evento, Função, Nome, Valor, Pix, Situação`, uma linha por `EventRole` do
  mês (`_pagamentos_query(month)`), idêntico ao `export_pagamentos()` de hoje.
