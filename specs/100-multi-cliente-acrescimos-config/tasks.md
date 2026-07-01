# Tasks: Múltiplos clientes + tipos de acréscimo configuráveis + redesign

**Feature**: 100-multi-cliente-acrescimos-config | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Testar contra `manto_local`. Migração manual + data-migrate (down_revision `d6a7b8c9e0f1`).

## Phase 1 — Modelo + migração de clientes (US1, P1) 🎯 MVP

- [ ] **T001** Em [constants.py](../../app/constants.py): `CLIENT_RELATION_TIPOS`
  (Contratante, Assessora, Mãe/Pai, Familiar, Outros).

- [ ] **T002** Em [models.py](../../app/models.py): `class EventClient` (event_id, client_id,
  relationship_type, created_at) + relationship `CalendarEvent.event_clients` (cascade). Property
  `clients_list`.

- [ ] **T003** Migração manual `migrations/versions/<hash>_event_clients.py` (down_revision
  `d6a7b8c9e0f1`): cria `event_clients` e **copia** os `calendar_events.client_id` não nulos como
  associação 'Contratante'. Aplicar/validar em `manto_local`. Cobre FR-005.

## Phase 2 — Backend multi-cliente (US1)

- [ ] **T004** `_handle_update_comercial` ([calendar/routes.py](../../app/calendar/routes.py)): ler
  `client_id[]` + `client_relation[]`; recriar `EventClient`; sincronizar `event.client_id` com o
  contratante (ou primeiro); regra: ≥1 cliente quando `event_requires_client`. Cobre FR-001, FR-002, FR-003.

- [ ] **T005** [clientes/routes.py](../../app/clientes/routes.py): `index` (contagem por evento) e
  `detail` (eventos do cliente) via `EventClient`; `delete` remove as associações. Cobre FR-004.

## Phase 3 — UI multi-cliente + relação (US1, US3)

- [ ] **T006** [event_detail.html](../../app/templates/event_detail.html): editor de **clientes** (linhas
  com busca/seleção + seletor de **relação** + remover; criação rápida) no lugar do picker único; envia
  `client_id[]`/`client_relation[]`. Reusa `/clientes/search` e `/clientes/quick-create`. Cobre FR-002.

- [ ] **T007** [clientes/detail.html](../../app/templates/clientes/detail.html): mostrar os eventos do
  cliente (via associação) com a **relação** naquele evento. Cobre FR-004.

## Phase 4 — Tipos de acréscimo configuráveis (US2)

- [ ] **T008** [orcamento/settings.py](../../app/orcamento/settings.py): `DEFAULTS["acrescimo_tipos"]`
  (lista atual) + helper `acrescimo_tipos_list()` = salvos + BV + Outro (dedup, BV protegido); `_migrate`
  injeta a chave se ausente. Cobre FR-007, FR-008.

- [ ] **T009** [orcamento/settings.html](../../app/templates/orcamento/settings.html) + POST em
  [orcamento/routes.py](../../app/orcamento/routes.py): editor da **lista de tipos** (add/remover; BV/Outro
  fixos e BV não-removível). Cobre FR-006, FR-007.

- [ ] **T010** Substituir `ACRESCIMO_TIPOS` (constants) pelo helper de config onde é passado aos templates
  ([orcamento/routes.py](../../app/orcamento/routes.py), [calendar/routes.py](../../app/calendar/routes.py)).
  BV detectado por `tipo == 'BV'` (inalterado). Cobre FR-008, FR-009.

## Phase 5 — Redesign do editor de acréscimos (US3)

- [ ] **T011** [orcamento/index.html](../../app/templates/orcamento/index.html) e
  [event_detail.html](../../app/templates/event_detail.html): editor de acréscimos redesenhado (cards/
  linhas alinhadas, rótulos, estado vazio, R$/% evidente, BV destacado). Sem mudar cálculo/salvamento.
  Cobre FR-010, FR-011, FR-012.

## Phase 6 — Verificação e qualidade

- [ ] **T012** Verificação contra `manto_local`: (a) 2 clientes com relações salvam/reexibem; (b)
  migração preservou vínculos como Contratante; (c) ficha do cliente lista eventos por associação; (d)
  regra ≥1 cliente; (e) adicionar/remover tipo de acréscimo (BV protegido); (f) acréscimos calculam/salvam
  idêntico. Cobre SC-001..SC-005.

- [ ] **T013** [P] `ruff` nos arquivos Python alterados; Jinja parse; JS balanceado; boot do app.

## Dependências

- T001→T002→T003. Phase 2 depende de T003. Phase 3 depende de Phase 2. Phase 4 (T008→T009→T010)
  independe de clientes. Phase 5 depende de Phase 4 (tipos via helper). Phase 6 ao final.

## Critério de pronto

- Vários clientes por evento com relação; migração sem perda; ficha via associação; ≥1 cliente exigido.
- Tipos de acréscimo editáveis nas configurações (BV protegido); editor redesenhado sem regressão.
- Checklist "Pronto" do CLAUDE.md (ruff + verificação em `manto_local`).
