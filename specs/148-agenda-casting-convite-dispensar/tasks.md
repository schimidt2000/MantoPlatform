# Tasks: convite / dispensar / restaurar / figurino (148)

## Backend
- [X] T001 `casting_ops.py`: extrair o núcleo das quatro ações —
      `send_invite(event, role, *, actor_name, tz) -> bool` (log + `invite_status=pending` +
      envio síncrono de convite; retorna se o e-mail saiu),
      `set_figurino_done(event, role, *, actor_name, tz)` (log + `figurino_done_at`),
      `dismiss_role(role, *, actor_name, dismissed_by) -> bool` (False se tem talento; senão
      `dismissed_at`/`dismissed_by` + log), `restore_role(role, *, actor_name)` (limpa dispensa +
      log). Docstrings/type hints.
- [X] T002 `routes.py`: `_handle_send_invite`, `_handle_figurino_done`, `dismiss_role`,
      `restore_role` viram wrappers finos sobre o núcleo (lêem form/`current_user`, dão `flash`).
      Handlers de figurino/invite buscam o role com `int(role_id)` (evita o bug psycopg3
      `filter_by(id=string)`). Comportamento observável idêntico.
- [X] T003 `agenda_write.py`: `POST /api/roles/<id>/invite` e `POST /api/roles/<id>/figurino-done`
      (ambos gate `_can_edit_event` — paridade com o POST Jinja que os despacha),
      `POST /api/roles/<id>/dismiss` e `POST /api/roles/<id>/restore` (só superadmin; dispensar →
      400 se cargo com talento). Todos retornam `serialize_event_detail`.
- [X] T004 `agenda_read.py`: `_serialize_role` expõe `"dismissed": role.dismissed_at is not None`.

## Frontend
- [X] T005 [P] `lib/casting.ts`: `useSendInvite`, `useSetFigurinoDone`, `useDismissRole`,
      `useRestoreRole` (POST nos endpoints; atualizam `["event", id]` com o evento retornado).
- [X] T006 `EventDetailPage.tsx`: por cargo, botões conforme RBAC —
      reenviar convite (se `show_casting` e tem talento), marcar figurino (se `show_figurino` e
      tem talento e não `figurino_done`), dispensar/restaurar (se `is_superadmin` e sem talento;
      alterna pelo `dismissed`). Feedback de clique (pending desabilita).

## Verificação
- [X] T007 `scripts/db/verify_148_casting.py`: paridade API×Jinja campo a campo para as quatro
      ações; 403 (figurino sem papel; dispensar/restaurar sem superadmin); bloqueio de dispensar
      cargo com talento (API 400, Jinja flash/sem efeito); reenviar convite sem talento = no-op;
      idempotência (2º clique não gera 2º e-mail/registro relevante). E-mail mockado. Jinja 302,
      API 200. ruff nos arquivos tocados; `tsc`/`build` limpos.

## Fase final
- [X] T008 Marcar tasks; commit no branch `148-...`; verificar na main mergeada; merge+push.
      `CLAUDE.md`/memória pointer. Changelog só quando substituir algo em produção (equipe segue
      no Jinja) — não republicar agora.
