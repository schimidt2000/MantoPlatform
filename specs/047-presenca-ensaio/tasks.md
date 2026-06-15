# Tasks: Presença é tarefa do ensaio (não do casting)

**Input**: `specs/047-presenca-ensaio/`
**Tests**: boot + ruff + test client. Sem migration.

- [x] T001 `app/calendar/routes.py`: constante `PRESENCE_CHARACTER` + reusar nos literais.
- [x] T002 `app/__init__.py`: excluir presença de pending_casting/total/done; `pending_presence`
      (shows futuros sem presença) para o ensaio.
- [x] T003 `app/templates/home.html`: subseção "Falta definir presença" + badge no header Ensaio.
- [x] T004 Verificação (US1–US2) + commit.

## Dependencies
- T001 → T002 → T003 → T004.
