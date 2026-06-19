# Tasks: Múltiplos ensaios por evento + página de ensaio simplificada

**Feature**: `062-ensaios-multiplos-pagina` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Reusa o vínculo `ensaios` e as rotas de ensaio existentes. Sem migration. Verificação contra
**`manto_local` (Postgres)**.

Convenção: `[P]` = paralelizável; `[US#]` = história relacionada.

---

## Fase 1 — Backend (rotas)

- [X] T001 [US2] `app/calendar/routes.py` — em `event_detail`, após o tratamento de POST e a montagem de `logs`, adicionar branch: se `event.event_type == "ENSAIO"`, renderizar `ensaio_detail.html` (contexto: `event`, `parent=event.parent`, `logs`, `show_ensaio` via `_CAN_ENSAIO`, `settings`) e **retornar** antes das consultas pesadas.
- [X] T002 [US1] `app/calendar/routes.py` — `create_ensaio`: ler `redirect_to` do form; se `"home"`, redirecionar para `home` após criar; senão manter `event_detail` do show.
- [X] T003 [US2] `app/calendar/routes.py` — `edit_ensaio`: adicionar `redirect_to == "ensaio"` → `event_detail(ensaio_id)` (volta à página simplificada). Manter `"event"` e default.

## Fase 2 — Página simplificada (US2)

- [X] T004 [US2] Criar `app/templates/ensaio_detail.html` (estende `base.html`): cabeçalho com selo ENSAIO; card data/hora + local + descrição; bloco "Show de origem" (link para `/events/<parent.id>` se houver, ou aviso de órfão); se `show_ensaio`: form inline de **editar** (→ `/events/<id>/edit-ensaio`, `redirect_to=ensaio`) e botão **cancelar** (→ `/events/<id>/delete-ensaio`); histórico (logs) opcional. Sem painéis de show.

## Fase 3 — Marcar múltiplos (US1)

- [X] T005 [US1] `app/templates/home.html` — no card "Ensaios agendados" de cada show, adicionar um **"+ Marcar outro ensaio"** (toggle + form inline) postando em `/events/<show_id>/create-ensaio` com `redirect_to=home` (data/início/fim/descrição/local mínimo, reusando os campos do form do evento).
- [X] T006 [US1] `app/templates/event_detail.html` — quando `event.ensaios` já existir, o `summary` do form passa a "Marcar outro ensaio" (clareza); form continua sempre disponível (FR-002).

## Fase 4 — Verificação

- [X] T007 Verificar contra **`manto_local`**: criar 2 ensaios num show (ambos persistem/aparecem); GET da página de um ensaio não traz painéis de show e traz o vínculo; editar/cancelar funcionam; órfão ok. `ruff check` sem erros novos (comparar com `git stash`).

---

## Dependências

- T001 antes de T004 (template consumido pela rota). T002 antes/junto de T005. T003 com T004.
- T007 ao final.

## MVP

T001+T004 (página simplificada) e T002+T005 (marcar outro na home) entregam as duas metades.
