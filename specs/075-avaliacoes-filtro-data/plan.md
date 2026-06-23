# Implementation Plan: Alternar filtro de avaliações por data (075)

**Branch**: `075-avaliacoes-filtro-data` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Adicionar um parâmetro `date_mode` (`evento` padrão | `avaliacao`) à página de avaliações. Quando
`avaliacao`, o filtro de período passa a usar `EventRating.submitted_at` em vez de
`CalendarEvent.start_at`, em **todos** os pontos do recorte. UI ganha um alternador que preserva os
demais filtros. **Sem modelo, sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2.

**Primary Dependencies**: nenhuma. Reusa `_parse_period`, `setFilter` (JS já existente).

**Storage**: sem migration (usa `submitted_at` já existente).

**Testing**: contra **`manto_local`** — em `evento` os números batem com hoje; em `avaliacao`, uma
avaliação recente de evento antigo aparece no período curto; demais filtros preservados; `ruff` sem
erros novos.

**Constraints**: padrão = `evento` (sem regressão); aplicar o critério de forma consistente em todas
as consultas/listas; pt-BR.

**Scale/Scope**: `app/talents/routes.py::avaliacoes` (coluna de data condicional em 2 consultas +
passar `date_mode` + rótulo) e `app/templates/talents/avaliacoes.html` (alternador).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `_parse_period` e `setFilter`.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Padrão mantém o comportamento atual; verificação em
  `manto_local`.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/talents/routes.py
  - avaliacoes(): date_mode = request.args.get('date_mode'); _date_col condicional
    (EventRating.submitted_at vs CalendarEvent.start_at) aplicado em ratings_q e rated_q;
    passa date_mode ao template; rótulo do recorte indica "por data da avaliação".
app/templates/talents/avaliacoes.html
  - linha "Filtrar por:" com dois chips (Data do evento / Data da avaliação) via setFilter,
    oculta quando event_id (período não se aplica).
```

**Structure Decision**: Coluna de data condicional + alternador na UI. Sem migration.

## Complexity Tracking

> Sem violações.
