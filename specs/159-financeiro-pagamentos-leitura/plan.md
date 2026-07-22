# Implementation Plan: Planilha de Pagamentos em React (Leitura) (159)

**Branch**: `159-financeiro-pagamentos-leitura` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/159-financeiro-pagamentos-leitura/spec.md`

## Summary

Quarta e última fatia de LEITURA da US4 (Financeiro/Vendas), depois do Pipeline de Vendas (156),
Dashboard Financeiro DRE (157) e Comissões (158). Migra a tela `/financeiro/pagamentos` para
React, reaproveitando 100% da lógica já existente em `app/financeiro/routes.py`
(`_pagamentos_query`, `_ensure_salary_payments`, `_build_payment_items`, `_build_bv_items`,
`_build_commission_items`, `_build_recurring_items`, `_resync_pending_commissions`) — o endpoint
novo só monta os mesmos itens do mês e serializa. Com esta fatia, a US4 fica completa em leitura;
toda escrita (marcar status, ações em massa, adiantamento, exportação) fica para uma fatia de
escrita futura.

## Technical Context

Igual à 144-158: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: núcleo reaproveita `_pagamentos_query`/`_ensure_salary_payments`/
  `_build_payment_items`/`_build_bv_items`/`_build_commission_items`/`_build_recurring_items`/
  `_resync_pending_commissions`, já existentes e puros o bastante para reuso (mesma exceção
  "core-in-routes" da 156/157/158 — helpers multi-uso dentro do blueprint, sem extrair `_ops` novo
  só para esta fatia).
- **II (padrões de código)**: endpoint novo em `app/api/financeiro_read.py` (arquivo já existe),
  type hints/docstring; sem lógica de negócio nova, só serialização (inclusive a sub-lista de
  adiantamentos, que é re-lida de `SalaryAdvance` como números — não reaproveita a string BRL
  pré-formatada que `_build_payment_items` monta para o template Jinja, ver Design Decisions).
- **III (API first)**: 1 endpoint novo, 100% JSON (`GET /api/financeiro/pagamentos`); a view Jinja
  `/financeiro/pagamentos` continua existindo em paralelo, sem mudança de comportamento (FR-008).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos itens/totais para o
  mesmo mês, comparados campo a campo com a view antiga.
- **V (feedback)**: estado vazio amigável quando não há itens no mês; 403 tratado pelo
  interceptor padrão do cliente API (mesmo comportamento de toda tela já migrada); troca de mês
  com loading visível (skeleton).
- **VII (monetário)**: valores formatados com `formatBRL`/`@manto/money` no frontend — a API
  devolve números (Decimal→float) em todos os campos monetários, inclusive nos adiantamentos
  (ver Design Decisions, ponto 2) — nunca string formatada, ao contrário do que a função
  `_build_payment_items` monta hoje para o template Jinja.
- **VIII (mobile-first)**: lista de itens de pagamento empilha em coluna única <768px, mesmo
  padrão da 156/157/158 (não é superfície pública, mas segue mobile-first por princípio geral de
  UI).
- **IX (movimento)**: sem transição nova; troca de mês usa o loading padrão do TanStack Query.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/159-financeiro-pagamentos-leitura/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/financeiro-pagamentos-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/financeiro_read.py          # + GET /api/financeiro/pagamentos (arquivo já existe)
frontend/apps/internal/src/
├── lib/financeiro.ts               # + usePagamentos(month) (arquivo já existe)
├── pages/PagamentosPage.tsx         # NOVO — filtro de mês + lista de itens + 5 totais
App.tsx                              # + rota /financeiro/pagamentos
scripts/db/verify_159_financeiro_pagamentos.py  # NOVO: paridade API×Jinja + RBAC 403
```

**Structure Decision**: núcleo permanece em `app/financeiro/routes.py` (funções já puras e
multi-uso, mesma exceção da 156/157/158) — só o endpoint de leitura é novo (mais uma rota em
`app/api/financeiro_read.py`, ao lado de `api_vendas_pipeline`/`api_financeiro_dashboard`/
`api_financeiro_comissoes`).

## Design Decisions

1. **`GET /api/financeiro/pagamentos`** (`app/api/financeiro_read.py`, gate:
   `_has_role(FINANCEIRO, SUPERADMIN)` — paridade exata com `require_financeiro`, sem exceção de
   responsável EducaManto nem recorte por vendedor, diferente de comissões/pipeline):
   - Parâmetro de querystring idêntico ao da view hoje: `month` (`YYYY-MM`, default mês corrente,
     mesmo fallback de `pagamentos()` para valor inválido).
   - Chama `_resync_pending_commissions()` e `_ensure_salary_payments(year, month)` antes de
     montar a lista — mesmo comportamento de hoje (gera lançamentos de salário do mês se ainda não
     existirem).
   - Monta a mesma combinação de itens que a view hoje: cachês (`_pagamentos_query` +
     `_build_payment_items` com `SalaryPayment`s do mês e `SpecialExpense`s aprovados/não pagos na
     criação), repasses de BV (`_build_bv_items`), comissões do ciclo do mês anterior
     (`_build_commission_items`), contas recorrentes (`_build_recurring_items` após
     `ensure_recurring_entries`) — ordenados por data, exatamente como a view.
   - Serializa cada item com um serializer novo (`_serialize_pagamento_item`): campos comuns
     (tipo, data ISO, favorecido, evento, valor float, chave PIX, status, `is_future`) mais campos
     específicos por tipo — `gross_amount`/`advance_amount`/`advances` para salário, `missing_data`
     para BV.
   - Serializa os 5 totais do mês (`total`, `pago`, `no_banco`, `pendente`, `futuro`) com a mesma
     regra de `pagamentos()` — `Decimal`→`float` na resposta.
2. **Adiantamentos re-serializados a partir de `SalaryAdvance`, não da string pré-formatada**:
   `_build_payment_items` monta hoje `item["advances"]` com `amount` já formatado em BRL (string),
   porque essa lista alimenta diretamente o template Jinja. Para a API, o serializer novo
   re-consulta `SalaryAdvance.query.filter_by(salary_payment_id=item["id"])` e monta
   `{id, amount: float, date: isoformat, proof}` — mesma fonte de dado (`SalaryAdvance`), zero
   regra de negócio nova (é só uma leitura direta, sem cálculo), só evita propagar string
   formatada pela API (Princípio VII).
3. **Frontend — página nova**: `PagamentosPage.tsx`, com o seletor de mês (mesmo formato
   `YYYY-MM` da tela antiga); lista única de itens (com badge de tipo: cachê/salário/BV/comissão/
   recorrente), badge de status, indicador de "futuro"/"dados pendentes" (BV sem PIX), e os 5
   totais do mês em destaque. Sem ações de escrita nesta fatia (sem marcar status, sem
   adiantamento, sem exportação) — mesma regra da 157/158 para as ações que ficaram de fora.
4. **Sem alteração em `require_financeiro`/helpers do Jinja**: o endpoint novo reimplementa o
   gate como função (`_has_role(FINANCEIRO, SUPERADMIN)`, já usado assim no dashboard da 157) —
   paridade por comportamento, verificada pelo script.

## Complexity Tracking

Nenhuma violação nova.
