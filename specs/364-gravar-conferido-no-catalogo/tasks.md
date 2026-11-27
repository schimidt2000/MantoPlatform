# Tasks: Gravar no catálogo o conferido (364)

## Phase 1: Setup

- [x] T001 Worktree `C:\tmp\mp364`, espelho `manto_364` (dump de 26/11 02h), `.specify/feature.json`
- [x] T002 Leitura das fotos apontadas nas observações → `app/admin/dados/ajustes_conferencia.json`

## Phase 2: Foundational

- [x] T003 Colunas `gravado_em` e `catalog_character_id` em `app/models.py`
- [x] T004 Migration manual `migrations/versions/f364a1b2c3d4_gravacao_do_conferido.py`; aplicar no `manto_364`
- [x] T005 `specs/364-gravar-conferido-no-catalogo/verify_364.py` (10 cenários; o 9 DEVE falhar), antes do núcleo

## Phase 3: História 1 — o conferido vira elenco (P1)

- [x] T006 [US1] `app/admin/catalog_gravacao_ops.py`: `resumo_da_gravacao`, `gravar_lote`, recorte da foto
- [x] T007 [US1] `GET …/conferencia/gravacao` e `POST …/conferencia/gravar` em `app/api/admin_catalogo_conferencia_{read,write}.py`
- [x] T008 [US1] Bloco "Gravar no catálogo" em `frontend/apps/internal/src/pages/CatalogoConferenciaPage.tsx` e hooks em `lib/catalogoConferencia.ts`

## Phase 4: História 2 — repetir não duplica (P1)

- [x] T009 [US2] Trava consultiva, pulo de item gravado, foto ausente vira "sem foto" em `catalog_gravacao_ops.py`

## Phase 5: História 3 — observações aplicadas (P2)

- [x] T010 [US3] `aplicar_ajustes` em `catalog_gravacao_ops.py`, chamado antes do primeiro lote

## Phase 6: Portões e fechamento

- [x] T011 `verify_364.py` verde; regressão `verify_360.py`
- [x] T012 `npm run typecheck`; `ruff check` nos tocados
- [x] T013 Tela aberta a 390 px
- [x] T014 Docs 01, 02, 03, 04, 05
- [x] T015 Convergência sem gaps
