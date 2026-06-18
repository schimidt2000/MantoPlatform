# Implementation Plan: Personagens já na agenda no dia (calculadora de orçamento)

**Branch**: `061-personagens-agenda-no-dia` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/061-personagens-agenda-no-dia/spec.md`

## Summary

Ao informar a data do evento na calculadora de orçamento, mostrar logo abaixo os personagens já
escalados em eventos daquele dia (papéis `role_type="character"`, distintos, excluindo apoio e
ensaios), para evitar venda duplicada. Um endpoint JSON (`/orcamento/personagens-no-dia`)
alimenta um bloco na UI que reage à mudança da data. **Sem mudança de modelo, sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `EventRole`/`CalendarEvent` e o decorator
`_require_vendas` do blueprint de orçamento.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem mudança de schema, sem migration.**

**Testing**: Verificação contra a **cópia local `manto_local` (Postgres)** — não SQLite vazio.
Test client: GET do endpoint para uma data com agenda e uma sem.

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Informativo (não bloqueia o orçamento); pt-BR; reusar acesso/idioms existentes;
não quebrar a calculadora.

**Scale/Scope**: 1 endpoint novo (`orcamento/routes.py`), 1 template (`orcamento/index.html`:
id no campo + container), JS (`orcamento.js` ou script da página).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `EventRole`/`CalendarEvent`,
  `role_type` existente e o decorator `_require_vendas`. Sem nova entidade.
- **II. Padrões Python**: ✅ Endpoint pequeno e tipado; query única.
- **III. Arquitetura em camadas**: ✅ Consulta na rota (borda); UI no template/JS.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Recurso aditivo (novo endpoint + bloco
  informativo); não altera o fluxo de cálculo nem o POST do orçamento. Verificação em
  `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Bloco de alerta claro, estado vazio tratado, cores via
  variáveis CSS.
- **VI. Planejar antes de codar**: ✅ Este plano + research + contracts.
- **VII. Valores monetários BR**: N/A.

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/061-personagens-agenda-no-dia/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
├── contracts/agenda-no-dia.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── orcamento/routes.py        # + GET /orcamento/personagens-no-dia (JSON), @_require_vendas
├── templates/orcamento/index.html  # id="event_date" + container #agenda-no-dia + JS de fetch
└── static/js/orcamento.js     # (opcional) função que busca e renderiza ao mudar a data
```

**Structure Decision**: Monolito Flask. Endpoint aditivo + bloco de UI. Sem novo blueprint, sem
migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
