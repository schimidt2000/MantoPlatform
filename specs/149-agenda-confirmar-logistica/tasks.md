# Tasks: confirmar evento / logística (149)

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
Padrão de 146/147/148: núcleo compartilhado → adaptadores finos (Jinja + API) → React → verificação
por paridade contra `manto_local`. Sem mudança de schema.

## Backend — núcleo e adaptadores

- [X] T001 `app/calendar/event_ops.py` (NOVO): `toggle_confirmed(event, *, actor_name, actor_id, tz)
      -> bool` e `save_logistics(event, *, makeup_time, makeup_location, departure_time,
      departure_location, needs_rehearsal, actor_name, tz) -> None`, com o efeito idêntico aos
      handlers atuais (mesmos campos, mesmo `EventLog`). Mover para cá `notify_accepted_roles` e
      `notify_ensaio_team` (de `routes.py`), + helper `resolve_makeup_location(selection, custom)`.
      Só importa `models`/`email_service` (sem `routes` — sem ciclo). Docstrings/type hints.
- [X] T002 `routes.py`: `_handle_toggle_confirmado` e `_handle_save_logistics` viram wrappers finos
      sobre o núcleo (lêem form/`current_user`, dão `flash`, resolvem "outro" via helper). Remover as
      defs de `_notify_accepted_roles`/`_notify_ensaio_team` e reimportá-las de `event_ops` com alias
      (`_notify_accepted_roles`, `_notify_ensaio_team`) para os 4 call sites existentes (sync
      inclusive) seguirem inalterados. Comportamento observável idêntico.
- [X] T003 `agenda_write.py`: `POST /api/events/<id>/confirm` (gate Comercial/Superadmin; toggle) e
      `PATCH /api/events/<id>/logistics` (gate `_can_edit_event`; corpo JSON com os campos). Ambos
      chamam o núcleo e retornam `serialize_event_detail`.
- [X] T004 `agenda_read.py`: bloco `event` expõe `confirmed_by`, `makeup_time`, `makeup_location`,
      `departure_time`, `departure_location`, `needs_rehearsal`; `_role_flags` expõe `can_confirm`
      (Comercial|SA) e `can_edit_event` (`_CAN_EDIT_EVENT`).

## Frontend

- [X] T005 [P] `lib/agenda.ts`: `EventoDetalhe.event` ganha `confirmed_by: string | null` e os 5
      campos de logística; `lib/eventOps.ts` (NOVO): `useToggleConfirm` (POST `/api/events/<id>/
      confirm`) e `useSaveLogistics` (PATCH `/api/events/<id>/logistics`) — atualizam `["event", id]`
      com o evento retornado.
- [X] T006 `EventDetailPage.tsx`: badge "Confirmado" vira botão (Confirmar/Desfazer) quando
      `flags.can_confirm`; nova seção **Logística** (leitura de maquiagem/saída/precisa-ensaio +
      form de edição quando `flags.can_edit_event`, com select de local "outro"→custom e checkbox de
      ensaio). Feedback de clique (pending desabilita). Conferir viewport 320–430px (Princípio VIII).

## Verificação

- [X] T007 `scripts/db/verify_149_logistica.py`: paridade API×Jinja campo a campo para as duas ações;
      confirmar/desconfirmar (toggle ida e volta), 403 (confirmar sem Comercial/SA; logística fora de
      `_CAN_EDIT_EVENT`), local "outro", e alerta de ENSAIO **só** na transição desligado→ligado (mock
      dos senders + contagem). E-mail mockado. Jinja 302, API 200. ruff nos arquivos tocados; `tsc`/
      `build` limpos.

## Fase final

- [ ] T008 Marcar tasks; commit no branch `149-...`; merge+push. `CLAUDE.md`/memória pointer.
      Changelog só quando substituir algo em produção (equipe segue no Jinja) — não republicar agora.
