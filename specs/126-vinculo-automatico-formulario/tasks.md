# Tasks — Vínculo Automático de Formulário a Evento (126)

- [X] T001 Migration: `form_responses` ganha `event_link_source` (String(20), nullable),
      `event_link_ambiguous` (Boolean, default False), `event_link_locked` (Boolean,
      default False); checar colisão de revision-id
- [X] T002 `app/models.py`: as 3 colunas novas em `FormResponse`
- [X] T003 `app/formularios/routes.py`: motor de casamento — `_real_event_candidates`,
      `_client_by_phone`, `_client_real_event_ids`, `_event_client_phones`,
      `_attempt_auto_link` (US1 + US2), `retry_auto_link_pending` (US1 P2 — retry);
      chamar `_attempt_auto_link` em `_submit_public_form` logo após `_save_response`
- [X] T004 `app/formularios/routes.py`: rotas `vincular_evento` (manual, reaproveitando
      `/gastos/api/eventos?date=` no picker) e `desvincular_evento` (US4) — ambas marcam
      `event_link_locked=True` (decisão humana não é sobrescrita depois)
- [X] T005 `app/calendar/sync.py`: `run_calendar_sync()` chama `retry_auto_link_pending()`
      após o laço de meses (best-effort, não derruba o ciclo), soma ao `detail` do
      AuditLog do sync
- [X] T006 `app/cli.py`: comando `backfill-form-event-links` (FR-007)
- [X] T007 `app/__init__.py` (home): lista `form_responses_precisam_revisao`
      (`event_link_ambiguous=True`), somada ao contador comercial e à condição "tudo em
      dia"; `app/templates/home.html`: novo bloco de aviso (US3), mesmo padrão visual do
      já existente "sem cliente"
- [X] T008 `app/templates/formularios/detail.html`: painel "Evento" — estado atual +
      badge de origem (auto por data/cliente/manual) + aviso quando ambíguo + buscador
      manual por data (JS reaproveitando `/gastos/api/eventos`) + botão "Desvincular"
- [X] T009 Verificação funcional vs manto_local (23/23): match único por data; ensaio
      excluído dos candidatos; ambiguidade com 2 eventos no mesmo dia sem cliente
      batendo; desempate por cliente já associado; contradição (evento com cliente de
      telefone diferente não vincula, fica ambíguo); 0 candidatos + cliente com 1 evento
      futuro vincula; retry pós-criação tardia do evento (`retry_auto_link_pending`);
      backfill via comando CLI; vincular/desvincular manual via HTTP com
      `event_link_locked` comprovadamente impedindo a automação de re-agir depois; aviso
      da home aparece só para casos ambíguos e some após resolução manual. Ruff: 11/11
      erros pré-existentes (models.py 8, sync.py 2, cli.py 1), zero novo — routes.py e a
      migration ficaram limpos.
- [X] T010 Commit, merge em main, push
