# Implementation Plan: Avaliações anônimas + função no evento

**Branch**: `056-avaliacoes-anonimas` | **Date**: 2026-06-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/056-avaliacoes-anonimas/spec.md`

## Summary

Anonimizar a autoria dos comentários na página `/talents/avaliacoes`: por padrão, todos
veem "Anônimo", **exceto super admin**, que vê o nome real — salvo quando o **modo anônimo
total** (interruptor global, controlado por um botão na página, só super admin) estiver
ativo, caso em que nem o super admin vê. Quando a autoria está visível, exibir ao lado do
nome a **função do talento no evento**. No **portal**, avisar claramente que as avaliações
são anônimas. Anonimização feita **no servidor** (o nome/função nem chega ao HTML quando
anônimo). Inclui migration para um flag em `SiteSetting`.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (Jinja2 + HTML/CSS/JS vanilla)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Migrate/Alembic, Flask-Login (RBAC).
Nenhuma dependência nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). **Uma mudança de schema**:
`site_settings.ratings_fully_anonymous` (Boolean, default False). Migration manual,
`down_revision = r4a5b6c7d8e9` (head atual).

**Testing**: Sem suíte automatizada — verificação manual via `quickstart.md`.

**Target Platform**: App web (Railway/produção), mobile-first.

**Project Type**: Web application (Flask monolito).

**Performance Goals**: Lookup de função em **uma** query batch (sem N+1) para os comentários
exibidos.

**Constraints**: Anonimato **real** (sem nome/função/link no HTML quando anônimo);
toggle só super admin; textos pt-BR; botão com feedback e sem envio duplicado.

**Scale/Scope**: 1 flag novo + 1 migration; ~5 arquivos (model, talents/routes, 1 template
da página, 2 templates do portal). Sem nova entidade.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `_comment_item`, o helper de
  papel `_can_edit_talent`, `SiteSetting` (singleton id=1), `AuditLog` para o log do toggle
  e `EventRole`/`strip_role_prefix` para a função. Sem lógica paralela.
- **II. Padrões Python**: ✅ Helpers pequenos com type hints/docstring (anonimização e mapa
  de funções).
- **III. Arquitetura em camadas**: ✅ A rota decide `show_authors`; a regra de exibição vive
  em helpers; sem queries espalhadas (função carregada em 1 batch).
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Notas/médias/indicadores
  inalterados; só a exibição da autoria muda. Verificação no app real (quickstart).
- **V. UI/UX com feedback (pt-BR)**: ✅ Botão de modo total com confirmação e estado de
  carregamento (anti-duplo-envio); aviso de anonimato no portal; cores via variáveis CSS.
- **VI. Planejar antes de codar**: ✅ Este plano.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: N/A — sem valores monetários.

**Privacidade (NÃO-NEGOCIÁVEL implícito)**: anonimização **no servidor** — o nome e a função
não são renderizados quando o comentário é anônimo (não basta esconder via CSS).

**Migration gate**: ✅ Mudança em `models.py` → migration manual.

**Resultado**: PASS — sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/056-avaliacoes-anonimas/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── anonymity.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
app/
├── models.py                              # + SiteSetting.ratings_fully_anonymous
├── talents/
│   └── routes.py                          # show_authors; _comment_item anonimiza; mapa de funções; rota toggle
└── templates/
    ├── talents/avaliacoes.html            # botão de modo total (super admin); função ao lado do nome
    └── portal/
        ├── rate.html                      # aviso de anonimato
        └── rate_detail.html               # aviso de anonimato
migrations/versions/
└── <rev>_ratings_fully_anonymous.py       # migration manual (down_revision r4a5b6c7d8e9)
```

**Structure Decision**: Monolito Flask existente. A anonimização é decidida no servidor
(rota + `_comment_item`); o flag global vive em `SiteSetting`; a função vem de `EventRole`
em uma query batch. Sem nova entidade, sem novo blueprint.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
