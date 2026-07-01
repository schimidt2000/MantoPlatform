# Tasks: Convite do portal — detalhes de evento e ensaio bem organizados

**Feature**: 102-portal-convite-ensaio-detalhes | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Mudança apenas de template ([portal/home.html](../../app/templates/portal/home.html)). Sem migração.

## Phase 1 — Convite pendente: evento rotulado (US3)

- [ ] **T001** No bloco de **convite pendente**, renomear os rótulos do evento para **Data do evento**,
  **Horário do evento** e **Local do evento**; manter `ev.location` completo (linha omitida se vazio).
  Cobre FR-006, FR-007.

## Phase 2 — Convite pendente: ensaio organizado + fim (US1, US2)

- [ ] **T002** No bloco de **convite pendente**, transformar cada ensaio em linhas rotuladas: cabeçalho
  "🎭 Ensaio", **Data do ensaio**, **Horário do ensaio** (`start_at` – `end_at`; só início se sem fim),
  **Local do ensaio** (omitido se vazio), seguidos de **observação** e **materiais** como hoje. Cobre
  FR-001, FR-002, FR-003, FR-004, FR-005.

## Phase 3 — Próximos eventos: fim do ensaio (US1, FR-008)

- [ ] **T003** No bloco de **próximos eventos**, incluir o **fim** do ensaio (início–fim) mantendo o
  estilo compacto. Cobre FR-008.

## Phase 4 — Verificação

- [ ] **T004** Jinja parse do `portal/home.html`; verificação dos casos: ensaio com/sem fim, ensaio
  sem local, vários ensaios, local do evento vazio. Boot do app. Cobre SC-001..SC-004.

## Dependências

- T001, T002, T003 são independentes (mesmo arquivo, blocos distintos). T004 ao final.

## Critério de pronto

- Ensaio exibe início–fim e fica organizado em Data/Horário/Local; evento rotulado como "do evento" com
  endereço completo; vários ensaios claros; próximos eventos com fim do ensaio. Checklist "Pronto".
