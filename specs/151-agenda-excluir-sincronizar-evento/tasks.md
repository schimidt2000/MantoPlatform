# Tasks: excluir e sincronizar evento em React (151)

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
Padrão de 146-150: núcleo compartilhado → adaptadores finos (Jinja + API) → React → verificação por
paridade contra `manto_local`. Exceção justificada: o núcleo mora em `routes.py` (helpers Google lá).
Google mockado na verificação. Sem mudança de schema.

## Backend — núcleos e adaptadores

- [X] T001 `routes.py`: extrair `_delete_event_flow(event, *, actor_name, actor_role) -> bool`
      (líder de grupo → `False`; senão `_log_sync("manual_deleted")` + `_delete_event(..., True)` +
      commit → `True`) e `_sync_single_event_flow(event) -> str`
      (`"no_google_id"`/`"not_found"`/`"ok"`). `delete_calendar_event` e `sync_single_event` viram
      wrappers finos (gate `_CAN_DELETE`/flashes/redirects idênticos; captura `title` antes de excluir).
- [X] T002 `agenda_write.py`: `DELETE /api/events/<id>` (`@api_login_required`; 404; `_can_delete()`
      senão 403; núcleo `False` → 409; sucesso `{"ok": true}`) e `POST /api/events/<id>/sync`
      (`@api_login_required`; 404; status → 400/`502`/`serialize_event_detail`). Helper `_can_delete()`
      (importa `_CAN_DELETE` de `routes`).
- [X] T003 `agenda_read.py`: `_role_flags` ganha `"can_delete": has(COMERCIAL) or is_superadmin`.

## Frontend

- [X] T004 `lib/eventOps.ts`: `useSyncEvent(eventId)` (POST `/sync`, `setQueryData(["event", id])`) e
      `useDeleteEvent(eventId)` (DELETE → `{ok}`; invalida `["agenda"]`/`["agenda-dia"]`, remove
      `["event", id]`). `EventDetailPage.tsx`: seção final com **Sincronizar com Google** (sempre) e
      **Excluir evento** (quando `flags.can_delete`, `window.confirm`, ao suceder `navigate("/agenda")`);
      feedback de pending; mensagens de erro amigáveis. Conferir 320–430px (Princípio VIII).

## Verificação

- [X] T005 `scripts/db/verify_151_excluir_sync.py`: mock do Google (`routes.delete_event` no-op;
      `routes.fetch_single_event`/`routes.sync_events` espionados). Paridade API×Jinja: exclusão
      (linha some + log `manual_deleted`), recusa de líder de grupo (API 409 / Jinja sem exclusão),
      403 sem `_CAN_DELETE`, 404; sincronizar ok (ambos chamam `sync_events` com o item), sem
      `google_event_id` (API 400), não encontrado (API 502), e `can_delete` na serialização. Jinja
      302; API 200/400/403/404/409/502. `ruff` nos tocados; `tsc`/`build` limpos.

## Fase final

- [X] T006 Marcar tasks; commit no branch `151-...`; merge+push. `CLAUDE.md`/memória pointer.
      Changelog só quando substituir algo em produção — não republicar agora.

## Dependências

- T001 → T002 (a API chama os núcleos de T001). T003 independe. T004 depende do backend. T005 por
  último. Nenhuma mudança de schema.
