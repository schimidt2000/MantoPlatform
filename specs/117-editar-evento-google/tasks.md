# Tasks — Botão "Editar no Google Agenda" (117)

- [X] T001 Migration `d0e1f2a3b4c5` (calendar_events += google_html_link) e upgrade no
      manto_local; conferir unicidade do revision
- [X] T002 `app/models.py`: coluna `google_html_link`
- [X] T003 `app/calendar/routes.py`: capturar `item.get("htmlLink")` nos dois branches de
      `sync_events()` (evento novo e evento existente)
- [X] T004 `app/templates/event_detail.html`: botão "Editar no Google Agenda" (RBAC
      COMERCIAL/SUPERADMIN + só com `google_html_link` preenchido)
- [X] T005 Verificação funcional vs manto_local (captura na sync, RBAC, ausência sem link)
      + ruff
- [X] T006 Commit, merge em main, push
