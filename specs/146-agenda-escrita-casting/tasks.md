# Tasks: escrita de casting — fatia P1 escalar (146, US1)

**Escopo**: só a User Story 1 (escalar/atualizar talento). US2 (adicionar/remover cargo) e
US3 (convite/dispensar/restaurar/figurino) têm seu próprio ciclo depois, reusando o padrão.

## Backend
- [X] T001 [US1] Criar `app/calendar/casting_ops.py` com `assign_role(event, role, *,
      talent_id, cache_value, travel_cache, actor_name, is_superadmin, tz)`: extrai o núcleo de
      `_handle_assign_casting` (cap, transições de invite, reset de figurino, EventLog, e-mails
      via `send_async`). Sem `request.form`/`flash`/`current_user`. Retorna `{message, ok}`.
- [X] T002 [US1] Refatorar `_handle_assign_casting` em `app/calendar/routes.py` para wrapper
      fino: lê `request.form` + `current_user`, chama `assign_role(...)`, `flash(result.message)`.
      Comportamento idêntico ao atual.
- [X] T003 [US1] Criar `app/api/agenda_write.py`: `POST /api/roles/<int:role_id>/assign` — RBAC
      (CASTING/SUPERADMIN; 403 senão), 404 se role inexistente; lê JSON, chama `assign_role`,
      retorna `serialize_event_detail(event, current_user, impersonate)`. Registrar em
      `app/api/__init__.py`.

## Frontend
- [X] T004 [P] [US1] `frontend/apps/internal/src/lib/casting.ts`: `useAssignRole(eventId)`
      (mutation TanStack Query → POST assign; ao suceder, atualiza o cache de `["event", id]`
      com o evento retornado).
- [X] T005 [US1] `EventDetailPage.tsx`: no bloco de elenco, quando `flags.show_casting`, cada
      cargo ganha ação de escalar — seletor de talento + `MoneyInput` de cachê + botão com
      feedback de pending (Princípio V). Usa `useAssignRole`. Transição suave no resultado.

## Verificação
- [X] T006 [US1] `scripts/db/verify_146_casting_write.py` (gitignored): monkeypatch de
      `send_async`; escalar via API → estado esperado (talento/cap/assigned_at/invite=pending/
      figurino resetado/EventLog/1 convite); **paridade** com o caminho Jinja (form) num cargo
      gêmeo; 403; 404; idempotência (reenvio não duplica). Coexistência: POST `/events/<id>`
      Jinja segue 200 (302 redirect). `ruff` nos arquivos novos; `tsc`/`build` limpos.

## Fase final
- [X] T007 Marcar tasks; commit no branch `146-...`; verificar na main mergeada; merge+push.
      `CLAUDE.md` pointer + memória. Changelog só quando substituir algo em produção (equipe
      segue no Jinja) — não republicar agora.

## Dependências
- T001 → T002/T003 (ambos chamam `assign_role`). T004 → T005. Verificação por último.
- Nenhuma mudança de schema. O handler Jinja muda de forma (wrapper) mas não de efeito —
  garantido pela verificação de paridade (Princípio IV).
