# Tasks: EducaManto ensemble + catering por pessoa

**Input**: `specs/048-educamanto-ensemble/`
**Tests**: boot + ruff + migration + test client.

## Phase 1: Modelo e migration
- [x] T001 `models.py`: ensemble_* no pacote, ensemble_add no item, to_dict.
- [x] T002 Migration `o1d2e3f4a5b6`: colunas + conversão catering por pessoa + ensemble_add; aplicar.

## Phase 2: Backend
- [x] T003 `educamanto/routes.py`: ENSAIO em _CAN_USE; _DEFAULT_ITEMS por pessoa + ensemble_add;
      parse/create/edit dos novos campos.

## Phase 3: UI
- [x] T004 `index.html`: dropdown + bloco ensemble + JS (effQty, linha ensemble, recálculo).
- [x] T005 `package_form.html`: cachê do ensemble + coluna ensemble_add.
- [x] T006 `base.html`: links EducaManto para ENSAIO.

## Phase 4: Verificação
- [x] T007 ruff + boot + test client (US1–US4); commit.

## Dependencies
- T001 → T002 → T003 → T004/T005/T006 → T007.
