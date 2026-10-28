# Tasks: Feature 322 — o casting vê o que está fechando

**Input**: artefatos em `/specs/322-o-que-o-casting-fecha/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/evento-elenco.md

**Verificação**: `specs/322-o-que-o-casting-fecha/verify_322.py` contra `manto_local`, escrito na
fase Foundational (T003) antes do núcleo; falha pelos motivos certos e passa ao fim de cada
história.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [ ] T001 Colunas `perfil_vendido` (`String(200)`), `criada_pelo_sistema` e `escalado_pelo_comercial`
      (`Boolean`, nulas) em `EventRole`, `app/models.py`, com o comentário do porquê (data-model.md)
- [ ] T002 Migration à mão `migrations/versions/c322a7e1b9d4_vaga_perfil_e_origem.py`
      (`down_revision = "e8b4a1c7d310"`, upgrade/downgrade das três colunas); `flask db upgrade` no
      `manto_local` e conferir `flask db heads` com uma cabeça só

---

## Phase 2: Foundational (bloqueia as histórias)

- [ ] T003 **`specs/322-o-que-o-casting-fecha/verify_322.py`** — os 23 cenários da spec (login pela
      API; eventos de teste criados por `POST /api/events` e orçamento descartável; escrita conferida
      por conexão separada; 17, 18 e 22 DEVEM falhar no código antigo; limpeza no `finally`).
      Rodar e guardar a saída vermelha em `verify_322_primeira_falha.txt`
- [ ] T004 `app/calendar/casting_ops.py`: `garantir_vaga_de_maquiador(event, *, tz)` (research R5) —
      sem efeito em cancelado/sem make/com "maquiad"; cria `Maquiador` extra com
      `criada_pelo_sistema=True` + `EventLog` do Sistema (FR-017); não comita

**Checkpoint**: banco migrado, verify vermelho pelos motivos certos, a regra pronta para os
caminhos.

---

## Phase 3: História 1 — o casting vê o que é cada personagem (P1) 🎯 MVP

**Verificação**: cenários 1–6 do `verify_322.py`; página do evento aberta.

- [ ] T005 [US1] `app/calendar/routes.py` `_compute_performer_caches`: chave `perfil` em cada item de
      personagem (tipo + marcas show · cantor · com maquiagem[ especial], separador " · ") — research R1
- [ ] T006 [P] [US1] `app/orcamento/produtos.py` `_item`/`itens_do_teto`: `perfil` da vaga do produto
      (rótulo do produto + "com maquiagem" quando a vaga tem make); coordenador do produto sem perfil
- [ ] T007 [US1] `app/calendar/routes.py` `_create_roles_from_input`: `perfil_vendido` do item
      pareado (`orc_chars[i]`), cortado em 200 caracteres
- [ ] T008 [US1] `app/calendar/orcamento_evento_ops.py` `aplicar_equipe_do_orcamento`: personagem
      casado recebe `perfil_vendido` só se vazio (FR-004)
- [ ] T009 [US1] `app/api/agenda_read.py` `_serialize_role`: `perfil` (gravado ou marcas das flags,
      FR-003), `criada_pelo_sistema`, `escalado_pelo_comercial` — para todo leitor do elenco
- [ ] T010 [P] [US1] `frontend/apps/internal/src/lib/agenda.ts` `RoleItem`: `perfil?`,
      `criada_pelo_sistema?`, `escalado_pelo_comercial?` (opcionais — janela do deploy)
- [ ] T011 [US1] `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx` `RoleCard`:
      linha do perfil abaixo do nome (texto secundário, `text-xs`)

**Checkpoint**: cenários 1–6 verdes; o card mostra o perfil.

---

## Phase 4: História 2 — personagem com maquiagem traz o maquiador (P1)

**Verificação**: cenários 7–12.

- [ ] T012 [US2] `app/calendar/routes.py` criação (`_create_event_core`, depois de
      `_apply_default_roles`): chamar `garantir_vaga_de_maquiador`
- [ ] T013 [US2] `app/calendar/event_ops.py` `update_event_core`: chamar `garantir_vaga_de_maquiador`
      no fim (depois do laço e do coordenador)
- [ ] T014 [US2] `app/calendar/orcamento_evento_ops.py` vínculo (`vincular_orcamento`, depois de
      `aplicar_equipe`): chamar `garantir_vaga_de_maquiador`; relatório diz "maquiador criado"

**Checkpoint**: cenários 7–12 verdes.

---

## Phase 5: História 3 — "adicionado pelo sistema" (P2)

**Verificação**: cenários 13–15.

- [ ] T015 [US3] `app/calendar/routes.py`: `criada_pelo_sistema=True` em `_ensure_coordinator`,
      `_ensure_sound_technician` (as duas vagas) e `_create_extra_roles_from_orcamento` (criação e
      correção no lugar)
- [ ] T016 [US3] `app/calendar/orcamento_evento_ops.py` `aplicar_equipe_do_orcamento`:
      `criada_pelo_sistema=True` nos coordenadores, técnico e maquiador criados
- [ ] T017 [US3] `CastingSection.tsx`: "adicionado pelo sistema" ao lado do nome (RoleCard e
      PresencaCard), menor e em texto secundário, lido pelo leitor de tela junto com o nome

**Checkpoint**: cenários 13–15 verdes.

---

## Phase 6: História 4 — só o superadmin mexe na maquiagem depois (P2)

**Verificação**: cenários 16–19.

- [ ] T018 [US4] `app/calendar/event_ops.py` `update_event_core`: sem `is_superadmin`, vaga existente
      mantém `needs_makeup`; vaga nova nasce com `needs_makeup=None` (FR-012)
- [ ] T019 [P] [US4] `frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx`: prop
      `maquiagemTravada` — caixa `disabled` e a frase "Só o superadmin muda a maquiagem depois que o
      evento existe."
- [ ] T020 [US4] `frontend/apps/internal/src/pages/EventEditPage.tsx`: passar
      `maquiagemTravada={!data.flags.is_superadmin}`

**Checkpoint**: cenários 16–19 verdes.

---

## Phase 7: História 5 — pré-escalado pelo comercial (P2)

**Verificação**: cenários 20–22.

- [ ] T021 [US5] `app/calendar/routes.py`: `escalado_pelo_comercial=True` na pré-escala de
      `_create_roles_from_input` e no coordenador escolhido de `_apply_default_roles`
- [ ] T022 [US5] `app/calendar/event_ops.py` `update_event_core`: `escalado_pelo_comercial=True` quando
      o formulário troca o talento (personagem e coordenador; vaga nova com talento)
- [ ] T023 [US5] `app/calendar/casting_ops.py` `assign_role`: `escalado_pelo_comercial=None` quando
      o talento muda (inclusive para vazio)
- [ ] T024 [US5] `CastingSection.tsx`: "inserido pelo comercial" junto ao nome do talento

**Checkpoint**: cenários 20–22 verdes.

---

## Phase 8: Polish e portões

- [ ] T025 `verify_322.py` inteiro verde → `verify_322_resultado.txt`; verifies vizinhos que tocam as
      mesmas funções (`specs/309-produtos-de-tabela/verify_309.py --regressao`,
      `specs/273-*/verify_273.py` se existir) sem regressão nova
- [ ] T026 `ruff check` nos `.py` tocados; `cd frontend && npm run typecheck`
- [ ] T027 Tela aberta (skill `manto-conferir-tela`): página do evento em desktop e 375×812;
      formulário de edição como comercial (travado) e superadmin (livre)
- [ ] T028 Docs: `docs/01` (schema `event_roles`, payload do elenco, regra do `PATCH`, §4.3),
      `docs/02` (página do evento e formulário de edição), `docs/03` (entrada no topo + índice),
      `docs/04` (invariante maquiagem ⇒ maquiador), `docs/05` (dívidas novas)

---

## Dependências

- T001 → T002 → T003 → T004 → histórias.
- US1 (T005–T011) e US2 (T012–T014) independentes entre si; US3 depende de T001 e toca os mesmos
  arquivos de US1/US2 (fazer depois); US4 e US5 tocam `update_event_core` — em sequência.
- Polish depois de todas.

## Paralelo

- T006 (produtos.py) ‖ T005 (routes.py); T010 (agenda.ts) ‖ backend; T019 (ElencoBlock) ‖ T018.

## Estratégia

MVP = US1 + US2 (o pedido central: o que é o personagem e o maquiador que aparece). US3–US5 no mesmo
ciclo, um deploy só.
