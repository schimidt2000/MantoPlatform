# Tasks: Avaliação não aparece para talento incluído (085)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: User Story 1 — Talento incluído consegue avaliar (P1) 🎯 MVP

- [X] T001 [US1] Adicionar `or_` ao import do SQLAlchemy e helper `_not_rejected()` (cláusula
  `or_(invite_status IS NULL, invite_status != 'rejected')`) em `app/talent_portal/routes.py`.
- [X] T002 [US1] `_rateable_event_ids`: usar `_not_rejected()` e janela
  `or_(event_end >= window7, assigned_at >= window7)` (mantendo `event_end < now`) em
  `app/talent_portal/routes.py`.
- [X] T003 [US1] `_editable_rating_event_ids`: usar `_not_rejected()` e janela por
  `or_(event_end >= window30, assigned_at >= window30)` em `app/talent_portal/routes.py`.
- [X] T004 [US1] `rate_event` (GET) e `submit_rating` (POST): trocar `invite_status == "accepted"` por
  `_not_rejected()` no `first_or_404()`, mantendo a guarda `_event_ended` em
  `app/talent_portal/routes.py`.

## Phase 2: Polish & Verificação

- [X] T005 Verificar contra `manto_local`: role simulada da Erika (assigned_at=agora, pending) faz #198
  entrar em `_rateable_event_ids` e passar no guard de `rate_event`; `rejected` não entra; evento não
  terminado não entra; antigo fora da janela não entra. Rodar `ruff` (sem erros novos).

## Dependencies

- T001 → T002, T003, T004 (helper antes dos usos).
- Tudo no mesmo arquivo → sequencial.
- T005 por último.

## MVP

User Story 1 é a feature inteira (correção do bug).
