# Tasks — Reembolsos de Despesas do Evento (136)

- [X] T001 `app/models.py`: `EventReimbursement` (event_id, description, amount,
      invoice_file_path, created_at/created_by_id, collected_at/collected_amount/
      receipt_file_path/collected_by_id, propriedade `is_collected`)
- [X] T002 Migration manual (`down_revision` = head atual) — cria `event_reimbursements`;
      checar colisão de revision-id antes de finalizar
- [X] T003 `app/__init__.py`: `UPLOAD_REEMBOLSOS` (mesmo padrão de `UPLOAD_PAYMENTS`) —
      dispensado na prática: nota fiscal reaproveita `UPLOAD_INVOICES` (via `_save_nf_file`)
      e comprovante reaproveita `UPLOAD_PAYMENTS`, sem config nova
- [X] T004 `app/calendar/routes.py`: `_handle_add_reembolso`, `_handle_collect_reembolso`,
      `_handle_delete_reembolso` (SUPERADMIN-only) registrados em `_EVENT_ACTIONS`;
      `event_detail()` passa `reembolsos`/`reembolsos_pendentes_total`; `create_event()`
      lê checkbox + campos inline e cria o reembolso após o evento commitado;
      `_clear_event_side_tables()` ganha limpeza de `EventReimbursement`
- [X] T005 `app/templates/event_create.html`: checkbox "terá reembolso?" revelando
      descrição + valor + nota fiscal opcional (mesmo padrão de `needs_rehearsal`)
- [X] T006 `app/templates/event_detail.html`: painel "💸 Reembolsos" (form de adicionar +
      lista com badge pendente/cobrado + toggle "marcar como cobrado" com comprovante +
      excluir SUPERADMIN-only), dentro do mesmo gate já existente da seção comercial
- [X] T007 `app/templates/event_detail.html` (`page_actions`): botão "💸 Cobrar
      reembolsos" (desabilitado sem pendência) + `buildCobrancaReembolso()` + wiring
- [X] T008 `app/__init__.py` (home) + `app/templates/home.html`: bloco "Reembolsos
      pendentes" no setor Comercial (mesmo padrão de "Cobranças pendentes"), somado a
      `_total_comercial` e ao estado vazio combinado
- [X] T009 Verificação funcional vs `manto_local`: reembolso na criação do evento;
      reembolso manual (múltiplos por evento); marcar como cobrado (valor+comprovante)
      some da home e do botão de cobrança; botão desabilitado sem pendência; SUPERADMIN
      exclui, outros papéis não conseguem; excluir evento com reembolso não quebra;
      permissão igual às demais ferramentas comerciais.
      Achado durante a verificação: `filter_by(id=request.form.get(...))` comparando
      string direto contra coluna Integer quebra em Postgres via driver psycopg (v3,
      usado em `manto_local`) — `operador não existe: integer = character varying`.
      Produção usa psycopg2 (implícito, não quebra), mas o padrão é frágil; corrigido nos
      3 handlers novos com cast explícito (`int(...)` após `.isdigit()`). Padrão antigo
      idêntico em `_handle_delete_payment`/`_handle_edit_payment`/contratos não foi
      tocado (fora do escopo desta feature) — registrado na memória do projeto.
- [X] T010 `ruff check` nos arquivos tocados (mesma contagem do baseline, 28 pré-existentes,
      nenhum novo); changelog (`docs/changelog.html`, republicado no link já existente);
      commit, merge em `main`, push
