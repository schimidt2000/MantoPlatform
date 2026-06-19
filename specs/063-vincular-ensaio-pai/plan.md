# Implementation Plan: Vincular um ensaio existente a um evento pai

**Branch**: `063-vincular-ensaio-pai` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/063-vincular-ensaio-pai/spec.md`

## Summary

Permitir, na página do ensaio (feature 062), **vincular o ensaio a um evento pai** (show)
escolhendo-o de uma lista buscável — funcionando para ensaios órfãos e para trocar o pai. Uma
nova rota seta `parent_event_id` com validações. **Sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `CalendarEvent.parent_event_id`/`ensaios` e
`_CAN_ENSAIO`.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem mudança de schema, sem migration.**

**Testing**: Verificação contra **`manto_local` (Postgres)**. Test client: vincular um órfão a um
show e conferir o vínculo + aparição em `show.ensaios`; rejeição de pai inválido.

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Restrito a ENSAIO/CASTING/SUPERADMIN; não vincular a outro ensaio nem a si
mesmo; pt-BR; não tocar no Google Calendar.

**Scale/Scope**: `calendar/routes.py` (nova rota `link-parent` + `candidate_shows` no branch
ENSAIO), `ensaio_detail.html` (form de vincular no bloco "Show de origem").

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa o campo de vínculo, a relação
  `ensaios`, o padrão `groupable_events` e `_CAN_ENSAIO`. Sem entidade nova.
- **II. Padrões Python**: ✅ Rota pequena e validada.
- **III. Arquitetura em camadas**: ✅ Validação/escrita na rota; seleção na página.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Aditivo; não altera criação/edição/
  cancelamento de ensaio nem a página de show. Verificação em `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Ação clara no bloco "Show de origem"; estados (órfão/
  vinculado) tratados; busca por nome.
- **VI. Planejar antes de codar**: ✅ Este plano + research.
- **VII. Valores monetários BR**: N/A.

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/063-vincular-ensaio-pai/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── calendar/routes.py        # + POST /events/<ensaio_id>/link-parent; candidate_shows no branch ENSAIO
└── templates/ensaio_detail.html  # form "Vincular a um show" (buscável) no bloco "Show de origem"
```

**Structure Decision**: Monolito Flask. Rota aditiva + UI na página do ensaio. Sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
