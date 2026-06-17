# Implementation Plan: Cancelar ensaio órfão (sem evento na agenda)

**Branch**: `057-cancelar-ensaio-orfao` | **Date**: 2026-06-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/057-cancelar-ensaio-orfao/spec.md`

## Summary

Expor o cancelamento de ensaios para os casos em que hoje ele é inacessível: ensaios
**órfãos** (show pai removido da agenda), a **página do próprio ensaio** e o painel da
**home**. A ação interna já existe (`delete_ensaio`, que remove o ensaio do sistema e do
Google Calendar sem tocar no show pai) — esta feature só adiciona a **descoberta** dos
órfãos e os **botões** que disparam essa ação. Sem mudança de modelo, sem migration.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (Jinja2 + HTML/CSS/JS vanilla)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Login (RBAC), Google Calendar API
(remoção do evento de ensaio — já usada por `delete_ensaio`). Nenhuma nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). **Sem mudança de schema, sem migration** —
reusa `CalendarEvent` (event_type="ENSAIO", `parent_event_id`/`parent`).

**Testing**: Sem suíte automatizada — verificação manual via `quickstart.md`.

**Target Platform**: App web (Railway/produção), mobile-first.

**Project Type**: Web application (Flask monolito).

**Performance Goals**: Query de órfãos leve (poucos ensaios; filtro por `event_type` +
ausência de pai).

**Constraints**: Ação destrutiva exige confirmação; nunca afeta o show pai; RBAC de ensaio;
textos pt-BR; remoção no Google falha de forma graciosa (avisa, não trava).

**Scale/Scope**: ~3 arquivos (home route, home template, event_detail template). Reusa a
rota `POST /events/<id>/delete-ensaio` existente — **nenhuma rota nova**.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa a rota `delete_ensaio` (que já
  trata órfão: redireciona para a home quando não há pai) e o helper de papel `_CAN_ENSAIO`.
  Nenhuma lógica nova de cancelamento.
- **II. Padrões Python**: ✅ Só uma query de órfãos pequena e bem nomeada na rota da home.
- **III. Arquitetura em camadas**: ✅ Rota monta a lista; a regra de cancelar já está
  isolada na rota `delete_ensaio`.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Cancelar ensaio nunca toca no show
  pai (já garantido); os blocos novos são aditivos. Verificação no app real (quickstart).
- **V. UI/UX com feedback (pt-BR)**: ✅ Botão "Cancelar ensaio" com **confirmação** (ação
  destrutiva) na home, na página do ensaio e na lista de órfãos; mensagens de sucesso/aviso
  já existentes na rota; cores via variáveis CSS.
- **VI. Planejar antes de codar**: ✅ Este plano.
- **VII. Valores monetários BR**: N/A — sem valores monetários.

**Resultado**: PASS — sem violações, sem migration.

## Project Structure

### Documentation (this feature)

```text
specs/057-cancelar-ensaio-orfao/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cancel-ensaio.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
app/
├── __init__.py                      # home: query orphan_ensaios + passa ao template
└── templates/
    ├── home.html                    # seção "Ensaios sem show" (órfãos) + botão Cancelar na lista existente
    └── event_detail.html            # bloco "Cancelar ensaio" quando event_type == 'ENSAIO'
```

**Structure Decision**: Monolito Flask existente. Toca 1 rota (home) para descobrir órfãos e
2 templates para expor o botão de cancelar (reusando a rota `delete_ensaio`). Sem novo
blueprint, sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
