# Tasks: Evento que cruza a meia-noite (071)

**Feature**: `071-evento-cruza-meia-noite` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem modelo/migration. Verificação do ciclo contra **`manto_local`**.

---

## Fase 1 — Helper compartilhado

- [X] T001 `app/calendar/routes.py`: criar `_build_start_end(d, start_str, end_str)` que combina data+horas e, se `et < st`, soma 1 dia ao fim (cruza a meia-noite). Levanta `ValueError` p/ horário inválido.

## Fase 2 — Aplicar nos 3 fluxos (US1/US2)

- [X] T002 [US1] `create_event`: usar `_build_start_end`; remover o erro `et <= st` e manter erro só quando `et == st`.
- [X] T003 [US2] `create_ensaio`: idem (helper + erro só em `et == st`).
- [X] T004 [US2] `edit_ensaio`: idem.

## Fase 3 — Frontend (US1)

- [X] T005 [US1] `app/templates/event_create.html`: validação JS (linha ~868) passa a bloquear só quando `fim == início` (permitir `fim < início`); adicionar aviso "termina no dia seguinte" quando `fim < início`.

## Fase 4 — Verificação

- [X] T006 Contra **`manto_local`**: criar evento 20:00→00:30 → `end_at` no dia seguinte (4h30); mesmo-dia inalterado; início==fim rejeitado; ensaio overnight ok. `ruff check` sem erros novos.

---

## Dependências

- T001 → (T002, T003, T004). T005 independe do backend. T006 ao final.

## MVP

T001+T002 (criar evento overnight). T003–T005 completam (ensaios + UI).
