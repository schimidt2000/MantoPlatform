# Tasks: Alternar filtro de avaliações por data (075)

**Feature**: `075-avaliacoes-filtro-data` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem modelo/migration. Verificação contra **`manto_local`**.

---

## Fase 1 — Backend (US1)

- [X] T001 [US1] `app/talents/routes.py::avaliacoes`: ler `date_mode` (`evento` padrão | `avaliacao`); definir `_date_col = EventRating.submitted_at if date_mode=='avaliacao' else CalendarEvent.start_at`.
- [X] T002 [US1] Aplicar `_date_col` no filtro de período de `ratings_q` (>= start, < end) e em `rated_q` (seletor de eventos), no lugar de `CalendarEvent.start_at`.
- [X] T003 [US1] Passar `date_mode` ao template e indicar no `recorte_label` quando for "por data da avaliação".

## Fase 2 — UI (US1)

- [X] T004 [US1] `app/templates/talents/avaliacoes.html`: linha "Filtrar por:" com dois chips (Data do evento / Data da avaliação) usando `setFilter({date_mode: ...})`; oculta quando `event_id` (período não se aplica). Padrão destaca "Data do evento".

## Fase 3 — Verificação

- [X] T005 Contra **`manto_local`**: em `evento` os números batem com o atual; em `avaliacao`, avaliação recente de evento antigo aparece no período curto e some no longo; trocar critério mantém período/categoria; `ruff check` sem erros novos.

---

## Dependências

- T001 → T002 → T003 → T004 → T005.

## MVP

T001–T004 entregam o alternador; T005 valida sem regressão.
