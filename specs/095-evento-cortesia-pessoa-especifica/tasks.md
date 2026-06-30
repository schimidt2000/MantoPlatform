# Tasks: Evento cortesia/permuta e pessoa específica na criação

**Feature**: 095-evento-cortesia-pessoa-especifica | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Sem migração (reusa `is_cortesia_permuta`, `EventRole.talent_id/assigned_at`). Testar contra
> `manto_local`. `[P]` = paralelizável (arquivos distintos).

## Phase 1 — Cortesia/permuta na criação (US1, P1) 🎯 MVP

- [ ] **T001** Em [event_create.html](../../app/templates/event_create.html): adicionar checkbox
  **"Cortesia / permuta (sem venda)"** na seção de venda + JS que, quando marcado, remove o `required`
  dos campos de valor e dá feedback visual (esmaece/oculta valores) e nota explicativa. Cobre FR-001.

- [ ] **T002** Em `create_event` ([calendar/routes.py](../../app/calendar/routes.py)): ler
  `is_cortesia_permuta`; quando marcado, **pular** os erros de "valor antes do desconto" e "valor de
  venda" (linhas ~2447-2452) e, ao montar o `CalendarEvent`, setar `sale_value=0`,
  `is_cortesia_permuta=True` (e `sale_value_gross` 0/None). Cobre FR-002, FR-003.

- [ ] **T003** Garantir que, **sem** a marcação, as validações de valor permanecem (venda normal). Cobre
  FR-004, SC-002.

## Phase 2 — Pré-escala de artista por personagem (US2, P1)

- [ ] **T004** Passar ao template do GET de `create_event` a lista de talentos atribuíveis
  (`id`, nome) para o autocomplete (consulta `Talent` status active, ordenada por nome).

- [ ] **T005** Em [event_create.html](../../app/templates/event_create.html) `buildCharRow`: adicionar,
  por linha de personagem, um **seletor de talento** (autocomplete da lista embutida) que preenche um
  hidden `char_talent_id[]` alinhado a `character_names[]`. Cobre FR-005, FR-009.

- [ ] **T006** Em `create_event` POST: ler `char_talent_id[]`; ao criar cada `EventRole` de personagem,
  se houver talento válido → setar `talent_id` + `assigned_at` (sem `invite_status`). Vaga sem seleção
  permanece aberta. Cobre FR-007, FR-008.

## Phase 3 — Pré-escala de coordenador específico (US3, P2)

- [ ] **T007** Em [event_create.html](../../app/templates/event_create.html): seletor **"Coordenador
  específico"** (mesmo autocomplete) → hidden `coordinator_talent_id`. Cobre FR-006.

- [ ] **T008** Em `create_event` POST: se `coordinator_talent_id` válido, criar a vaga "Coordenador"
  (extra) já com `talent_id` + `assigned_at` (ajustar/uso de `_ensure_coordinator` para não duplicar a
  vaga). Sem seleção → vaga vazia como hoje. Cobre FR-007, FR-008.

## Phase 4 — Sinalização de conflito (FR-010)

- [ ] **T009** Extrair helper `_talent_time_conflict(talent_id, start, end, exclude_event_id)` a partir
  da lógica existente (~linhas 1352-1363) e, após criar o evento, **flash** de aviso listando talentos
  pré-escalados com conflito de horário. Não bloqueia. Cobre FR-010, SC-005.

## Phase 5 — Verificação e qualidade

- [ ] **T010** [P] Verificação contra `manto_local`: (a) criar cortesia sem valor → venda=0,
  is_cortesia_permuta=True; (b) venda normal sem valor → erro; (c) personagem com talento → vaga
  atribuída; sem talento → aberta; (d) coordenador específico → vaga de Coordenador atribuída; (e)
  talento com conflito → flash de aviso. Cobre SC-001..SC-005, FR-011.

- [ ] **T011** [P] `ruff format`/`ruff check` nos trechos alterados; smoke de render do
  `event_create.html` (Jinja parse) e boot do app.

## Dependências

- T001→T002→T003 (cortesia). T004→T005→T006 (artista). T007→T008 (coordenador). T009 após T006/T008.
- Phase 5 ao final.

## Critério de pronto

- Cortesia/permuta criável sem valor (venda=0); venda normal intacta.
- Personagem/coordenador nascem pré-escalados quando há talento; abertos quando não.
- Casting envia convite normalmente; conflitos sinalizados.
- Checklist "Pronto" do CLAUDE.md (ruff + verificação em `manto_local`).
