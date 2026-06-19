# Tasks: Vincular um ensaio existente a um evento pai

**Feature**: `063-vincular-ensaio-pai` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Reusa `parent_event_id`/`ensaios` e `_CAN_ENSAIO`. Sem migration. Verificação contra
**`manto_local` (Postgres)**.

---

## Fase 1 — Backend

- [X] T001 [US1] `app/calendar/routes.py` — nova rota `POST /events/<int:ensaio_id>/link-parent` (`@login_required`; checar `_CAN_ENSAIO` senão 403): exige `ensaio.event_type == "ENSAIO"` (senão 400); lê `parent_event_id`; valida pai (existe, `event_type != "ENSAIO"`, `!= ensaio.id`) — inválido/vazio → flash erro + redirect sem mudar; válido → `ensaio.parent_event_id = parent.id`, commit, `EventLog`, flash sucesso; redireciona para a página do ensaio.
- [X] T002 [US1] `app/calendar/routes.py` — no branch ENSAIO de `event_detail`, passar `candidate_shows` = `CalendarEvent` com `event_type != "ENSAIO"` e `id != event.id`, ordenado por `start_at` desc.

## Fase 2 — UI

- [X] T003 [US1] `app/templates/ensaio_detail.html` — no bloco "Show de origem", para `show_ensaio`, adicionar form (`POST .../link-parent`) com input de busca + `<select name="parent_event_id">` listando `candidate_shows` (título + data) e botão **Vincular** (rótulo "Trocar show" se já houver `parent`). Filtro JS simples por nome sobre as opções.

## Fase 3 — Verificação

- [X] T004 Verificar contra **`manto_local`**: vincular um ensaio órfão a um show (vínculo persiste; ensaio aparece em `show.ensaios`); trocar o pai; rejeição de pai inválido (outro ensaio / próprio / vazio); rota exige `_CAN_ENSAIO`. `ruff check` sem erros novos (comparar `git stash`).

---

## Dependências

- T001 e T002 antes de T003. T004 ao final.

## MVP

T001+T002+T003 entregam o pedido (vincular órfão a um show pela página do ensaio).
