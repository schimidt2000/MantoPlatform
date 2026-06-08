# Tasks: Sincronização automática da agenda confiável

**Input**: `specs/029-cron-sync-confiavel/`
**Tests**: boot + ruff + migration up/down + verificação no app real. Migration escrita à mão.

## Phase 1: Fonte única da sincronização
- [x] T001 `app/calendar/sync.py` (novo): `run_calendar_sync(lookahead_months=6) -> dict` — move a
      lógica de faixa de meses do `sync_worker.py` (meses hoje→+N + buffer; por mês fetch → sync_events
      → _cleanup_stale_events → _mark_month_synced; grava AuditLog; retorna resumo). Imports tardios
      dos helpers de `calendar.routes` p/ evitar ciclo. Type hints + docstring.
- [x] T002 `sync_worker.py`: vira wrapper fino — `with app.app_context(): run_calendar_sync()` e
      `sys.exit` conforme erros. Mantém compatibilidade (Princípio IV/I).

## Phase 2: Controle de execução única (banco)
- [x] T003 Migration manual `i5c6d7e8f9a0_calendar_auto_sync_at.py` (down_revision `h4b5c6d7e8f9`):
      adiciona `calendar_auto_sync_at` DateTime nullable em `site_settings`. up/down.
- [x] T004 `app/models.py`: `SiteSetting.calendar_auto_sync_at = db.Column(db.DateTime, nullable=True)`.
- [x] T005 `app/calendar/sync.py`: `_claim_auto_sync(interval_seconds) -> bool` — UPDATE condicional
      atômico (id=1 e (NULL ou < now-interval) → now); `rowcount == 1` ganha o ciclo.

## Phase 3: Thread interna
- [x] T006 `app/config.py`: `CALENDAR_SYNC_INTERVAL` (env, default 600).
- [x] T007 `app/__init__.py`: `_start_calendar_sync(app)` espelhando `_start_talent_sync` (daemon,
      warmup 15s, loop a cada INTERVAL: app_context → se `_claim_auto_sync` → `run_calendar_sync`;
      try/except logando). Chamar em `create_app()` ao lado de `_start_talent_sync(app)`.

## Phase 4: Visibilidade (leve)
- [x] T008 (se viável) exibir `calendar_auto_sync_at` na tela de Sincronização (`admin.sync_status`).
      Caso contrário, manter só no AuditLog (FR-006 já satisfeito).

## Phase 5: Verificação
- [x] T009 boot + `ruff check`/`ruff format`; migration up/down. Cenários: (a) claim→run sincroniza,
      grava AuditLog e atualiza `calendar_auto_sync_at`; (b) segundo claim imediato retorna False
      (execução única); (c) botão "Sincronizar agora" inalterado; (d) erro em fetch não derruba o
      ciclo/thread; (e) sem duplicação de eventos.

## Dependencies
- T001 → T002. T003 → T004 → T005. T005/T001 → T007. T006 → T007. T009 por último.

## Notes
- Idempotência de `sync_events` + claim atômico = sem duplicação/concorrência (constraint
  `google_event_id` é unique). Sem mudar o botão. `sync_worker.py` mantido como backup/manual.
