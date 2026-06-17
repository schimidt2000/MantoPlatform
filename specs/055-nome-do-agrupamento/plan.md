# Implementation Plan: Nome do agrupamento de eventos

**Branch**: `055-nome-do-agrupamento` | **Date**: 2026-06-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/055-nome-do-agrupamento/spec.md`

## Summary

Adicionar um **nome ao agrupamento** (campo no evento principal) e usá-lo como rótulo único
do grupo na **home comercial** e nos **balanços financeiros**, exibindo o grupo como uma só
entrada (sem listar satélites como itens/linhas próprias). Reutiliza o vínculo de
agrupamento das features 053/054; o cálculo consolidado (grupo = 1 venda, custos somados no
principal) já existe e não muda — muda a **apresentação**. Inclui uma migration manual para
o novo campo `group_name`.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (Jinja2 + HTML/CSS/JS vanilla)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Migrate/Alembic, Flask-Login (RBAC).
Nenhuma dependência nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). **Uma mudança de schema**: nova coluna
`calendar_events.group_name` (String, nullable). Migration manual (autogenerate quebrado por
drift — ver memória do projeto), `down_revision = q3f4a5b6c7d8` (head atual).

**Testing**: Sem suíte automatizada (`pytest`/`conftest.py` inexistentes) — verificação
manual via `quickstart.md`, como nas features 051–054.

**Target Platform**: App web (Railway/produção), mobile-first.

**Project Type**: Web application (Flask monolito).

**Performance Goals**: Sem impacto — apenas leitura de um campo já carregado e filtros que
reusam índices existentes.

**Constraints**: Reuso do mecanismo 053/054; rótulo com fallback para o título; textos
pt-BR; edição com feedback e sem envio duplicado; valores em padrão BR (inalterado).

**Scale/Scope**: 1 campo novo + 1 migration; ~6 arquivos tocados (model, calendar/routes,
__init__ home, financeiro/routes, e 3 templates). Sem nova entidade.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa o vínculo 053/054 e o
  action-dispatch (`_EVENT_ACTIONS`); o rótulo do grupo é uma **única** propriedade
  (`group_display_name`) consumida por todas as telas — sem reinventar por tela.
- **II. Padrões Python**: ✅ Propriedade/handler com type hints e docstring; funções
  pequenas.
- **III. Arquitetura em camadas**: ✅ Rotas orquestram; a regra de exibição é uma
  propriedade do modelo; queries da home/financeiro só ganham um filtro de satélite.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Eventos não agrupados inalterados;
  cálculo financeiro do grupo idêntico (053). Verificação no app real no quickstart.
- **V. UI/UX com feedback (pt-BR)**: ✅ Campo de nome opcional ao agrupar e edição na tela
  do principal; botão de salvar desabilita ao enviar (anti-duplo-envio); valores preservados
  em erro; cores via variáveis CSS.
- **VI. Planejar antes de codar**: ✅ Este plano.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Sem mudança em formatação de dinheiro.

**Migration gate**: ✅ Mudança em `models.py` → migration manual criada (Phase 1/data-model).

**Resultado**: PASS — sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/055-nome-do-agrupamento/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── group-name.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
app/
├── models.py                          # + coluna group_name; + propriedade group_display_name
├── calendar/
│   └── routes.py                      # _handle_group_events lê group_name; ação rename_group
├── __init__.py                        # home: events_sem_valor exclui satélites
├── financeiro/
│   └── routes.py                      # dashboard: events_data exclui satélites (tabela)
└── templates/
    ├── event_detail.html              # campo "nome do grupo" no agrupar + edição no principal + nome no banner
    ├── home.html                      # cobranças/sem-valor usam group_display_name
    └── financeiro/dashboard.html      # tabela de eventos usa group_display_name
migrations/versions/
└── <rev>_group_name.py                # migration manual (down_revision q3f4a5b6c7d8)
```

**Structure Decision**: Monolito Flask existente. Nova coluna + propriedade de exibição como
fonte única do rótulo; as telas (home, dashboard) apenas consomem a propriedade e ganham um
filtro para ocultar satélites. Sem nova entidade, sem novo blueprint.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
