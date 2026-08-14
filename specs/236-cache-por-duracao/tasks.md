# Tasks: Cachê sugerido pela duração real do evento

**Input**: Design documents from `/specs/236-cache-por-duracao/`

**Tests**: `verify_236.py` contra `manto_local` (gabarito: orçamentos 1806 e 1573) + quickstart.

## Phase 1: Foundational

- [x] T001 Régua em `app/calendar/routes.py::_compute_performer_caches`: parâmetro `horas_extra: int | None = None`; quando > 4, cada papel de tabela ganha `cache_custom` = round(base_4h_sem_make ÷ 4 × horas) + delta_make + noturno + adicional_fora_sp + show customizado; coordenador e técnico escalam, maquiador não; `horas_extra=None` produz saída idêntica à atual (paridade)

## Phase 2: US1 — Evento nasce com cachês da duração real (P1) 🎯 MVP

- [x] T002 [US1] Criação em `app/calendar/routes.py`: `duracao` validada como int ≥ 1 (erro de campo se inválida — fim do fallback→1h); com `orcamento_history_id`, recomputar cachês no servidor (`_compute_performer_caches` do form_snapshot, `horas_extra` quando > 4) e usar em `cache_value`/`cache_cap`; `orc_caches` do cliente só como fallback sem orçamento; conferir o caminho do wrapper Jinja e do endpoint JSON (`app/api/agenda_write.py`)
- [x] T003 [US1] `_build_orcamento_prefill`: incluir `cache_custom` nos `caches` quando o orçamento tem `duracao_custom` > 4 (informativo p/ tela); tipo `OrcamentoCache` em `frontend/apps/internal/src/lib/eventCreate.ts` ganha `cache_custom?: number`
- [x] T004 [US1] Criar `specs/236-cache-por-duracao/verify_236.py` (blocos 1–2 do quickstart: gabarito 520/500/575, paridade 1–4h nos snapshots 1806/1573, duração inválida rejeitada) e rodar contra `manto_local`

## Phase 3: US1 (UI) — Duração livre na criação

- [x] T005 [US1] `frontend/apps/internal/src/pages/EventCreatePage.tsx`: input "Outra (h)" (min 5) ao lado dos botões 1–4h, mutuamente exclusivo com eles; pré-carrega `duracao_custom` do prefill e mostra `total_custom` como preço de referência; envia a duração escolhida; `npx tsc --noEmit` limpo

## Phase 4: US3 — Aviso "abaixo do sugerido" no casting

- [x] T006 [US3] `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx`: `abaixoDoSugerido = cache_cap != null && cache < cache_cap` → aviso informativo (mesmo padrão visual do atual, sem expor o número e sem bloqueio); papéis sem cap seguem sem aviso

## Phase 5: Polish

- [x] T007 Validação no app real (quickstart blocos 2–4: criar evento 6h do orçamento 1806 no manto_local, conferir prefill/tetos/avisos) e regressão (orçamento 1573 recalcula idêntico; tsc limpo)
- [x] T008 Documentação viva: `docs/01` (contrato da criação/duração), `docs/02` (EventCreatePage + CastingSection), `docs/03` (entrada no topo com o bug do fallback→1h e a régua), `docs/05` (baixa da dívida "teto de 1h em eventos longos")

## Dependencies

T001 → T002/T003/T004 → T005 → T007; T006 independente após T001; US2 (noturno) já é atendida por T001/T002 (o noturno existente no prefill passa a viajar com a duração certa).

## Implementation Strategy

MVP = T001–T004 (backend certo + verificado). T005/T006 fecham a UX. Commits atômicos por fase.
