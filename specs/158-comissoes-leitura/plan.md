# Implementation Plan: Comissões em React (Leitura) (158)

**Branch**: `158-comissoes-leitura` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/158-comissoes-leitura/spec.md`

## Summary

Terceira fatia da US4 (Financeiro/Vendas), depois do Pipeline de Vendas (156) e do Dashboard
Financeiro DRE (157). Migra a tela `/financeiro/comissoes` para React, reaproveitando 100% da
lógica já existente em `app/financeiro/routes.py` (`comissoes()`, `_resync_pending_commissions`,
`_COMMISSION_STATUS_LABELS`) — o endpoint novo só monta a query do mês e serializa. Planilha de
pagamentos (`/financeiro/pagamentos`) fica para uma fatia futura, grande e sensível o bastante
para seu próprio `/speckit-plan`. Cadastro de funcionário/salário (`/financeiro/funcionarios`) não
entra mais no escopo da US4 — já é só um redirect para Usuários (feature 022), sem tela própria.

## Technical Context

Igual à 144-157: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: núcleo reaproveita `comissoes()`/`_resync_pending_commissions`/
  `_COMMISSION_STATUS_LABELS`, já existentes e puros o bastante para reuso (mesma exceção
  "core-in-routes" da 156/157 — helpers multi-uso dentro do blueprint, sem extrair `_ops` novo só
  para esta fatia).
- **II (padrões de código)**: endpoint novo em `app/api/financeiro_read.py` (arquivo já existe,
  criado na 156), type hints/docstring; sem lógica de negócio nova, só serialização.
- **III (API first)**: 1 endpoint novo, 100% JSON (`GET /api/financeiro/comissoes`); a view Jinja
  `/financeiro/comissoes` continua existindo em paralelo, sem mudança de comportamento (FR-008).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmas linhas/total/estornos
  para o mesmo mês e mesmo usuário, nos dois caminhos (Financeiro e Comercial).
- **V (feedback)**: estado vazio amigável quando não há comissões no mês; 403 tratado pelo
  interceptor padrão do cliente API (mesmo comportamento de toda tela já migrada); troca de mês
  com loading visível (skeleton).
- **VII (monetário)**: valores formatados com `formatBRL`/`@manto/money` no frontend — a API
  devolve números (Decimal→float, mesma convenção da 156/157), nunca string formatada.
- **VIII (mobile-first)**: lista de comissões empilha em coluna única <768px, mesmo padrão da
  156/157 (não é superfície pública, mas segue mobile-first por princípio geral de UI).
- **IX (movimento)**: sem transição nova; troca de mês usa o loading padrão do TanStack Query.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/158-comissoes-leitura/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/financeiro-comissoes-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/financeiro_read.py          # + GET /api/financeiro/comissoes (arquivo já existe, da 156)
frontend/apps/internal/src/
├── lib/financeiro.ts               # + useComissoes(month) (arquivo já existe, da 157)
├── pages/ComissoesPage.tsx          # NOVO — filtro de mês + lista + estornos + total
App.tsx                              # + rota /financeiro/comissoes
scripts/db/verify_158_financeiro_comissoes.py  # NOVO: paridade API×Jinja (Financeiro e Comercial) + RBAC 403
```

**Structure Decision**: núcleo permanece em `app/financeiro/routes.py` (funções já puras e
multi-uso, mesma exceção da 156/157) — só o endpoint de leitura é novo (mais uma rota em
`app/api/financeiro_read.py`, ao lado de `api_vendas_pipeline` e `api_financeiro_dashboard`).

## Design Decisions

1. **`GET /api/financeiro/comissoes`** (`app/api/financeiro_read.py`, gate: `require_vendas`
   reimplementado como função — COMERCIAL/FINANCEIRO/SUPERADMIN, ou o responsável EducaManto
   configurado independente de papel, paridade exata com o decorator Jinja):
   - Parâmetro de querystring idêntico ao da view hoje: `month` (`YYYY-MM`, default mês corrente,
     mesmo fallback de `comissoes()` para valor inválido).
   - Chama `_resync_pending_commissions()` antes de montar a query — mesmo comportamento de hoje.
   - Monta a mesma query de `CommissionPayment` do mês (status `a_pagar`/`pago`, por `sale_date`
     ou, na ausência, por `created_at`) e a de estornos pendentes (`status="a_pagar"`,
     `amount < 0`), ambas restritas a `seller_id=current_user.id` quando o usuário não é
     Financeiro/Superadmin — mesma regra de `can_manage` da view.
   - Serializa: `entries` (lista de `{id, seller_name, event_title, sale_date, amount, status,
     paid_at}`), `estornos` (mesma forma), `total_a_pagar` (float), `can_manage` (bool), `month`
     (eco do filtro resolvido), `sellers` (lista `{id, name}`, só quando `can_manage`).
2. **Frontend — página nova**: `ComissoesPage.tsx`, com o seletor de mês (mesmo formato
   `YYYY-MM` da tela antiga); seções: total a pagar do mês, tabela de comissões (vendedor, evento,
   data da venda, valor, status, data de pagamento), tabela de estornos pendentes (quando houver).
   Sem ações de escrita nesta fatia (sem botão de marcar pago) — mesma regra da 157 para nf_emitir.
3. **Sem alteração em `require_vendas`/helpers do Jinja**: o endpoint novo reimplementa o gate
   (mesma regra exata de `require_vendas`: `_has_role(COMERCIAL, FINANCEIRO, SUPERADMIN)` OU
   `_is_educamanto_responsavel()` — já existe como `_can_view_vendas` em `financeiro_read.py`,
   reusada sem duplicar, mesma função usada pelo pipeline na 156), não importa o decorator Flask —
   paridade por comportamento, verificada pelo script.
4. **Não existe papel `VENDAS`** no sistema (`RoleName` só tem SUPERADMIN/CASTING/FIGURINO/
   COMERCIAL/FINANCEIRO/ENSAIO/REVENDEDOR_EDUCAMANTO/MARKETING) — o nome do blueprint/rota
   `/vendas/` e da função `require_vendas` é só nomenclatura; a regra de acesso real é
   COMERCIAL/FINANCEIRO/SUPERADMIN + responsável EducaManto, como no ponto 3.

## Complexity Tracking

Nenhuma violação nova.
