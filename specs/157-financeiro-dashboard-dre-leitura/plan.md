# Implementation Plan: Dashboard Financeiro (DRE) em React (Leitura) (157)

**Branch**: `157-financeiro-dashboard-dre-leitura` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/157-financeiro-dashboard-dre-leitura/spec.md`

## Summary

Segunda fatia da US4 (Financeiro/Vendas), depois do Pipeline de Vendas (156). Migra o painel
gerencial `/financeiro/` (DRE realizado/projetado/total, KPIs, painéis laterais, tendência
mensal, auditoria, tabela de eventos e pendências de recebimento/notas) para React, reaproveitando
100% dos cálculos já existentes em `app/financeiro/routes.py` (`_resolve_period`, `_compute_drg`,
`_salary_cost`, `_group_cost`, `_event_cost`, `_event_commission`, `_get_commission_rate`,
`_is_permuta`, `_pct`, `_get_fator_r_threshold`, `_get_tax_rate`, `_month_range`, `_prev_month`,
`_month_refs_between`) — o endpoint novo só monta a query do período e serializa. Planilha de
pagamentos (`/financeiro/pagamentos`), cadastro de funcionário/salário (`/financeiro/
funcionarios`) e comissões (`/financeiro/comissoes`) ficam para fatias futuras — cada uma grande e
sensível o bastante para seu próprio `/speckit-plan`.

## Technical Context

Igual à 144-156: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: núcleo reaproveita `_resolve_period`/`_compute_drg`/`_salary_cost`/
  `_group_cost`/`_event_cost`/`_event_commission`/`_get_commission_rate`/`_is_permuta`/`_pct`/
  `_get_fator_r_threshold`/`_get_tax_rate`/`_month_range`/`_prev_month`/`_month_refs_between`,
  todos já existentes e puros (sem `request`/`flash`, exceto `_resolve_period` que só lê
  `request.args` — mesmo padrão hoje) em `app/financeiro/routes.py` — mesma exceção
  "core-in-routes" da 156 (helpers multi-uso dentro do blueprint, sem extrair `_ops` novo só
  para esta fatia).
- **II (padrões de código)**: endpoint novo em `app/api/financeiro_read.py` (arquivo já existe,
  criado na 156), type hints/docstring; sem lógica de negócio nova, só serialização e composição
  do payload.
- **III (API first)**: 1 endpoint novo, 100% JSON (`GET /api/financeiro/dashboard`); a view Jinja
  `/financeiro/` continua existindo em paralelo, sem mudança de comportamento (FR-009).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos valores de DRE/KPIs/
  painéis/tabela para o mesmo período, nos dois caminhos.
- **V (feedback)**: estado vazio amigável quando não há eventos no período; 403 tratado pelo
  interceptor padrão do cliente API (mesmo comportamento de toda tela já migrada); troca de
  período com loading visível (skeleton), sem UI "morta".
- **VII (monetário)**: valores formatados com `formatBRL`/`@manto/money` no frontend — a API
  devolve números (Decimal→float, mesma convenção da 156), nunca string formatada.
- **VIII (mobile-first)**: painéis empilham em coluna única <768px; tabela de eventos com scroll
  horizontal dentro do próprio card (mesmo padrão da 156).
- **IX (movimento)**: sem transição nova; troca de período usa o loading padrão do TanStack Query.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/157-financeiro-dashboard-dre-leitura/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/financeiro-dashboard-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/financeiro_read.py          # + GET /api/financeiro/dashboard (arquivo já existe, da 156)
frontend/apps/internal/src/
├── lib/financeiro.ts               # NOVO — useFinanceiroDashboard(period, start?, end?)
├── pages/FinanceiroDashboardPage.tsx  # NOVO — filtro de período + DRE + KPIs + painéis + tabela
App.tsx                              # + rota /financeiro
scripts/db/verify_157_financeiro_dashboard.py  # NOVO: paridade API×Jinja (DRE/KPIs/tabela) + RBAC 403
```

**Structure Decision**: núcleo permanece em `app/financeiro/routes.py` (funções já puras e
multi-uso, mesma exceção da 156) — só o endpoint de leitura é novo (mais uma rota em
`app/api/financeiro_read.py`, que já existe desde a 156, ao lado de `api_vendas_pipeline`).

## Design Decisions

1. **`GET /api/financeiro/dashboard`** (`app/api/financeiro_read.py`, gate: `require_financeiro`
   reimplementado como função — FINANCEIRO/SUPERADMIN, paridade exata com o decorator Jinja):
   - Parâmetros de querystring idênticos aos da view hoje: `period` (`este_mes`|`30d`|
     `mes_anterior`|`custom`, default `este_mes`), `start`/`end` (ISO, só usados quando
     `period=custom`) — resolvidos via `_resolve_period` (mesma função, sem reimplementar).
   - Monta a mesma query de eventos do período (exceto ENSAIO) e reusa `_compute_drg` três vezes
     (realizado/projetado/total) exatamente como a view faz hoje — nenhuma lógica nova de corte
     realizado×projetado (usa `now_naive` em horário de Brasília, mesma regra).
   - Serializa: `dre` (`{realizado, projetado, total}`, cada um o dict retornado por
     `_compute_drg`, com `Decimal`→`float`), `kpis` (`ticket_medio`, `ratio_custo_talento`,
     `breakeven_pct`, `breakeven_atingido`, `fixed_cost`, `fator_r_pct`, `fator_r_threshold`,
     `fator_r_protegido`), `paineis` (`receita_por_tipo`, `top_sellers`, `monthly_trend`,
     `auditoria`, `a_receber_clientes`, `pagamentos_pendentes`, `pagamentos_realizados`),
     `eventos` (tabela do período, mesmos campos de `events_data` hoje), `pendencias`
     (`recebimentos_previstos`, `nf_a_emitir`, `custo_nota_itens` + totais).
   - Resposta inclui `period`/`period_label`/`start`/`end`/`is_full_month` (eco do filtro
     resolvido, para o frontend refletir o estado ativo sem duplicar `_resolve_period` no
     cliente).
2. **Frontend — página nova**: `FinanceiroDashboardPage.tsx`, com os 4 filtros de período como
   toggle/select (mesmo rótulo da tela antiga) + inputs de data quando `custom`; seções: DRE (3
   colunas realizado/projetado/total), tira de KPIs, painéis laterais (grid 2 colunas ≥768px,
   1 coluna abaixo), tabela de eventos (mesmo padrão de scroll horizontal da 156), painel de
   pendências (recebimentos previstos + notas fiscais). Sem link de detalhe por enquanto além do
   já existente `/events/:id` nas linhas da tabela (mesmo padrão da 156).
3. **Sem alteração em `require_financeiro`/helpers do Jinja**: o endpoint novo reimplementa o
   gate (mesma regra: FINANCEIRO/SUPERADMIN), não importa o decorator Flask — paridade por
   comportamento, verificada pelo script.
4. **Query de eventos do período repetida três vezes no Jinja atual (base, realizados,
   projetados) é reaproveitada como está** — não é uma ineficiência introduzida por esta fatia;
   fora de escopo otimizar, para minimizar risco de divergência de resultado.

## Complexity Tracking

Nenhuma violação nova.
