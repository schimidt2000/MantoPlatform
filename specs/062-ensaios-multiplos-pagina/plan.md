# Implementation Plan: Múltiplos ensaios por evento + página de ensaio simplificada

**Branch**: `062-ensaios-multiplos-pagina` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/062-ensaios-multiplos-pagina/spec.md`

## Summary

(1) Tornar evidente e cômodo marcar **vários ensaios** por evento — incluindo um caminho na home
("+ Marcar outro ensaio") — aproveitando o vínculo um-para-muitos já existente. (2) Dar ao tipo
ENSAIO uma **página simplificada** (`ensaio_detail.html`), via branch antecipado em
`event_detail`, mostrando só data/hora, local, descrição, o show de origem e as ações de
editar/cancelar — sem os painéis de show. **Sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `CalendarEvent`/relação `ensaios`, rotas
`create_ensaio`/`edit_ensaio`/`delete_ensaio` e `_CAN_ENSAIO`.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem mudança de schema, sem migration.**

**Testing**: Verificação contra **`manto_local` (Postgres)**. Test client: criar 2 ensaios num
evento; abrir a página do ensaio (simplificada) e a do show (completa).

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Não quebrar a página de show nem o cancelar de órfão (feature 057); pt-BR;
reusar rotas/idioms existentes.

**Scale/Scope**: `calendar/routes.py` (branch em `event_detail`; `redirect_to` em
`create_ensaio`/`edit_ensaio`), novo `templates/ensaio_detail.html`, `home.html` (+ "marcar
outro"), pequeno ajuste em `event_detail.html` (label).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Usa o vínculo e as rotas de ensaio já
  existentes; só adiciona uma visão e um caminho de UI. Sem entidade nova.
- **II. Padrões Python**: ✅ Branch pequeno e tipado; sem lógica duplicada.
- **III. Arquitetura em camadas**: ✅ Decisão de exibição na rota/template; sem regra de negócio
  nova.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Página de show inalterada; cancelar de
  órfão preservado; branch só para ENSAIO. Verificação em `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Página enxuta e clara; estados (órfão) tratados.
- **VI. Planejar antes de codar**: ✅ Este plano + research.
- **VII. Valores monetários BR**: N/A.

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/062-ensaios-multiplos-pagina/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── calendar/routes.py        # event_detail: branch ENSAIO -> ensaio_detail.html (early return)
│                             # create_ensaio: honrar redirect_to=home; edit_ensaio: redirect_to=ensaio
├── templates/
│   ├── ensaio_detail.html    # NOVO — página simplificada do ensaio
│   ├── event_detail.html     # label "Marcar outro ensaio" quando já há ensaios (clareza)
│   └── home.html             # card de ensaios agendados: "+ Marcar outro ensaio" (form inline)
```

**Structure Decision**: Monolito Flask. Novo template dedicado + branch de rota; reuso das rotas
de ensaio. Sem novo blueprint, sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
