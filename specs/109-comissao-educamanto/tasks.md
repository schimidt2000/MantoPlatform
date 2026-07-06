# Tasks — Comissão EducaManto + Padronização dos Orçamentos (109)

**Input**: plan.md, research.md, data-model.md, contracts/routes.md

## Phase 1: Setup

- [X] T001 Conferir head das migrations (`c3d4e5f6a7b8`) e unicidade do revision novo
      `e5f6a7b8c9d0` em `migrations/versions/`

## Phase 2: Foundational

- [X] T002 `app/constants.py`: constante `EDUCAMANTO_TITLE_PREFIX = "(EDU"`
- [X] T003 `app/models.py`: `SiteSetting.educamanto_seller_id` (FK users, nullable) +
      relationship; `CommissionPayment.payable_from` (Date, nullable);
      property `CalendarEvent.is_educamanto`
- [X] T004 Migration manual `migrations/versions/e5f6a7b8c9d0_educamanto_commission.py`
      (2 colunas + backfill do responsável) e `flask db upgrade` no manto_local

## Phase 3: User Story 1 — comissão do responsável após realização (P1)

- [X] T005 `app/financeiro/routes.py`: helper `_commission_beneficiary(event, settings)`;
      `_event_commission` usa o beneficiário p/ elegibilidade
- [X] T006 `app/financeiro/routes.py`: `_sync_commission_payment` — should_have via
      beneficiário (EDU não exige seller_id); grava/atualiza `seller_id` e `payable_from`
      nas linhas `a_pagar`
- [X] T007 `app/financeiro/routes.py`: `_build_commission_items` — janela por
      `COALESCE(payable_from, sale_date)`
- [X] T008 `app/calendar/routes.py`: `_delete_event` — estorno copia `payable_from`
- [X] T009 `app/admin/routes.py` + `app/templates/admin_settings.html`: select
      "Responsável EducaManto" (GET passa users; POST salva educamanto_seller_id)

## Phase 4: User Story 2 — acesso do responsável (P2)

- [X] T010 `app/financeiro/routes.py`: `_is_educamanto_responsavel()`; `require_vendas`
      aceita o responsável; `pipeline()` filtra `title ilike "(EDU%"` quando
      responsável-somente
- [X] T011 `app/__init__.py`: context processor `is_educamanto_responsavel`;
      `app/templates/base.html`: links Pipeline/Comissões ganham o caso (Clientes não)

## Phase 5: User Story 3 — histórico padronizado (P3)

- [X] T012 `app/educamanto/routes.py`: `historico()` — filtros `date_from`/`date_to`/
      `user_id` (user_id só superadmin), `is_superadmin` + `users` no contexto
- [X] T013 `app/templates/educamanto/historico.html`: coluna "Gerado por" (superadmin) +
      filtros no padrão da calculadora

## Phase 6: Polish & verificação

- [X] T014 Script de verificação funcional vs manto_local (cenários do quickstart.md),
      requests fora de app_context
- [X] T015 `ruff check` nos arquivos tocados (sem erro novo); conferir moeda BR nas telas
      tocadas
- [X] T016 Commit atômico, merge em main, push
