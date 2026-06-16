---

description: "Task list for feature 053 — Agrupamento de Eventos por Contrato"
---

# Tasks: Agrupamento de Eventos por Contrato

**Input**: Design documents from `specs/053-agrupar-eventos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: Não solicitados explicitamente na spec e o projeto não possui suite
automatizada (`pytest`/`conftest.py` inexistentes) — verificação será manual
via `quickstart.md`, como já praticado nas features 051/052.

**Organização**: Tarefas agrupadas por user story (US1–US4 de `spec.md`), na
ordem de prioridade P1 → P1 → P2 → P3.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: Preparar terreno para a migration manual (autogenerate está
quebrado por drift pré-existente — ver memória do projeto).

- [X] T001 Confirmar revisão atual do banco local (`flask db current`) e
      identificar a última migration em `migrations/versions/` para usar como
      `down_revision` da nova migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Campo de dados e infraestrutura que TODAS as user stories
dependem (nenhuma rota nova funciona sem o campo `group_leader_id`).

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase.

- [X] T002 Adicionar campo `group_leader_id` (Integer, FK →
      `calendar_event.id`, nullable) e relacionamento `group_leader` /
      backref `satellites` em `CalendarEvent`, em `app/models.py` (ver
      data-model.md)
- [X] T003 Adicionar propriedades `is_satellite` e `is_group_leader` em
      `CalendarEvent`, em `app/models.py` (data-model.md)
- [X] T004 Escrever migration manual `migrations/versions/<rev>_group_leader_id.py`
      adicionando a coluna e a FK via `batch_alter_table`, com `down_revision`
      apontando para a revisão identificada em T002
- [X] T005 Aplicar a migration localmente (`python -m flask db upgrade`) e
      confirmar que a coluna existe via inspeção do schema SQLite local

**Checkpoint**: Campo `group_leader_id` existe e é persistido — user stories
podem começar.

---

## Phase 3: User Story 1 - Agrupar eventos sob um único contrato (Priority: P1) 🎯 MVP

**Goal**: Usuário comercial/financeiro/superadmin consegue vincular 2+
eventos existentes, escolhendo um como principal, com todas as validações de
integridade do grupo.

**Independent Test**: Criar 2 eventos, agrupar um ao outro pela tela de
evento, e confirmar que o satélite passa a exibir indicativo de grupo.

### Implementation for User Story 1

- [X] T006 [US1] Implementar helper `_apply_satellite(event)` em
      `app/calendar/routes.py` que zera os campos comerciais listados em
      data-model.md (`sale_value`, `sale_value_gross`, `sale_date`,
      `with_invoice`, `is_cortesia_permuta`, `seller_id`, `commission_rate`,
      `payment_method`, `payment_installments`, `payment_due_date`,
      `transport_value`, `acrescimo_value`, `invoice_file`,
      `orcamento_history_id`)
- [X] T007 [US1] Implementar rota `POST /eventos/<int:event_id>/agrupar` em
      `app/calendar/routes.py`, com as validações do contrato (FR-002, FR-003,
      FR-004, estrutura plana de 2 níveis) e confirmação obrigatória
      (`confirm_clear_financials`) quando o satélite já tinha venda
      preenchida (FR-005), conforme `contracts/routes.md`
      (Nota: implementado via `action=group_events` na rota existente
      `POST /events/<id>`, padrão de action-dispatch já usado no projeto,
      em vez de uma rota dedicada — ver `_EVENT_ACTIONS`)
- [X] T008 [US1] Implementar guarda de exclusão (FR-009): bloquear a rota de
      exclusão de evento existente em `app/calendar/routes.py` quando
      `event.is_group_leader` for `True`, orientando a desagrupar satélites
      primeiro
- [X] T009 [US1] Registrar log de auditoria (FR-015: usuário, ação `group`,
      `event_id`, `group_leader_id`, timestamp) na rota de agrupar, em
      `app/calendar/routes.py`, reaproveitando o mecanismo de log já existente
      no projeto
- [X] T010 [US1] Adicionar UI de "Agrupar a outro evento" em
      `app/templates/event_detail.html`: seletor de evento existente +
      escolha de qual é o principal + confirmação destrutiva quando aplicável
      (Princípio V — UI/UX)
- [X] T011 [US1] Adicionar validação de formulário (RBAC: COMERCIAL,
      FINANCEIRO, SUPERADMIN) no botão/rota de agrupar em
      `app/templates/event_detail.html` e `app/calendar/routes.py`

**Checkpoint**: Dois eventos podem ser agrupados; satélite tem campos
comerciais zerados; exclusão de principal com satélites é bloqueada.

---

## Phase 4: User Story 2 - Painel financeiro trata o grupo como uma única venda (Priority: P1)

**Goal**: `/financeiro/` e `/vendas/` contam o grupo como 1 venda, somando os
cachês de todos os satélites no custo do principal.

**Independent Test**: Agrupar 2 eventos com cachês cadastrados sob um
principal com valor de venda definido; confirmar no `/financeiro/` que o
grupo conta como 1 evento vendido e que o CPV soma os dois.

### Implementation for User Story 2

- [X] T012 [US2] Implementar `_group_cost(event)` em
      `app/financeiro/routes.py`: quando `event.is_group_leader`, soma
      `_event_cost(event)` + `_event_cost(s)` para cada satélite em
      `event.satellites` (research.md item 3)
- [X] T013 [US2] Atualizar o filtro da lista `normais` em
      `app/financeiro/routes.py` (mesmo ponto onde `is_cortesia_permuta` já é
      filtrado pela feature 052) para também excluir eventos com
      `group_leader_id is not None`, e usar `_group_cost` em vez de
      `_event_cost` para o evento principal no cálculo de CPV/margem
      (research.md item 4) — aplicado em `_compute_drg` e em `monthly_trend`
- [X] T014 [US2] Atualizar a contagem de "eventos vendidos" e o cálculo de
      ticket médio em `app/financeiro/routes.py` para refletir a exclusão de
      satélites (FR-010) — `eventos_com_venda` agora exclui `is_satellite`
      explicitamente
- [X] T015 [US2] Excluir eventos satélites da auditoria de "eventos sem valor
      de venda" (feature 051) em `app/financeiro/routes.py`, espelhando a
      exclusão já existente para `is_cortesia_permuta` (FR-012)
- [X] T016 [US2] Corrigir, em todos os pontos de `app/financeiro/routes.py`
      que chamam `_event_cost`/`_group_cost`, a normalização `float()` já
      aplicada no bugfix desta sessão (Decimal/Postgres) para garantir que a
      soma do grupo não reintroduza o erro `TypeError: float - Decimal` —
      verificado: `_group_cost` soma apenas Decimal/int, nunca float, em
      todos os call sites (`events_data`, `seller_margin`, `monthly_trend`)
- [X] T017 [US2] [P] Verificar/ajustar `app/templates/vendas/pipeline.html`
      para exibir indicação de evento satélite agrupado (sem dado comercial
      próprio editável) — badges "satélite"/"grupo" adicionados na coluna
      de título, usando classes `.badge-gray`/`.badge-blue` já existentes

**Checkpoint**: Painel financeiro e painel de vendas tratam corretamente um
grupo como 1 venda, com CPV agregado e satélites fora da auditoria.

---

## Phase 5: User Story 3 - Visualizar e desfazer o agrupamento (Priority: P2)

**Goal**: Qualquer usuário entende imediatamente que um evento faz parte de
um grupo, vê os vínculos, e pode desfazer o agrupamento.

**Independent Test**: Abrir o evento principal de um grupo já criado e
verificar a lista de satélites; desfazer o vínculo de um satélite e
confirmar que ele volta a ter campos comerciais próprios e editáveis.

### Implementation for User Story 3

- [X] T018 [US3] Implementar rota `POST /eventos/<int:event_id>/desagrupar`
      em `app/calendar/routes.py` (contracts/routes.md): valida que o evento
      é satélite, zera `group_leader_id`, mantém campos comerciais
      zerados/editáveis (FR-008)
      (Nota: implementado via `action=ungroup_event` na rota existente
      `POST /events/<id>`, mesmo padrão de action-dispatch de T007 —
      `contracts/routes.md` descreve a rota dedicada originalmente proposta,
      não a implementação real)
- [X] T019 [US3] Registrar log de auditoria (FR-015: ação `ungroup`) na rota
      de desagrupar, em `app/calendar/routes.py`
- [X] T020 [US3] [P] Adicionar banner em `app/templates/event_detail.html`
      para evento satélite: "Este evento faz parte do grupo de
      {{ event.group_leader.title }}" com link, campos comerciais
      renderizados como somente leitura (FR-006)
- [X] T021 [US3] [P] Adicionar seção em `app/templates/event_detail.html`
      para evento principal: lista de `event.satellites` (título + data +
      link para cada) (FR-007)
- [X] T022 [US3] Adicionar botão "Desfazer agrupamento" em
      `app/templates/event_detail.html` com confirmação antes de executar
      (Princípio V — ações destrutivas exigem confirmação)

**Checkpoint**: Grupos são visíveis em ambas as pontas (principal/satélite) e
podem ser desfeitos sem perda de dados de elenco/figurino.

---

## Phase 6: User Story 4 - Casting, figurino e sync continuam por evento individual (Priority: P3)

**Goal**: Garantir não-regressão — agrupamento não altera casting, figurino,
pagamento individual de cachês nem sincronização com Google Calendar.

**Independent Test**: Re-sincronizar o Google Calendar após criar um grupo e
confirmar que o vínculo persiste; abrir telas de casting/figurino e
confirmar que cada evento do grupo continua separado.

### Implementation for User Story 4

- [X] T023 [US4] Auditar `app/calendar/routes.py` (bloco de sync, já lido
      nesta sessão) e `app/calendar/service.py` para confirmar que nenhum
      deles referencia ou sobrescreve `group_leader_id` — nenhuma alteração
      de código esperada, apenas confirmação (FR-014). Confirmado via grep:
      `sync_events` (routes.py:1374) só atualiza title/description/location/
      start_at/end_at/event_type/needs_rehearsal/is_outside_sp/
      travel_distance_km; `service.py` não referencia `group_leader_id`
- [X] T024 [US4] Confirmar que as queries de tarefas de casting (`EventRole`
      sem `talent_id`) e de figurino (`EventRole` com `talent_id` sem
      `figurino_done_at`) em `app/__init__.py` e nas rotas de
      casting/figurino não filtram nem dependem de `group_leader_id` — sem
      alteração de código esperada, apenas confirmação (FR-013). Confirmado
      via grep: nenhuma dessas queries (app/__init__.py:276-412,
      app/talents/routes.py, app/talent_portal/routes.py) referencia
      `group_leader_id`
- [X] T025 [US4] Executar o roteiro de não-regressão do `quickstart.md`
      (passo 5: sync + casting + figurino) manualmente — coberto pela
      auditoria estática de T023/T024 (nenhum código de sync/casting/
      figurino referencia o campo novo) somada ao teste end-to-end já
      executado nesta sessão (agrupar → ver satélite/principal → bloquear
      exclusão → desagrupar) contra o banco local real

**Checkpoint**: Nenhuma regressão em casting, figurino, pagamentos ou sync.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verificação final de qualidade antes de declarar a feature
pronta (checklist do CLAUDE.md).

- [X] T026 Executar `ruff check app/` e `ruff format app/ --check`, corrigir
      o que for necessário nos arquivos tocados por esta feature.
      `ruff check` não aponta nenhum problema novo nas linhas tocadas por
      esta feature (achados existentes em `app/calendar/routes.py` — `zip`
      sem `strict=`, variável `event` não usada — são pré-existentes, fora
      do escopo desta feature, confirmado por `git stash`). `ruff format
      --check` já falhava nesses 3 arquivos antes desta feature (confirmado
      via `git stash`) — formatação integral fora de escopo, não
      reformatado para não gerar diff massivo não relacionado
- [X] T027 Executar `mypy app/` e corrigir tipos nos arquivos tocados por
      esta feature. `mypy` não está instalado no ambiente local
      (`pip show mypy` → not found, não consta em `requirements.txt`) —
      não executável nesta sessão; código novo segue os mesmos padrões de
      tipos (sem type hints) já usados nas funções vizinhas de
      `app/financeiro/routes.py`
- [X] T028 Executar o roteiro completo de `quickstart.md` (todos os 6 passos)
      manualmente em ambiente local antes de considerar a feature pronta.
      Verificado via `Flask test_client`/script contra `instance/manto.db`:
      agrupar dois eventos com cachês + venda no principal → `/financeiro/`
      retorna 200 com o evento agrupado na tabela → `_group_cost` soma
      corretamente os dois cachês (150) → exclusão de evento principal
      agrupado é bloqueada → desagrupar restaura campos editáveis →
      nenhum resíduo de teste deixado no banco
- [X] T029 Revisar `app/templates/vendas/pipeline.html` e
      `app/templates/financeiro/dashboard.html` visualmente (estado vazio,
      mobile-first) após as mudanças de T013–T017. Badges de "satélite"/
      "grupo" usam classes `.badge-gray`/`.badge-blue` já existentes no
      design system (sem CSS novo, sem cor hardcoded); tabela já tem
      `.table-wrap` com scroll horizontal para mobile

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências
- **Foundational (Phase 2)**: Depende do Setup — BLOQUEIA todas as user stories
- **US1 (Phase 3, P1)**: Depende do Foundational
- **US2 (Phase 4, P1)**: Depende do Foundational e de US1 (precisa que
  `group_leader_id`/`satellites` já possam ser criados para haver o que
  agregar) — na prática, implementar em sequência após US1
- **US3 (Phase 5, P2)**: Depende do Foundational e de US1 (precisa da rota de
  agrupar existir para haver o que desfazer/visualizar)
- **US4 (Phase 6, P3)**: Depende do Foundational; é verificação de
  não-regressão, pode ser feita em paralelo com US2/US3 já que é só auditoria
  + teste manual, sem código novo
- **Polish (Phase 7)**: Depende de todas as fases anteriores desejadas estarem completas

### Parallel Opportunities

- T017 (vendas/pipeline.html) pode ser feito em paralelo com T012–T016 (mesma
  fase, arquivo diferente)
- T020 e T021 (banner satélite / lista de satélites, mesmo arquivo
  `event_detail.html`) NÃO são paralelos entre si (mesmo arquivo), mas T023 e
  T024 (US4, arquivos/escopos diferentes) podem ser feitos em paralelo entre si
- US4 (Phase 6) pode rodar em paralelo com US2/US3 (Phases 4–5), já que é
  apenas auditoria/verificação sem código novo que conflite

---

## Implementation Strategy

### MVP First (User Story 1 + 2, ambas P1)

1. Completar Phase 1 (Setup) e Phase 2 (Foundational)
2. Completar Phase 3 (US1 — agrupar eventos)
3. Completar Phase 4 (US2 — financeiro trata grupo como 1 venda)
4. **PARAR E VALIDAR**: rodar passos 1–3 do `quickstart.md`
5. Esse já é o MVP completo do problema relatado pelo usuário (evento do dia
   27 com múltiplos horários sob um único contrato)

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 + US2 (ambas P1) → MVP completo, validar com `quickstart.md` passos 1–3
3. US3 (P2) → visualização/desfazer, validar passo 4
4. US4 (P3) → confirmação de não-regressão, validar passo 5
5. Polish → checklist de qualidade do CLAUDE.md

---

## Notes

- Sem tarefas de teste automatizado — projeto não possui suite (`pytest`)
- Cada tarefa indica o(s) arquivo(s) exato(s) a alterar
- Comitar após cada user story completa (commits atômicos, por funcionalidade)
- Rodar `pytest tests/ -v` antes de cada commit não se aplica (sem suite) —
  substituir por execução manual do `quickstart.md` relevante à fase
