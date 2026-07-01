# Implementation Plan: Task para o comercial completar clientes

**Branch**: `101-task-cliente-faltante` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/101-task-cliente-faltante/spec.md`

## Summary

Adicionar à home uma tarefa comercial **"Sem cliente"**: eventos a partir da **data de início do
sistema** (`release_date`) que **não têm cliente** associado (features 094/100), excluindo **ENSAIO** e
**satélites**. Espelha a tarefa já existente **"Sem valor de venda"** — nenhuma tabela nova, tarefa
**derivada** no controlador da home.

## Technical Context

**Language/Version**: Python 3.x (Flask), Jinja2

**Primary Dependencies**: Flask, SQLAlchemy. Sem dependência nova. **Sem migração** (usa modelos
existentes: `CalendarEvent`, associação `EventClient` da feature 100, `SiteSetting.release_date`).

**Storage**: PostgreSQL/SQLite. Testar contra `manto_local`.

**Testing**: pytest/scripts contra `manto_local`. Casos: evento sem cliente a partir da data aparece;
com cliente sai; ENSAIO/satélite/antes-da-data não aparecem; visível só p/ comercial.

**Constraints**: Reutilizar `task_cutoff` (release_date) e `show_comercial` já existentes na home. "Sem
cliente" = sem associação `EventClient` (fonte de verdade). Sem regressão nas demais tarefas.

**Scale/Scope**: 1 query nova na rota da home + 1 seção no template + ajuste do texto de ajuda no admin.

## Constitution Check

- **Sem duplicação**: espelha o padrão de `events_sem_valor` (mesmo corte, mesma exclusão de satélites/
  ensaios, mesmo `show_comercial`). ✅
- **Tarefa derivada**: sem novo modelo/migração. ✅
- **Não quebrar**: adição isolada ao bloco Comercial. ✅

Resultado: PASS.

## Project Structure

```text
app/
├── __init__.py                 # home(): query events_sem_cliente + passar ao template
└── templates/
    ├── home.html               # seção "Sem cliente" no bloco Comercial + contagem
    └── admin_settings.html      # texto de ajuda menciona a nova tarefa (opcional)
```

**Structure Decision**: Segue o padrão de tarefas derivadas da home. `events_sem_cliente` é calculado ao
lado de `events_sem_valor`, com os mesmos filtros (corte por `release_date`, exclui ENSAIO e satélites),
sob a mesma flag `show_comercial`. A condição "sem cliente" usa `~CalendarEvent.event_clients.any()`.

## Implementation Approach

1. **Query** em `home()`: `events_sem_cliente` = eventos com `~event_clients.any()`, `start_at >=
   task_cutoff`, `group_leader_id IS NULL`, excluindo ENSAIO. Passar ao `render_template`.
2. **Template** `home.html`: nova seção "Sem cliente" no bloco Comercial (mesma aparência de "Sem valor
   de venda"), somando ao total de pendências e à condição de "nenhuma pendência".
3. **Admin** (opcional): ajustar o texto de ajuda de `release_date` para citar a nova tarefa.
4. **Verificação** contra `manto_local`.

## Complexity Tracking

> Sem violações de constituição. Feature mínima e derivada.
