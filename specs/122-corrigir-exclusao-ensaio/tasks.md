# Tasks — Corrigir Erro 500 ao Excluir Ensaio (122)

- [X] T001 `app/calendar/routes.py`: extrair `_clear_event_side_tables(event_id)` (EventLog/
      EventContract/EventPayment/EventRating) a partir das linhas já existentes em
      `_delete_event()`
- [X] T002 `_delete_event()`: usar o helper; `except RuntimeError: pass` → `except
      Exception as exc:` com `current_app.logger.exception` + flash amigável
- [X] T003 `delete_ensaio()`: chamar o helper antes de `db.session.delete(ensaio)`;
      `except RuntimeError as exc:` → `except Exception as exc:` com log mantendo o flash
      já existente
- [X] T004 Verificação funcional vs manto_local: reproduzir o cenário relatado (ensaio com
      EventLog + falha simulada do Google) e confirmar exclusão limpa na 1ª tentativa;
      ensaio órfão; ensaio sem histórico (caminho feliz); exclusão de evento comum
      continua funcionando após a refatoração + ruff
- [X] T005 Commit, merge em main, push
