# Tasks — Cliente na Criação de Evento + Busca sem Acentos (114)

- [X] T001 `app/static/js/client_picker.js`: extrair o IIFE do `event_detail.html`
      (exigência via `data-required`); `event_detail.html` passa a incluir o arquivo
- [X] T002 `app/calendar/routes.py`: helper `_parse_client_pairs()` (extraído de
      `_handle_update_sale`, que passa a usá-lo)
- [X] T003 `app/templates/event_create.html`: bloco de clientes no começo do formulário +
      include do JS + render de `old_clients`
- [X] T004 `app/calendar/routes.py` (create): POST persiste EventClient + client_id
      primário; GET e re-renders de erro passam `client_relation_tipos` e `old_clients`
- [X] T005 `app/utils.py`: `strip_accents_lower()` + `unaccent_lower_sql()`;
      `app/clientes/routes.py`: aplicar em `/clientes/search` e na lista
- [X] T006 Verificação funcional vs manto_local (acentos 2 sentidos, criação com cliente,
      erro preserva, regressão event_detail) + ruff
- [X] T007 Commit, merge em main, push
