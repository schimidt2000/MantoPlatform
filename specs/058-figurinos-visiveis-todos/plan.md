# Implementation Plan: Figurinos visíveis a todos (edição restrita)

**Branch**: `058-figurinos-visiveis-todos` | **Date**: 2026-06-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/058-figurinos-visiveis-todos/spec.md`

## Summary

Abrir a **visualização** de figurinos para todos os usuários autenticados (link no menu +
lista + impressão) e **restringir as edições** (criar/editar/excluir ficha, girar foto,
sincronizar Drive) a SUPERADMIN e FIGURINO — no servidor (recusa por URL direta) e na UI
(botões só para quem pode editar). Sem mudança de modelo, sem migration.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (Jinja2 + HTML/CSS/JS vanilla)

**Primary Dependencies**: Flask, Flask-Login (RBAC). Nenhuma nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). **Sem mudança de schema, sem migration.**

**Testing**: Sem suíte automatizada — verificação manual via `quickstart.md` + test client.

**Target Platform**: App web (Railway/produção), mobile-first.

**Project Type**: Web application (Flask monolito).

**Constraints**: Recusa no servidor (não só esconder botão); textos pt-BR; reutilizar o
padrão de checagem de papel já existente no projeto.

**Scale/Scope**: ~3 arquivos (figurino/routes.py, base.html, figurinos.html). Sem rota nova.

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa o padrão de checagem de papel
  (helper local, como `_is_superadmin()` já existente em `figurino/routes.py`) e o
  `eff_has_role` do Jinja (usado em `base.html`). Sem lógica nova paralela.
- **II. Padrões Python**: ✅ Helper pequeno `_can_edit_figurino()` com docstring; guardas
  `abort(403)` no topo das rotas de mutação.
- **III. Arquitetura em camadas**: ✅ Guarda na rota; template só decide exibir botões.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ FIGURINO/SUPERADMIN seguem com as
  mesmas ações; leitura/impressão inalteradas. Verificação no app real (quickstart).
- **V. UI/UX consistente (pt-BR)**: ✅ Botões de edição só para quem pode; acesso negado
  reutiliza a página 403 existente; sem cor hardcoded nova.
- **VI. Planejar antes de codar**: ✅ Este plano.
- **VII. Valores monetários BR**: N/A.

**Resultado**: PASS — sem violações, sem migration. (Bônus de segurança: fecha rotas de
edição que hoje só exigiam login.)

## Project Structure

### Documentation (this feature)

```text
specs/058-figurinos-visiveis-todos/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
├── contracts/access.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── figurino/routes.py        # + _can_edit_figurino(); guarda abort(403) nas rotas de mutação
└── templates/
    ├── base.html             # menu: link Figurinos visível a todos os autenticados
    └── figurinos.html        # botões de criar/editar/excluir/sync só para quem pode editar
```

**Structure Decision**: Monolito Flask existente. Guarda de papel nas rotas de mutação +
liberação do link/visualização. Sem novo blueprint, sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
