# Implementation Plan: excluir e sincronizar evento em React (151)

**Branch**: `151-agenda-excluir-sincronizar-evento` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Migra **excluir evento** e **sincronizar evento** (as ações de nível-evento sem upload que faltavam)
para React + API JSON, no padrão de 146-150. Diferença: o núcleo destas duas ações fica como função
de módulo em `app/calendar/routes.py` (os helpers Google vivem lá; mover inverteria `routes → ops`).
Os handlers Jinja viram wrappers finos; dois endpoints REST (`DELETE /api/events/<id>`,
`POST /api/events/<id>/sync`); o serializer expõe o flag `can_delete`; a `EventDetailPage` ganha
botões de sincronizar (qualquer autenticado) e excluir (só `can_delete`, com confirmação → navega à
agenda). Verificação por paridade contra `manto_local`, Google mockado. Sem mudança de schema.

## Technical Context

Igual à 146-150: Python/Flask + React (Vite/TS/TanStack Query); sem dependência nova; verificação
com test client contra `manto_local`; requests fora de `app_context`. Helpers reusados já existentes
em `routes.py`: `_delete_event(event, also_from_google)` (limpa tabelas sem cascade, trata comissões,
chama Google `delete_event`), `_log_sync(...)`, `fetch_single_event(CALENDAR_ID, gid)`,
`sync_events([item])`, constante `_CAN_DELETE = {SUPERADMIN, COMERCIAL}`, propriedade
`CalendarEvent.is_group_leader`.

## Constitution Check

- **I (reutilizar)**: um núcleo por ação (`_delete_event_flow`, `_sync_single_event_flow`) em
  `routes.py`, reusado pelo wrapper Jinja e pelo endpoint JSON. A API importa de `routes.py`
  (função-local), a MESMA direção `api → routes` já usada para os gates (`_CAN_EDIT_EVENT` etc.) —
  sem inverter `routes → ops`, sem ciclo. Nenhuma lógica duplicada.
- **IV (não quebrar)**: wrappers Jinja com efeito idêntico (mesmo log, mesma guarda de líder de
  grupo, mesmos flashes); paridade verificada. POSTs Jinja seguem 302.
- **V (feedback)**: botões com feedback (mutations do TanStack); excluir pede `window.confirm`
  (destrutivo) e desabilita enquanto pendente — sem exclusão dupla.
- **VII (monetário)**: sem valor monetário novo.
- **VIII (mobile-first)**: os botões (incl. a área "zona de perigo") conferidos em 320–430px.
- **IX (movimento)**: reusa as transições já presentes na `EventDetailPage`.

## Project Structure

```text
app/calendar/routes.py        # + _delete_event_flow, _sync_single_event_flow (núcleos de módulo);
                              #   delete_calendar_event / sync_single_event viram wrappers finos
app/api/agenda_write.py       # + DELETE /api/events/<id>, POST /api/events/<id>/sync; helper _can_delete
app/api/agenda_read.py        # _role_flags: + can_delete (Comercial|SA)
frontend/apps/internal/src/
├── lib/eventOps.ts           # + useDeleteEvent (DELETE, invalida agenda), useSyncEvent (POST)
└── pages/EventDetailPage.tsx # botões Sincronizar (qualquer auth) e Excluir (can_delete) + navegação
scripts/db/verify_151_excluir_sync.py   # NOVO: paridade API×Jinja, Google mockado
```

## Design Decisions

1. **Núcleos em `routes.py`** (funções de módulo, sem `request`/`flash` dentro delas — os wrappers é
   que dão flash):
   - `_delete_event_flow(event, *, actor_name, actor_role) -> bool` — se `event.is_group_leader`,
     retorna `False` (não exclui); senão `_log_sync("manual_deleted", ...)`, `_delete_event(event,
     also_from_google=True)`, `db.session.commit()`, retorna `True`. (Obs.: `_delete_event` pode dar
     um `flash` de aviso só em falha do Google — inofensivo em contexto de request da API.)
   - `_sync_single_event_flow(event) -> str` — `"no_google_id"` se sem `google_event_id`;
     `"not_found"` se `fetch_single_event` retorna vazio; senão `sync_events([item])` +
     `db.session.commit()` → `"ok"`.
2. **Wrappers Jinja**: `delete_calendar_event` mantém o gate `_CAN_DELETE`/`abort(403)`, captura o
   `title` antes, chama `_delete_event_flow` e escolhe o flash/redirect pelo retorno (recusa →
   flash de erro + volta ao detalhe; sucesso → flash + volta à agenda). `sync_single_event` chama
   `_sync_single_event_flow` e mapeia o status para os três flashes de hoje.
3. **Endpoints REST** (`agenda_write.py`):
   - `DELETE /api/events/<id>` — `@api_login_required`; 404 se não existe; `_can_delete()` senão 403;
     `_delete_event_flow(...)` → `False` = 409 ("desagrupe os satélites antes"); sucesso =
     `{"ok": true}`.
   - `POST /api/events/<id>/sync` — `@api_login_required`; 404 se não existe; status do núcleo →
     `"no_google_id"` = 400, `"not_found"` = 502, `"ok"` = `serialize_event_detail` (evento
     atualizado). Novo helper `_can_delete()` (importa `_CAN_DELETE` de `routes`).
4. **Serializer** (`agenda_read.py`): `_role_flags` ganha `"can_delete": has(COMERCIAL) or
   is_superadmin` (= `_CAN_DELETE`). Flag aditivo.
5. **Frontend** (`lib/eventOps.ts`): `useSyncEvent(eventId)` (POST, `setQueryData(["event", id])`) e
   `useDeleteEvent(eventId)` (DELETE → `{ok}`; onSuccess invalida `["agenda"]`/`["agenda-dia"]` e
   remove `["event", id]`; a navegação fica no componente via `useNavigate`). Na `EventDetailPage`,
   uma seção final com botão **Sincronizar com Google** (sempre) e, quando `flags.can_delete`, um
   botão **Excluir evento** (destrutivo, `window.confirm`, ao suceder `navigate("/agenda")`); erros
   com mensagem amigável.
6. **Verificação** (`verify_151_excluir_sync.py`): mocka o Google — `routes.delete_event` (Google)
   vira no-op para a exclusão testar só o efeito local; `routes.fetch_single_event` e
   `routes.sync_events` são espionados para provar que API e Jinja chamam o MESMO núcleo. Cobre:
   exclusão API×Jinja (linha some + log `manual_deleted`), recusa de líder de grupo (API 409 / Jinja
   sem exclusão), 403 sem `_CAN_DELETE`, 404, sincronizar ok (ambos chamam `sync_events` com o item),
   sem `google_event_id` (API 400 / flash), não encontrado (API 502 / flash), e o flag `can_delete`
   na serialização. Jinja 302; API 200/400/403/404/409/502. `ruff` nos arquivos tocados; `tsc`/
   `build` limpos.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Núcleo em `routes.py` (não em módulo `ops`) | `_delete_event`/`fetch_single_event`/`sync_events`/`_log_sync` vivem em `routes.py` e são usados em muitos pontos | Mover para `ops` inverteria `routes → ops` (event_ops importaria routes) ou exigiria mover helpers pesados acoplados ao Google — mais risco que benefício; `api → routes` já é a direção usada para gates |
