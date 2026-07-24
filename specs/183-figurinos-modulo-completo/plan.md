# Implementation Plan: Reestruturação do Banco de Figurinos

**Branch**: `183-figurinos-modulo-completo` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/183-figurinos-modulo-completo/spec.md`

## Summary

Reestruturar `frontend/apps/internal/src/pages/FigurinoListPage.tsx` (e o formulário associado)
para uma grade densa de 5-6 colunas com enquadramento vertical de foto, ações rápidas de
Imprimir/Editar por card, um painel "Figurinos Faltantes" restrito a SUPERADMIN e colapsável
com ações de descartar/associar, e busca + filtro por tags. O trabalho de UI fica 100% em
`frontend/apps/internal`; a única extensão de backend é a mínima necessária para persistir tags,
o descarte de alertas de personagem sem ficha e a associação de cargos de evento a uma ficha —
seguindo o padrão já usado por toda rota nova do repo (`app/api/figurino_*.py` +
`app/figurino/figurino_ops.py`). Nenhuma view/template Jinja legado é tocada.

## Technical Context

**Language/Version**: Python 3.14 (Flask/SQLAlchemy) + TypeScript 5 / React 18 (Vite)

**Primary Dependencies**: Flask, SQLAlchemy, Alembic (Flask-Migrate) · React, TanStack Query,
Tailwind CSS, `@manto/ui` (Button, Card, PageHeader, Skeleton, FilterDropdown/CheckboxList),
`@manto/api-client` (apiFetch, assetUrl), Framer Motion

**Storage**: PostgreSQL (produção Railway; verificação sempre contra `manto_local`)

**Testing**: Playwright (`frontend/apps/internal/e2e/`) contra `manto_local`; script de
verificação funcional com Flask test client (padrão `verify_*.py`) contra `manto_local`

**Target Platform**: Web (staff autenticado, desktop-first — módulo interno, não é superfície
pública mobile-first)

**Project Type**: Web app (frontend React desacoplado + backend Flask API JSON)

**Performance Goals**: Filtro de busca/tag client-side, sem chamada de rede adicional (dataset já
carregado por `useFigurinoSheets`); resposta perceptível <300ms ao digitar (SC-006)

**Constraints**: Zero alteração em `app/figurino/routes.py` e `app/templates/figurino_*.html`
(FR-015); RBAC de escrita (FIGURINO/SUPERADMIN) e de visibilidade do painel (SUPERADMIN)
validado tanto no frontend (ocultar) quanto no backend (403 defensivo)

**Scale/Scope**: Banco de figurinos da Manto (centenas de fichas); 2 telas React tocadas
(`FigurinoListPage`, `FigurinoFormPage`), ~4 endpoints de API novos/estendidos, 1 migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: `SectorPanel` (painel colapsável, já usado no Dashboard) é
  reaproveitado para o painel de faltantes; `FilterDropdown`/`CheckboxList` (já usados na busca de
  Talentos, feature 180) são reaproveitados para o filtro de tags; o `<select>` nativo de ficha de
  figurino já existe em `EventCreatePage.tsx` e serve de referência para o seletor "associar a uma
  ficha existente". Nenhum componente novo de design system é criado. **PASS**.
- **II. Padrões de código**: type hints + docstrings no Python novo; TypeScript estrito (sem
  `any`) nos hooks/props novos. **PASS** (verificado na implementação).
- **III. Arquitetura em camadas**: novos endpoints ficam em `app/api/figurino_write.py`
  (write) e a lógica em `app/figurino/figurino_ops.py` (ops puro) — nenhuma regra de negócio na
  rota. **PASS**.
- **IV. Não quebrar o que funciona**: `chars_without_sheet` muda de `string[]` para uma lista de
  objetos (`{character_name, character_name_norm}`) na função `figurino_ops.list_sheets()`,
  usada **apenas** pelo endpoint de API (`/api/figurino`). Confirmado por busca no repo: a view
  Jinja legada (`app/figurino/routes.py::figurinos()`) **não chama** `list_sheets()` — ela já
  tinha sua própria query inline duplicada (mesma lógica, independente) que alimenta
  `figurinos.html`. Logo, alterar o retorno de `list_sheets()` não afeta o Jinja legado (FR-015);
  o único consumidor do novo formato é a própria `FigurinoListPage` (reescrita nesta mesma
  feature). **PASS**.
- **V. UI/UX (feedback, sem botão morto, confirmação destrutiva)**: Imprimir/Editar/Descartar/
  Associar usam `loading`/`disabled` do `Button`; descarte usa `window.confirm()` (padrão já
  adotado, sem Dialog no design system); toasts de erro em pt-BR via padrão já usado nas mutations
  existentes. **PASS**.
- **VI. Planejar antes de codar**: esta é a execução do fluxo spec-kit completo. **PASS**.
- **VII. Valores monetários**: não aplicável (sem valores monetários nesta feature). **N/A**.
- **VIII. Mobile-first em superfícies públicas**: não aplicável — `/figurinos` é superfície
  interna de staff, não pública; ainda assim a grade degrada para 1-3 colunas em telas estreitas
  (não quebra). **N/A / degradação razoável aplicada**.
- **IX. Movimento com propósito**: abertura/fechamento do painel de faltantes e expansão dos
  filtros usam Framer Motion (via `SectorPanel`/`FilterDropdown`, que já implementam
  `useReducedMotion()`). **PASS**.

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/183-figurinos-modulo-completo/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── api-figurino.md   # Phase 1 output — contrato dos endpoints novos/alterados
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
# Backend — extensão mínima, sem tocar Jinja legado
app/
├── models.py                      # + FigurinoSheet.tags; + model FigurinoMissingDismissal
├── figurino/
│   └── figurino_ops.py            # list_sheets() reescrito (cobertura por figurino_sheet_id
│                                   #   OU nome); + dismiss_missing_character(); +
│                                   #   associate_missing_character(); create/edit_sheet aceitam tags
└── api/
    └── figurino_write.py          # + POST /api/figurino/faltantes/dispensar
                                    # + POST /api/figurino/faltantes/associar
                                    # (create/edit existentes passam a aceitar `tags`)

migrations/versions/
└── <hash>_figurino_tags_e_faltantes.py   # tags em figurino_sheets + tabela
                                            # figurino_missing_dismissals

# Frontend — 100% do trabalho de UI
frontend/apps/internal/src/
├── lib/
│   └── figurino.ts                # tipos atualizados (tags, MissingCharacter);
│                                   #   useDismissMissingCharacter(); useAssociateMissingCharacter()
├── pages/
│   ├── FigurinoListPage.tsx       # grade densa 5-6 col, busca, filtro de tags, painel faltantes
│   └── FigurinoFormPage.tsx       # + editor de tags (chips)
└── e2e/
    └── figurinos.spec.ts          # Playwright: grade, ações de card, painel RBAC, busca/filtro
```

**Structure Decision**: Web app já existente (frontend `apps/internal` + backend Flask `app/`).
Reaproveita a estrutura de pastas em camadas já estabelecida pelas features 154/155 (figurino) —
sem introduzir novos diretórios ou padrões.

## Complexity Tracking

*Sem violações da constituição a justificar.*
