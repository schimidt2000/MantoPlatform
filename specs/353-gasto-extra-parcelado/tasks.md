---
description: "Tasks da feature 353 — gasto extra parcelado"
---
# Tasks: Gasto extra parcelado

**Input**: artefatos em `/specs/353-gasto-extra-parcelado/`

**Verificação (Princípio VIII)**: `verify_353.py` contra o `manto_352` (exceção registrada no `plan.md`), escrito na
fase Foundational, antes do núcleo.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [x] T001 Confirmar o `manto_352` na revisão `f352a1b2c3d4` (sem dados de verify sobrando) para receber a `f353`

---

## Phase 2: Foundational

- [x] T002 Model `GastoParcela` (tabela `gasto_parcelas`) e `SpecialExpense.parcelas` (`order_by=numero`, `cascade="all, delete-orphan"`, `lazy="selectin"`) em `app/models.py`, conforme `data-model.md`
- [x] T003 Migration manual `migrations/versions/f353a1b2c3d4_gasto_parcelas.py` (`down_revision = "f352a1b2c3d4"`): tabela, FK CASCADE, índice, `UNIQUE(special_expense_id, numero)`, `CHECK (valor > 0)`; downgrade; aplicar no `manto_352` com `flask db upgrade && python seed.py`
- [x] T004 Núcleo `app/gastos/parcela_ops.py` (novo): constantes (mínimo 2, máximo 24, mensagens), `ParcelaValidationError(field, message)`, `situacao_derivada(parcelas)`
- [x] T005 **`specs/353-gasto-extra-parcelado/verify_353.py`** — os 11 cenários da spec (FIGURINO e FINANCEIRO descartáveis; conexão separada; cenário 10 DEVE falhar; limpeza no `finally`), escrito AGORA e falhando nos cenários não construídos

---

## Phase 3: História 1 — Lançar em parcelas (P1) 🎯

- [x] T006 [US1] `app/gastos/parcela_ops.py`: `ler_itens(bruto)` (lista ou JSON) e `gravar_parcelas(expense, itens)` — validação por índice, recusas (sem desembolso, devolução, multa, já pago, auditor de marketing), renumeração, `amount` = soma, `payment_status` derivado
- [x] T007 [US1] `app/gastos/gastos_ops.py`: `create_expense` aceita `parcelas` (soma vira o `amount` antes da validação) e chama `gravar_parcelas`; `ParcelaValidationError` sobe como `GastoValidationError` no campo
- [x] T008 [US1] `app/api/gastos_write.py`: `parcelas` (JSON) no `POST /api/gastos`; `app/api/gastos_read.py`: `parcelas` no `_expense_dict`
- [x] T009 [P] [US1] `frontend/apps/internal/src/lib/gastos.ts`: tipo `GastoParcela`, `parcelas?:` no `GastoExtra`, `parcelas` nos inputs de criar (JSON no multipart) e editar
- [x] T010 [US1] `frontend/apps/internal/src/components/Gastos/ParcelasCampo.tsx` (novo): caixa "Pagar em parcelas", linhas data + `MoneyInput`, remover/adicionar, total, parcela paga travada, erros por índice
- [x] T011 [US1] `frontend/apps/internal/src/pages/GastosExtrasPage.tsx`: estado das parcelas no formulário, valor somente leitura quando parcelado, `parcelas` no payload, erros `parcelas*` com lugar

---

## Phase 4: História 2 — Cada parcela na Planilha (P1)

- [x] T012 [US2] `app/gastos/parcela_ops.py`: `parcelas_da_planilha_entre(desde, ate)`, `itens_da_planilha(parcelas, hoje)`, `marcar_situacao(parcela, status, ator)`
- [x] T013 [US2] `app/financeiro/routes.py`: `_pagamentos_gastos_entre` exclui o gasto parcelado; `app/financeiro/atrasados_ops.py`: parcelas em aberto dos meses anteriores
- [x] T014 [US2] `app/api/financeiro_read.py`: itens das parcelas no mês; `app/api/financeiro_write.py`: ramo `expense_parcela` no set-status (antes do `else`) e `parcela_ids` no lote
- [x] T015 [US2] `frontend/apps/internal/src/lib/financeiro.ts` e `lib/pagamentos.ts`: tipo `expense_parcela` (rótulo "Gasto", selecionável, situações do gasto), `parcela_ids` no lote, invalidar `["gastos-extras"]`; `pages/PagamentosPage.tsx`: montar `parcela_ids`

---

## Phase 5: História 3 — Alterar ao editar e aprovar (P1)

- [x] T016 [US3] `app/gastos/gastos_ops.py`: `edit_expense` aplica `parcelas` (ausente = intocado com `amount` = soma; `[]` = desliga; lista = substitui) com a trava da parcela paga; `changed` considera as parcelas
- [x] T017 [US3] `app/api/gastos_write.py`: `parcelas` no `PATCH /api/gastos/<id>`

---

## Phase 6: História 4 — Ver as parcelas no gasto (P2)

- [x] T018 [US4] `frontend/apps/internal/src/components/Gastos/GastoItemViews.tsx`: bloco "Parcelas" no cartão e na linha da tabela

---

## Phase 7: Polimento

- [x] T019 `npm run typecheck`; `ruff check` nos tocados; `ruff format` só nos novos
- [x] T020 `verify_353.py` verde; regressão `verify_352.py` e `specs/331-atrasados-na-planilha/verify_331.py`
- [x] T021 Telas: formulário (criar, editar com parcela paga travada) em 390 px e desktop; lista; Planilha com itens de parcela
- [x] T022 Docs: `docs/01` (tabela, contratos, itens da Planilha, §4.3), `docs/02` (formulário, lista, Planilha), `docs/03` (entrada), `docs/04` (parcela na Planilha, gasto na DRE)

---

## Dependências e ordem

Setup → Foundational → US1 → US2 → US3 → US4 → Polimento. T009 em paralelo com T006–T008; T015 depois de T014.

## Estratégia

MVP = US1 + US2 (lançar e pagar por parcela). Commit `feat(353):` por caminho; sobe junto com a 352 quando o dono pedir.

---

## Phase 8: Convergence

- [x] T023 Corrigir a spec §RBAC: os gates não mudaram, então o `docs/01` §4.3 não ganha linha; a mudança de contrato está no §3 (tabela de endpoints da Planilha e §3.7) per spec §RBAC (contradicts)
