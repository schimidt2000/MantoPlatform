# Tasks: adicionar/remover cargo (147)

## Backend
- [X] T001 `casting_ops.add_role(event, *, character_name, talent_id, cache_value, role_type,
      actor_name, tz)` — extrai `_handle_add_role`; cachê via `parse_brl`; log + convite se tem
      talento. `casting_ops.delete_role(event, role, *, is_superadmin, actor_name, tz)` — extrai
      `_handle_delete_role` (accepted→só superadmin; log; delete). Retornam cargo / bool.
- [X] T002 `routes.py`: `_handle_add_role` e `_handle_delete_role` viram wrappers finos; o do
      delete busca o role com `int(role_id)` (corrige o bug psycopg3 `filter_by(id=string)`).
- [X] T003 `agenda_write.py`: `POST /api/events/<id>/roles` (gate `_CAN_EDIT_EVENT`; 400 nome
      vazio) e `DELETE /api/roles/<id>` (gate CASTING/SUPERADMIN; 403 se accepted e não-SA).
      Ambos retornam `serialize_event_detail`.

## Frontend
- [X] T004 [P] `lib/casting.ts`: `useAddRole(eventId)`, `useDeleteRole(eventId)` (atualizam o
      cache `["event", id]` com o evento retornado).
- [X] T005 `EventDetailPage.tsx`: form "adicionar cargo" (nome + talento opcional + cachê) abaixo
      do elenco quando `show_casting`; botão remover por cargo (com confirmação).

## Verificação
- [X] T006 `scripts/db/verify_147_cargo.py`: add via API vs Jinja (paridade de linha); delete
      via API vs Jinja; delete de cargo `accepted` bloqueado p/ não-SA; 403/404/400;
      idempotência do delete (2º delete → 404). E-mail mockado. Jinja 302. ruff/tsc/build.

## Fase final
- [X] T007 Commit, verificar na main mergeada, merge+push; `CLAUDE.md` pointer + memória.
