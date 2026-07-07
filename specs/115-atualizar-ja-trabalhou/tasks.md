# Tasks — Atualizar "Já Trabalhou com a Manto" Automaticamente (115)

- [X] T001 `app/calendar/routes.py`: `_mark_talents_worked()` chamada ao fim de
      `sync_events()` — liga `worked_before` para talentos com evento real já realizado e
      convite não recusado, nunca desliga
- [X] T002 Verificação funcional vs manto_local (liga após evento passado, não liga se
      futuro/recusado/ensaio, idempotente, edição manual preservada) + ruff
- [X] T003 Commit, merge em main, push
