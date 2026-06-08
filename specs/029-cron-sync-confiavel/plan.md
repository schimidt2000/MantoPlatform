# Implementation Plan: Sincronização automática da agenda confiável

**Branch**: `029-cron-sync-confiavel` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

## Summary

Substituir a dependência de um serviço Cron externo frágil por uma **sincronização interna ao app**
(thread de background, como a de talentos), reaproveitando a **mesma lógica do botão** por mês.
Extrair a lógica de "sincronizar uma faixa de meses" para uma **função única** usada pela thread e pelo
`sync_worker.py`. Garantir **execução única** entre os workers do gunicorn via **claim atômico no
banco** (UPDATE condicional), que também serve de marcador de última execução. Sem mudar o
comportamento do botão.

## Constitution Check

- **I. Reutilizar** ✅ — extrai `run_calendar_sync()` como fonte única; thread, cron e (lógica do)
  botão passam a compartilhar o mesmo núcleo. Reusa `_start_talent_sync` como modelo.
- **III. Camadas / config central** ✅ — intervalo via config; lógica de sync no módulo de calendar.
- **IV. Não quebrar** ✅ — botão intacto; cron continua funcionando (vira wrapper). Operações já são
  idempotentes; o claim atômico evita concorrência. Verificação no app real.
- **V. Feedback** ✅ — registra última execução/erro (AuditLog + marcador), fechando o diagnóstico.

## Estado atual (confirmado na investigação)

- Botão (`agenda()` com `force_sync`): `fetch_events_for_month` → `sync_events` →
  `_cleanup_stale_events` → `_mark_month_synced` (1 mês). Idêntico, por mês, ao cron.
- `sync_worker.py`: mesma sequência para faixa de meses (hoje → +6, com buffer pelo último evento no
  banco). É um **serviço Cron separado** no Railway — frágil/que pode não estar ativo.
- Token OAuth no banco (`SiteSetting.google_token`) → autenticação funciona em qualquer processo.
- `_start_talent_sync(app)` (em `app/__init__.py`) já é o padrão de thread de background; roda em
  produção (gunicorn) — mas **uma vez por worker** (3x). Para a agenda isso exige controle de execução
  única (constraint `google_event_id` é `unique` → concorrência geraria IntegrityError).

## Design Detalhado

### 1. Fonte única — `run_calendar_sync()` (em `app/calendar/sync.py`, novo)
- Move a lógica de faixa de meses do `sync_worker.py` para `run_calendar_sync(lookahead_months=6) ->
  dict`:
  - calcula meses (hoje → +N, com buffer pelo último evento no banco),
  - por mês: `fetch_events_for_month` → `sync_events` → `_cleanup_stale_events` → `_mark_month_synced`,
  - registra `AuditLog` (actor "sync_worker"/"auto-sync") com resumo,
  - retorna `{months, errors, results}`.
- Deve ser chamada **dentro de um app_context** (a thread cria o contexto).
- `sync_worker.py` vira um wrapper fino: `with app.app_context(): run_calendar_sync()`.

> Nota de import: hoje `sync_events`, `_cleanup_stale_events`, etc. vivem em `app/calendar/routes.py`.
> Para evitar import circular, `run_calendar_sync` importa esses helpers localmente (dentro da função)
> ou eles permanecem em routes e `sync.py` os importa de forma tardia. Mantém os helpers onde estão.

### 2. Controle de execução única — claim atômico no banco
- **Migration (manual)**: adiciona coluna `calendar_auto_sync_at` (DateTime, nullable) em
  `site_settings`. `down_revision = "h4b5c6d7e8f9"`. Campo no modelo `SiteSetting`.
- Helper `_claim_auto_sync(interval_seconds) -> bool`:
  - `UPDATE site_settings SET calendar_auto_sync_at = :now WHERE id = 1 AND
    (calendar_auto_sync_at IS NULL OR calendar_auto_sync_at < :now - interval)`.
  - `rowcount == 1` → este processo ganhou o ciclo (retorna True); senão False (outro já rodou).
  - Atômico no nível do banco (SQLite e Postgres), então **exatamente um worker** roda por ciclo.
- `calendar_auto_sync_at` serve também como **marcador da última execução** (FR-006/US4).

### 3. Thread interna — `_start_calendar_sync(app)` (em `app/__init__.py`)
- Espelha `_start_talent_sync`: mesma guarda de dev (WERKZEUG_RUN_MAIN), `daemon=True`,
  `name="calendar-sync"`, `time.sleep(15)` de aquecimento.
- Loop: a cada `CALENDAR_SYNC_INTERVAL` (config, default **600s**):
  - `with app.app_context():` → se `_claim_auto_sync(INTERVAL)` então `run_calendar_sync()`.
  - `try/except` logando erro (não derruba a thread) — FR-005.
- Chamada em `create_app()` ao lado de `_start_talent_sync(app)`.
- Config `CALENDAR_SYNC_INTERVAL` em `config.py` (env `CALENDAR_SYNC_INTERVAL`, default 600).

### 4. Visibilidade (US4) — leve
- O `AuditLog` já é gravado por `run_calendar_sync` (aparece em `/admin/logs`).
- Adicionar, na tela de Sincronização (`admin.sync_status`, se existir), a exibição de
  `calendar_auto_sync_at` ("Última sincronização automática: …"). Se a tela não comportar facilmente,
  fica só no AuditLog (FR-006 já satisfeito). Confirmar no implement.

### 5. Verificação (app real)
- Forçar `_claim_auto_sync` retornar True e chamar `run_calendar_sync` → meses sincronizados,
  AuditLog gravado, `calendar_auto_sync_at` atualizado.
- Segundo `_claim_auto_sync` imediato → retorna False (execução única).
- Botão "Sincronizar agora" → continua igual.
- Simular `fetch_events_for_month` lançando erro → ciclo registra erro, não derruba; thread continua.
- Boot + ruff + migration aplica/reverte.

## Project Structure
```text
migrations/versions/i5c6d7e8f9a0_calendar_auto_sync_at.py  # NOVO — coluna calendar_auto_sync_at
app/models.py                 # SiteSetting.calendar_auto_sync_at
app/calendar/sync.py          # NOVO — run_calendar_sync() (fonte única) + _claim_auto_sync()
app/__init__.py               # _start_calendar_sync(app); chamada em create_app()
app/config.py                 # CALENDAR_SYNC_INTERVAL (default 600)
sync_worker.py                # vira wrapper fino chamando run_calendar_sync()
app/templates/...sync_status  # (opcional) exibir última sincronização automática
```

## Fora de escopo
- Mudar o comportamento do botão "Sincronizar agora".
- Webhooks/push do Google (sync em tempo real) — fora; mantém polling por intervalo.
- Remover o `sync_worker.py` (mantido como backup/manual).
```
