# Implementation Plan: Pipeline de Vendas em React (Leitura) (156)

**Branch**: `156-vendas-pipeline-leitura` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/156-vendas-pipeline-leitura/spec.md`

## Summary

Abre a US4 (Financeiro/Vendas) — equivalente ao que a 145 foi para Agenda e a 154 para Talentos/
Figurino: a fatia de leitura mais estreita e independente do módulo. Migra `/vendas/` (pipeline
de vendas) para React: listagem de eventos com venda/custo/lucro/comissão, reaproveitando os
cálculos já existentes em `app/financeiro/routes.py` (`_group_cost`, `_event_cost`,
`_event_commission`, `_get_commission_rate`) sem duplicar. Dashboard DRE (`/financeiro/`),
planilha de pagamentos (`/financeiro/pagamentos`), cadastro de funcionário/salário
(`/financeiro/funcionarios`) e comissões (`/financeiro/comissoes`) ficam para fatias futuras —
cada uma grande e financeiramente sensível o suficiente para seu próprio `/speckit-plan`.

## Technical Context

Igual à 144-155: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

- **I (reutilizar)**: núcleo reaproveita `_group_cost`/`_event_cost`/`_event_commission`/
  `_get_commission_rate`/`_is_permuta`/`_has_role`/`_is_educamanto_responsavel`, todos já
  existentes e já puros (sem `request`/`flash`, só `event`/`settings`/`current_user`) em
  `app/financeiro/routes.py` — mesma exceção "core-in-routes" de `calendar/routes.py`
  (146-153): esses helpers são multi-uso dentro do blueprint financeiro (dashboard, pipeline,
  comissões), então não faz sentido extrair para um módulo `_ops` novo só para esta fatia.
- **II (padrões de código)**: endpoint novo em `app/api/financeiro_read.py`, type hints/
  docstring; sem lógica de negócio nova, só serialização.
- **III (API first)**: 1 endpoint novo, 100% JSON (`GET /api/vendas/pipeline`); a view Jinja
  `/vendas/` continua existindo em paralelo, sem mudança de comportamento (FR-007).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos valores de
  venda/custo/comissão/lucro para os mesmos eventos, nos dois caminhos.
- **V (feedback)**: estado vazio amigável quando não há eventos; 403 tratado pelo
  `RequireAuth`/interceptor padrão do cliente API (mesmo comportamento de toda tela já migrada).
- **VII (monetário)**: valores formatados com `formatBRL`/`@manto/money` no frontend — a API
  devolve números (Decimal→float, mesma convenção de `_event_detail_json`/`get_talent_profile`),
  nunca string formatada.
- **VIII (mobile-first)**: tabela do pipeline conferida em 320–430px (scroll horizontal dentro
  do próprio card, mesmo padrão já usado em outras tabelas migradas).
- **IX (movimento)**: navegação padrão (React Router) para o detalhe do evento já migrado; sem
  transição nova.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/156-vendas-pipeline-leitura/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/vendas-pipeline-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/financeiro_read.py         # NOVO — GET /api/vendas/pipeline
app/api/__init__.py                # + import do módulo novo (efeito colateral de registro)
frontend/apps/internal/src/
├── lib/vendas.ts                  # NOVO — useVendasPipeline()
├── pages/VendasPipelinePage.tsx   # NOVO — tabela (mesmas colunas da Jinja, lucro condicional)
App.tsx                            # + rota /vendas
scripts/db/verify_156_vendas_pipeline.py  # NOVO: paridade API×Jinja + RBAC 403
```

**Structure Decision**: núcleo permanece em `app/financeiro/routes.py` (funções já puras e
multi-uso, mesma exceção da Agenda) — só o endpoint de leitura é novo, em
`app/api/financeiro_read.py` (nome espelha `agenda_read.py`/`talents_read.py`/`figurino_read.py`).

## Design Decisions

1. **`GET /api/vendas/pipeline`** (`app/api/financeiro_read.py`, gate: `require_vendas`
   reimplementado como função — COMERCIAL/FINANCEIRO/SUPERADMIN ou responsável EducaManto,
   paridade exata com `require_vendas`/`_is_educamanto_responsavel`):
   - Reaproveita a mesma query de `pipeline()` (eventos exceto ENSAIO, filtro EducaManto
     quando aplicável, `order_by(start_at.desc())`).
   - Para cada evento (pulando satélites, mesma regra `if e.is_satellite: continue`): monta
     `{"event_id", "title", "is_satellite": False, "is_group_leader", "group_label",
     "location", "sale_date", "sale_value", "custo", "comissao", "with_invoice", "lucro"}` —
     `lucro` só presente quando `is_financeiro` (Financeiro/Superadmin), mesma condicional do
     template hoje.
   - `title`/`group_label`: quando `is_group_leader`, `group_label` = `group_display_name` +
     contagem de satélites; senão `group_label` é `None` e `title` é `event.title` (o frontend
     decide o que mostrar, mesma lógica hoje no Jinja).
   - Resposta: `{"items": [...], "is_financeiro": bool}` — `is_financeiro` replica a flag que
     hoje controla a coluna de lucro no template, exposta para o frontend decidir a coluna.
2. **Frontend — página nova, não seção de página existente**: `VendasPipelinePage.tsx` é uma
   tabela simples (mesmo padrão de `TalentsListPage`), com link "Ver" para
   `/events/:id` (rota já existente desde a 145) — sem duplicar o detalhe do evento.
3. **Sem alteração em `require_vendas`/helpers do Jinja**: o endpoint novo reimplementa o gate
   (mesma regra), não importa a closure `require_vendas` (decorator específico de view Flask,
   não reusável como função de gate simples) — paridade por comportamento, verificada pelo
   script.

## Complexity Tracking

Nenhuma violação nova.
