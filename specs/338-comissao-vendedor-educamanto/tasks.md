---
description: "Tasks da feature 338 — comissão do vendedor e lucro real no EducaManto"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Comissão do vendedor e lucro real no EducaManto

**Input**: artefatos em `/specs/338-comissao-vendedor-educamanto/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `verify_338.py` contra `manto_338` (espelho de 06/11,
`research.md` R9), escrito na Fase 2, antes do núcleo; nasce falhando pelos motivos certos.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Constante `ORIGEM_VENDEDOR_EDUCAMANTO = "vendedor_educamanto"` e as mensagens do campo (valor inválido, acima da venda, fora do EducaManto, cancelado) em `app/constants.py`

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T002 Colunas novas em `app/models.py`: `CalendarEvent.educamanto_seller_commission`, `CommissionPayment.source`, `EventCancellation.educamanto_seller_id` (+ relação `educamanto_seller` com `foreign_keys=`) e `EventCancellation.educamanto_seller_commission`, com comentário do porquê
- [X] T003 Migration manual `migrations/versions/d338c5a9e2b1_comissao_vendedor_educamanto.py` (`down_revision = 'd323b5a1c0e7'`; upgrade e downgrade das 4 colunas e da FK); aplicar no `manto_338` com `flask db upgrade`
- [X] T004 Trilhas na reconciliação em `app/financeiro/comissoes_ops.py`: filtro `_da_trilha(fonte)`; `_comissao_existente`, `_beneficiarios_com_linha_viva`, `reconciliar_comissao_do_cancelado` (parâmetro `fonte=None`; linha nova nasce com `source=fonte`; a liberação no dia do evento vale também para a trilha do vendedor), `_reconciliar_ajuste_vivo` e `comissao_exibida_do_evento` na trilha principal — nenhum número muda nesta tarefa
- [X] T005 **`specs/338-comissao-vendedor-educamanto/verify_338.py`** — os 10 cenários da spec (Jundiaí e Santo Américo pela função, sem gravar; EducaManto descartável para os de escrita; login só pela API; escrita conferida por conexão separada; 403 que deve sair; limpeza no `finally`) mais o de não-regressão da comissão comum — rodado agora, falhando nos cenários ainda não construídos

**Checkpoint**: trilhas no lugar, verify falhando só pelo que falta.

---

## Phase 3: História 1 — A comissão do responsável sobre o lucro real (P1) 🎯 MVP

**Meta**: a base do responsável desconta gastos extras aprovados, imposto da nota e a comissão do vendedor.

**Verificação**: cenários 1 e 2 (R$ 771,82 e R$ 61,01) e o de não-regressão.

- [X] T006 [US1] Mover `DEFAULT_TAX_RATE` e `_get_tax_rate` de `app/financeiro/routes.py` para `app/financeiro/comissoes_ops.py` (routes reimporta os dois nomes)
- [X] T007 [US1] `comissao_do_vendedor_edu(event, settings) -> (valor, vendedor)`, `_gastos_da_base(ids)` e `custo_da_base_educamanto(event, settings, *, sem_o_dia=None)` em `app/financeiro/comissoes_ops.py` (dias vivos por `group_ops.dias_vivos`; gastos aprovados fora `cancel_ops.filtro_devolucao`)
- [X] T008 [US1] `_base_da_comissao`, `comissao_cheia_do_evento` e `cheia_do_congelado` com o imposto (`com_nota` sobreponível) e o custo novo em `app/financeiro/comissoes_ops.py`
- [X] T009 [US1] Custo do ato e do corte pela função nova em `app/calendar/cancel_ops.py` (`_custo_congelado`, `_custo_sem_o_dia`); `com_nota=canc.with_invoice` nas duas chamadas de `recongelar_do_comercial`
- [X] T010 [US1] Rodar `verify_338.py`: cenários 1, 2 e não-regressão verdes

**Checkpoint**: a comissão do Gabriel já sai da conta nova (sem a Thaís, enquanto o campo não existe).

---

## Phase 4: História 2 — A comissão do vendedor EducaManto (P1)

**Meta**: o card Comercial grava o valor; nasce a linha do vendedor; DRE e comissão prevista somam.

**Verificação**: cenários 3 a 7 e 9.

- [X] T011 [US2] `_sync_comissao_do_vendedor_edu` e a casca `_sync_commission_payment` (corpo de hoje em `_sync_comissao_do_evento`, depois a trilha do vendedor) em `app/financeiro/comissoes_ops.py`
- [X] T012 [US2] `educamanto_seller_commission` em `SATELLITE_FIELDS_CLEARED` (`app/calendar/group_ops.py`) e o estorno da exclusão copiando `source` (`aplicar_estorno_comissao`, `app/calendar/cancel_ops.py`)
- [X] T013 [US2] Validação `erros_da_comissao_do_vendedor` e gravação do campo (chave ausente não mexe; cortesia grava `NULL`; 409 `cancelado` quando o valor muda no cancelado) em `app/calendar/event_ops.py`; corpo do `PATCH /comercial` em `app/api/agenda_write.py`
- [X] T014 [US2] DRE: comissão do vendedor nas comissões de `_compute_drg` em `app/financeiro/routes.py`; `comissao_prevista` em `app/financeiro/vendas_ops.py` (`build_kpis`)
- [X] T015 [US2] Rodar `verify_338.py`: cenários 3 a 7 e 9 verdes

---

## Phase 5: História 3 — No cancelado, as duas comissões acompanham o retido (P2)

**Verificação**: cenário 8.

- [X] T016 [US3] Congelado do vendedor no ato (`ContaDoAto.vendedor_id/vendedor_valor/vendedor_retido`, `alvos_do_vendedor`, `_congelar`) e a reconciliação da trilha do vendedor na execução e na prévia do ato em `app/calendar/cancel_ops.py`
- [X] T017 [US3] `reaplicar_cancelado` refaz a trilha do vendedor; troca de vendedor em `recongelar_do_comercial` passa o congelado e os motivos em `app/calendar/cancel_ops.py`
- [X] T018 [US3] `ResumoCancelado.comissao_vendedor_retido` e `vendedor_edu`, no `efeito_resultado`, em `totais_cancelamentos` e no `painel_de_cancelamentos` (alvo) em `app/calendar/cancel_ops.py`
- [X] T019 [US3] Rodar `verify_338.py`: cenário 8 verde

---

## Phase 6: História 4 — As telas mostram de onde vem cada comissão (P3)

- [X] T020 [US4] Detalhe: `venda.educamanto_seller_commission`, `venda.mostra_comissao_do_vendedor`, `kpi.seller_commission`, `kpi.seller_commission_name` em `app/api/agenda_read.py`
- [X] T021 [US4] `CommissionEntry.origem` + `sale_count` por evento distinto em `app/financeiro/comissoes_ops.py`; `commission_lines[].origem` em `app/financeiro/routes.py`
- [X] T022 [P] [US4] Tipos opcionais em `frontend/apps/internal/src/lib/agenda.ts`, `lib/eventInline.ts` (`EventComercialInput`) e `lib/financeiro.ts` (`CommissionEntry`, `CommissionLine`)
- [X] T023 [US4] Campo "Comissão do vendedor" no `VendaForm`, valor no `VendaPanel` e a linha do vendedor no KPI "Comissão" em `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx`
- [X] T024 [P] [US4] Rótulo "Comissão do vendedor (EducaManto)" em `frontend/apps/internal/src/pages/ComissoesPage.tsx` e em `frontend/apps/internal/src/components/Pagamentos/PagamentoItemViews.tsx`
- [X] T025 [US4] Conferir no Browser pane (backend e Vite do worktree): card Comercial de um EducaManto e Comissões

---

## Phase 7: Polish

- [X] T026 Portões: `cd frontend && npm run typecheck`; `ruff check` nos arquivos tocados; `ruff format` na migration e no verify
- [X] T027 Docs: `docs/01` (schema das 3 tabelas, `/comercial`, §4.3), `docs/02` (card Comercial, Comissões), `docs/04` §2 (regra de comissão ramo 5, invariantes do cancelado), `docs/03` (entrada no topo + índice); `.claude/skills/financeiro/SKILL.md` (coluna `source`)
- [X] T028 `/speckit-converge` e commit `feat(338):` por caminho

## Dependências

Fase 2 → US1 → US2 (a base usa a comissão do vendedor e o campo) → US3 (congela o vendedor) → US4 (telas).
US4 depende só dos campos de API de US2; T022 e T024 podem correr em paralelo com T023.

## Estratégia

MVP = US1 + US2: é o que conserta o repasse de 05/11 (Gabriel R$ 771,82 + R$ 61,01; Thaís R$ 1.500). US3
fecha o buraco do cancelado; US4 deixa a origem visível.

## Phase 8: Convergence

- [X] T029 Estender o cenário 8 do `specs/338-comissao-vendedor-educamanto/verify_338.py` com a troca de vendedor pelo Superadmin no cancelado (o antigo vai a 0, o novo leva o retido da comissão do vendedor) per FR-005 (partial)
