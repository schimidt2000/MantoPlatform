# Tasks: RH em React + destino do blueprint órfão `tools_bp` (166)

**Input**: Design documents from `specs/166-rh-tools-bp-react/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/rh-endpoint.md, quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_166_rh_tools_bp.py` contra
`manto_local`, gerado na Phase de Polish.

**Organização**: 2 user stories — US1 painel de RH em React (P1), US2 decisão/remoção de
`tools_bp` (P2). Independentes entre si.

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

Nenhuma — RH não tem núcleo de negócio a extrair (só checagem de permissão, já em
`User.has_permission`).

## Phase 3: User Story 1 — Painel de RH em React (P1)

- [X] T002 [US1] Implementar `GET /api/rh/dashboard` em `app/api/rh_read.py` (NOVO): gate
      `current_user.has_permission("rh.view")` → 403; 200 `{"can_manage_users": bool}`.
- [X] T003 Registrar `rh_read` em `app/api/__init__.py`.
- [X] T004 [P] [US1] Criar `useRhDashboard()` em `frontend/apps/internal/src/lib/rh.ts` (NOVO).
- [X] T005 [US1] Criar `frontend/apps/internal/src/pages/RhDashboardPage.tsx` (NOVO): mostra o
      atalho "Gerenciar usuários" (link direto para `/admin/users`, ainda Jinja, via
      `API_BASE` — fatia futura da US6 migra esse destino) quando `can_manage_users`.
- [X] T006 [US1] Adicionar rota `/rh` em `App.tsx` + link no dashboard (`DashboardPage.tsx`).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 4: User Story 2 — Decisão sobre `tools_bp` (P2)

- [X] T007 [US2] Remover `app/tools/` (`routes.py`, `__init__.py`) e
      `app/templates/tools/transport_calculator.html` — decisão registrada em `spec.md`
      (Assumptions): duplicava, de forma desatualizada, `app/orcamento/transport.py`; nunca
      esteve registrado em `app/__init__.py`, sem consumidor real.
- [X] T008 [US2] Confirmar que `app/orcamento/transport.py` não importa nada de `app/tools/` e
      continua funcionando sem alteração.

**Checkpoint**: US2 completa e testável isoladamente.

---

## Phase 5: Polish & Verificação

- [X] T009 Criar `scripts/db/verify_166_rh_tools_bp.py` (gitignored): paridade API×Jinja do
      painel de RH (com/sem `user.manage`), gate 403 sem `rh.view`, confirma remoção de
      `app.tools` (módulo inexistente + rota órfã 404) e que `calcular_van` do orçamento segue
      funcionando.
- [X] T010 Rodar `ruff check app/` nos arquivos tocados (`rh_read.py`, `__init__.py`).
- [X] T011 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T012 Conferência mobile (320–430px) da tela de RH — **não verificado nesta sessão**: sem
      Playwright/chromium-cli disponível no ambiente (mesma limitação recorrente).
- [X] T013 Atualizar `docs/changelog.html` com entrada em linguagem simples e republicar no link
      existente.

## Dependencies

Setup (Phase 1) → US1 (Phase 3) e US2 (Phase 4) em paralelo (independentes) → Polish (Phase 5).

## Implementation Strategy

MVP = US1 (painel de RH) — é a única rota real da fatia. US2 (remoção de `tools_bp`) é uma
decisão de limpeza sem risco de regressão (código nunca esteve em produção).
