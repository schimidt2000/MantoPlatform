# Tasks: Pipeline de Vendas em React (Leitura) (156)

**Input**: Design documents from `specs/156-vendas-pipeline-leitura/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/vendas-pipeline-endpoint.md,
quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_156_vendas_pipeline.py` contra
`manto_local`, gerado na Phase de Polish.

**Organização**: story única (US1, P1) — não há uma segunda user story nesta fatia.

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

Nenhuma — núcleo (`_group_cost`/`_event_cost`/`_event_commission`/`_get_commission_rate`/
`_is_permuta`) já existe em `app/financeiro/routes.py`.

## Phase 3: User Story 1 — Ver o pipeline de vendas em React (P1)

**Goal**: usuário com acesso a Vendas vê a listagem de eventos (venda/custo/comissão/lucro)
inteiramente pela tela React.

**Independent Test**: abrir `/vendas` em React e conferir paridade de valores com a tela antiga
para o mesmo usuário.

- [X] T002 [US1] Implementar `GET /api/vendas/pipeline` em `app/api/financeiro_read.py` (NOVO):
      gate paridade com `require_vendas`/`_is_educamanto_responsavel`, query igual à de
      `pipeline()` (`app/financeiro/routes.py:1528`), serialização conforme
      `contracts/vendas-pipeline-endpoint.md` (`lucro` só quando `is_financeiro`).
- [X] T003 [US1] Registrar o módulo novo em `app/api/__init__.py` (import para efeito colateral
      de registro das rotas, mesmo padrão dos demais módulos `_read.py`).
- [X] T004 [P] [US1] Criar `useVendasPipeline()` em `frontend/apps/internal/src/lib/vendas.ts`
      (NOVO) — `useQuery` simples contra `/api/vendas/pipeline`.
- [X] T005 [US1] Criar `frontend/apps/internal/src/pages/VendasPipelinePage.tsx` (NOVO):
      tabela com as colunas de `contracts/vendas-pipeline-endpoint.md` (lucro condicional a
      `is_financeiro`), valores formatados com `formatBRL` (`@manto/money`), estado vazio
      amigável, link "Ver" para `/events/:id`.
- [X] T006 [US1] Adicionar rota `/vendas` em `App.tsx` (+ item de navegação, se o menu lateral
      já listar telas migradas — mesmo padrão das rotas anteriores).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: Polish & Verificação

- [X] T007 Criar `scripts/db/verify_156_vendas_pipeline.py` (gitignored): test client Flask
      contra `manto_local`, requests fora de `app_context` — cobre paridade de valores (venda/
      custo/comissão/lucro), exclusão de satélite, filtro EducaManto, e os gates 403.
- [X] T008 Rodar `ruff check app/` nos arquivos tocados.
- [X] T009 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [X] T010 Conferência mobile (320–430px) da tabela do pipeline (scroll horizontal dentro do
      card, Princípio VIII).
- [X] T011 Atualizar `docs/changelog.html` com entrada em linguagem simples, republicando no
      mesmo link existente.

## Dependencies

Setup (Phase 1) → Foundational (Phase 2, vazia) → US1 (Phase 3) → Polish (Phase 4).
Dentro da story: endpoint API → registro do módulo → hook frontend → página → rota.

## Implementation Strategy

MVP = a própria US1 (story única desta fatia). Fatias futuras da US4 (dashboard DRE, planilha
de pagamentos, funcionário/salário, comissões) seguem cada uma com seu próprio ciclo completo.
