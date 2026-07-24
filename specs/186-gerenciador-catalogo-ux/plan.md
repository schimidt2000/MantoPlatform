# Implementation Plan: Gerenciador de Catálogo — UX e Fluxo Ficha↔Catálogo↔Venda

**Branch**: `186-gerenciador-catalogo-ux` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/186-gerenciador-catalogo-ux/spec.md`

## Summary

Evoluir o Gerenciador de Catálogo Interno (`frontend/apps/internal`) com: amarração bidirecional
Ficha↔Personagem (inclusive a partir da tela de Ficha), busca visual (com foto) de Personagens no
elenco de eventos, alternador Cards/Árvore em `/admin/catalogo`, kebab menu + seleção múltipla com
ações em massa (mover/inativar/excluir), UX de capa/reordenação de fotos mais direta, e a correção
real do link "Catálogo" do menu — que depende de servir `apps/public` sob `/catalogo/*` no mesmo
serviço Railway do `apps/internal` (não existe hoje nenhum deploy separado do app público).
Nenhuma migration de banco — só extensão de respostas de API e reatribuição de FKs já existentes.

## Technical Context

**Language/Version**: Python 3.14, TypeScript 5.x

**Primary Dependencies**: Flask + SQLAlchemy (backend, sem mudança); React + Vite + Tailwind +
`@manto/ui` + TanStack Query (frontend, sem mudança); `serve-handler` (nova, backend estático do
monorepo `frontend/` — substitui uso da CLI `serve` por uso programático)

**Storage**: PostgreSQL — nenhuma migration nesta feature

**Testing**: `verify_186.py` (padrão `specs/*/verify_*.py`) + Playwright (`apps/internal/e2e`,
config já existe desde a feature 180) + `apps/public/e2e` (config da feature 185, cobrindo o novo
prefixo `/catalogo` em modo de build de produção via `vite preview`)

**Target Platform**: Web — painel interno (desktop, ERP) + vitrine pública (mobile-first, sem
mudança de UI nesta feature, só de path)

**Project Type**: Web application (mesmo monorepo das features 144/185)

**Performance Goals**: Sem meta numérica nova — árvore/lista/ações em massa operam sobre o volume
atual do catálogo (centenas de itens, não milhares), sem paginação nova necessária

**Constraints**: Zero migration; zero Dialog novo no design system (Assumption/Governança —
"mover em massa" é painel inline, não modal); deploy dual-app não pode quebrar o app interno
existente (fallback de SPA próprio por prefixo)

**Scale/Scope**: 6 User Stories (P1×3, P2×3), 17 Functional Requirements, 1 endpoint novo + 2
estendidos, ~8 componentes novos/estendidos em `apps/internal`, 1 servidor estático novo para o
monorepo `frontend/`

## Constitution Check

*GATE: avaliado antes da Fase 0 e reavaliado após a Fase 1.*

| Princípio | Como esta feature cumpre |
|---|---|
| I — Reutilizar antes de criar | `elenco-busca`/`catalog_character_ops` (feature 185) estendidos, não recriados; `FilterDropdown` como referência de padrão enxuto para o `KebabMenu` novo; ações em massa de inativar/excluir reaproveitam endpoints já existentes em vez de criar variantes "em lote" redundantes. |
| II — Padrões Python/TS | Endpoint novo (`mover-em-massa`) com type hints + docstring + `CatalogValidationError`; componentes TS novos com interfaces explícitas, zero `any`. |
| III — API First / camadas | Endpoint novo em `app/api/admin_catalogo_write.py`, delega a `catalog_character_ops.py`; zero lógica de negócio na rota. |
| IV — Não quebrar o que funciona | Deploy dual-app mantém 100% do comportamento atual do app interno (fallback próprio); Vite `base`/`basename` do app público são condicionais a `PROD`, preservando dev local e os testes Playwright da feature 185 inalterados. |
| V — UI/UX com feedback | Ações em massa usam `window.confirm()` (padrão já estabelecido) antes de inativar/excluir; toda mutação usa `loading` do `Button`. |
| VI — Planejar antes de codar | Esta esteira (spec → plan → tasks → implement). |
| VIII — Mobile-first em superfícies públicas | Não aplicável a este trabalho (100% `apps/internal`, ERP desktop) — a única superfície pública tocada (`apps/public`) muda só de path de build, zero mudança visual. |
| IX — Movimento fluido | Expandir/recolher na árvore e a barra flutuante de ações em massa usam transição Framer Motion (150–350ms), respeitando `useReducedMotion()`. |

**Resultado**: PASS — nenhuma violação a justificar.

## Project Structure

### Documentation (this feature)

```text
specs/186-gerenciador-catalogo-ux/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/api-catalogo-ux.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── admin/catalog_character_ops.py     # + move_characters()
└── api/
    ├── catalogo_read.py               # elenco-busca: + photo_url, RBAC ampliado (FIGURINO)
    ├── admin_catalogo_read.py         # GET /admin/catalogo: + characters[] resumido por item
    └── admin_catalogo_write.py        # + POST .../personagens/mover-em-massa

frontend/
├── server.js                          # NOVO — dual-app static server (serve-handler)
├── package.json                       # + serve-handler; start aponta pro server.js novo
├── railway.json / nixpacks.toml       # build compila os dois apps; start = node server.js
├── apps/public/
│   ├── vite.config.ts                 # + base condicional a PROD
│   └── src/App.tsx                    # + basename condicional a PROD
└── apps/internal/src/
    ├── components/
    │   ├── KebabMenu.tsx               # NOVO — menu de 3 pontos genérico
    │   ├── CharacterAutocomplete.tsx   # NOVO — busca com foto em miniatura
    │   ├── CatalogBulkActionBar.tsx    # NOVO — barra flutuante de ações em massa
    │   ├── CatalogTreeView.tsx         # NOVO — modo Árvore
    │   ├── CatalogCardGrid.tsx         # NOVO — modo Cards (extraído/refatorado da list page)
    │   └── EventFormBlocks/ElencoBlock.tsx  # + usa CharacterAutocomplete
    ├── lib/
    │   ├── adminCatalogo.ts           # + tipos/hook de characters no summary, mover-em-massa
    │   └── catalogoElenco.ts          # + photo_url no tipo
    └── pages/
        ├── AdminCatalogoListPage.tsx   # orquestra Cards/Árvore + seleção
        ├── AdminCatalogoFormPage.tsx   # + badge de capa, drag-and-drop de fotos
        └── FigurinoFormPage.tsx        # + campo "Vincular a um Personagem do Catálogo"

specs/186-gerenciador-catalogo-ux/verify_186.py
frontend/apps/internal/e2e/catalogo-ux.spec.ts   # NOVO
frontend/apps/public/e2e/catalogo-prefixo.spec.ts # NOVO — valida /catalogo/* em build de produção
```

**Structure Decision**: Mesmo monorepo, mesmos dois apps — nenhuma estrutura de projeto nova.
`frontend/server.js` é a única peça de infraestrutura nova, no nível do monorepo (não dentro de
nenhum app), porque serve os dois `dist` ao mesmo tempo.

## Complexity Tracking

*Sem violações da Constitution Check — tabela vazia.*
