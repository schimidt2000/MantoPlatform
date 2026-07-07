# Tasks — Marcar Evento como Confirmado (116)

- [X] T001 Migration `c9d0e1f2a3b4` (calendar_events += confirmed_at, confirmed_by_id) e
      upgrade no manto_local; conferir unicidade do revision
- [X] T002 `app/models.py`: colunas + relationship `confirmer`
- [X] T003 `app/calendar/routes.py`: `POST /events/<id>/toggle-confirmado` (RBAC
      COMERCIAL/SUPERADMIN, EventLog)
- [X] T004 `app/templates/event_detail.html`: botão ao lado de "Confirmar dados do evento"
      + indicador de quem/quando confirmou
- [X] T005 Verificação funcional vs manto_local (marcar, desfazer, persistência, RBAC, log)
      + ruff
- [X] T006 Commit, merge em main, push
