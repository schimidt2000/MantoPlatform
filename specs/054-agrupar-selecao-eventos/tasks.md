---
description: "Task list for feature 054 — Seleção de eventos no agrupamento (busca + multi-seleção)"
---

# Tasks: Seleção de eventos no agrupamento (busca + multi-seleção)

**Input**: Design documents from `specs/054-agrupar-selecao-eventos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/group-events.md, quickstart.md

**Tests**: Não solicitados e o projeto não possui suíte automatizada
(`pytest`/`conftest.py` inexistentes) — verificação manual via `quickstart.md`, como nas
features 051/052/053.

**Organização**: Tarefas por user story (US1–US3 de `spec.md`), ordem P1 → P1 → P2.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: Nada a preparar — sem dependências novas, sem migration (modelo da 053
reutilizado). Esta fase é intencionalmente vazia.

- [X] T001 Confirmar que a feature 053 está aplicada (coluna `group_leader_id`,
      `_handle_group_events`, `_apply_satellite`, propriedades `is_satellite`/
      `is_group_leader`) — base reutilizada por esta feature, sem novo schema

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Trocar a fonte de candidatos (remover a janela ±3 dias) — todas as user
stories dependem da lista ampla de eventos elegíveis.

**⚠️ CRITICAL**: Nenhuma user story funciona antes desta fase.

- [X] T002 Em `app/calendar/routes.py` (rota `event_detail`), substituir a query de
      `groupable_events` que usa janela de ±3 dias (`window_start`/`window_end`) por
      todos os eventos não-ENSAIO exceto o próprio, ordenados por `start_at` desc; manter
      o passe de `groupable_events` ao `render_template` (data-model.md, research.md item 3)

**Checkpoint**: A lista de candidatos passa a conter todos os eventos elegíveis.

---

## Phase 3: User Story 1 - Buscar e marcar vários eventos para agrupar (Priority: P1) 🎯 MVP

**Goal**: Buscar qualquer evento (nome/data) e marcar vários por checkbox para agrupar de
uma só vez.

**Independent Test**: Abrir evento, buscar um evento de data distante, marcar dois e
confirmar que ambos entram no grupo.

### Implementation for User Story 1

- [X] T003 [US1] Em `app/calendar/routes.py`, estender `_handle_group_events` para ler
      `request.form.getlist("target_event_ids")` (múltiplos) no lugar do
      `target_event_id` único; resolver os eventos alvo e montar o conjunto de
      participantes (atual + alvos) — manter `action=group_events` em `_EVENT_ACTIONS`
      (contracts/group-events.md)
- [X] T004 [US1] Em `app/calendar/routes.py`, aplicar o agrupamento em laço atômico:
      para cada participante que não é o principal, chamar `_apply_satellite` + setar
      `group_leader_id` e gravar `EventLog`; um único `db.session.commit()` ao final;
      flash de sucesso com a contagem de satélites (contracts/group-events.md)
- [X] T005 [US1] Em `app/templates/event_detail.html`, substituir o `<select
      name="target_event_id">` por uma **lista de checkboxes** (`name="target_event_ids"`)
      dos `groupable_events`, cada item com título + data/hora; manter dentro do
      `<details>` "Agrupar a outro evento"
- [X] T006 [US1] Em `app/templates/event_detail.html`, adicionar um campo de busca acima
      da lista e o JS de filtragem em tempo real, **reaproveitando** o helper de
      normalização acento-insensível de `app/templates/financeiro/pagamentos.html`
      (`toLowerCase().normalize('NFD')...`) — filtra por título e data (research.md item 2)
- [X] T007 [US1] Em `app/templates/event_detail.html`, exibir estado vazio da busca
      ("nenhum evento encontrado") e garantir que a lista inicial apareça sem texto
      digitado (FR-005, edge case de busca sem resultado)

**Checkpoint**: Busca funciona; múltiplos eventos podem ser marcados e agrupados numa só
ação sob o evento atual.

---

## Phase 4: User Story 2 - Escolher qual evento é o principal depois da seleção (Priority: P1)

**Goal**: Depois de marcar o conjunto, indicar qual evento é o principal (atual como
padrão).

**Independent Test**: Marcar 3 eventos, escolher um deles como principal, confirmar e
verificar que o escolhido virou principal e os outros satélites.

### Implementation for User Story 2

- [X] T008 [US2] Em `app/templates/event_detail.html`, montar a escolha do principal
      (`name="leader_event_id"`, radios) com o evento atual + os eventos marcados, com o
      atual pré-selecionado; atualizar as opções no cliente conforme os checkboxes são
      marcados/desmarcados (research.md item 7, FR-004)
- [X] T009 [US2] Em `app/calendar/routes.py`, validar em `_handle_group_events` que
      `leader_event_id` ∈ {evento atual} ∪ {alvos selecionados}; recusar com aviso caso
      contrário (contracts/group-events.md regra 3)

**Checkpoint**: O principal é escolhido corretamente entre os participantes; os demais
viram satélites dele.

---

## Phase 5: User Story 3 - Confirmação e preservação das regras de integridade (Priority: P2)

**Goal**: Multi-seleção não pode regredir as proteções da 053 nem perder a seleção em erro.

**Independent Test**: Tentar incluir um evento já satélite e confirmar recusa clara sem
agrupar os demais; após erro, a seleção é preservada.

### Implementation for User Story 3

- [X] T010 [US3] Em `app/calendar/routes.py`, garantir no laço de validação de
      `_handle_group_events` que TODAS as regras da 053 valem para cada participante
      (já satélite, já principal, ENSAIO, auto-agrupamento) e que a falha de qualquer um
      recusa a operação inteira sem alterar o banco — indicando o evento problemático
      (contracts/group-events.md regras 5–7, atomicidade)
- [X] T011 [US3] Em `app/calendar/routes.py`, manter a confirmação `confirm_clear_financials`
      agora avaliada sobre o conjunto: se qualquer satélite resultante tem `sale_value`,
      exigir a confirmação antes de zerar (FR-008)
- [X] T012 [US3] Em `app/templates/event_detail.html`, renderizar os eventos já agrupados
      (`is_satellite` ou `is_group_leader`) como itens **desabilitados** com etiqueta
      "já agrupado" (não selecionáveis) — FR-006, research.md item 4
- [X] T013 [US3] Em `app/templates/event_detail.html`, adicionar validação client-side no
      envio: exigir ≥1 marcado e principal escolhido (destaque/foco, sem bloquear em
      silêncio); manter o checkbox de confirmação de substituição quando algum marcado tem
      venda; desabilitar o botão ao enviar (anti-duplo-envio) — Princípio V, FR-010

**Checkpoint**: Proteções intactas; erros comuns barrados no cliente sem perder a seleção;
botão não duplica envio.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Qualidade final (Portões da constituição).

- [X] T014 Executar `ruff check app/calendar/routes.py` e `ruff format --check` nos
      arquivos tocados; corrigir o que for novo nesta feature
- [X] T015 Executar o `quickstart.md` (passos 1–6) no app real, incluindo a equivalência
      com a 053 no Painel Financeiro (FR-012/SC-005) e a não-regressão do caminho N=1

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: confirmação apenas; sem bloqueio real.
- **Foundational (Phase 2)**: BLOQUEIA todas as user stories (lista de candidatos).
- **US1 (Phase 3, P1)**: depende do Foundational. É o MVP.
- **US2 (Phase 4, P1)**: depende de US1 (precisa dos checkboxes para montar a escolha do
  principal). Implementar em sequência após US1.
- **US3 (Phase 5, P2)**: depende de US1/US2 (valida o fluxo de multi-seleção).
- **Polish (Phase 6)**: depende de tudo anterior.

### Parallel Opportunities

- T005, T006, T007 tocam o mesmo arquivo (`event_detail.html`) — **não** paralelizáveis
  entre si. T003/T004 (routes.py) podem ser feitos enquanto se edita o template, mas como
  o handler e a UI compartilham o contrato, recomenda-se sequência.
- Há poucos arquivos (2) — paralelismo real é mínimo nesta feature.

---

## Implementation Strategy

### MVP (US1 + US2, ambas P1)

1. Phase 2 (lista ampla) → Phase 3 (busca + multi-seleção) → Phase 4 (escolher principal).
2. **PARAR E VALIDAR**: passos 1–3 do `quickstart.md`. Já resolve a dor relatada.

### Incremental

1. Foundational → base.
2. US1 + US2 → MVP, validar quickstart 1–3.
3. US3 → proteções + preservação de seleção, validar quickstart 4–5.
4. Polish → ruff + quickstart completo (6).

---

## Notes

- Sem tarefas de teste automatizado (projeto sem suíte) — verificação via `quickstart.md`.
- Sem migration: modelo da 053 reutilizado integralmente.
- Comitar a feature como um commit atômico após validação (Princípio IV).
