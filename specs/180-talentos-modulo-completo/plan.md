# Implementation Plan: Reestruturação do Módulo de Talentos (Listagem, Filtros e Perfil)

**Branch**: `180-talentos-modulo-completo` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/180-talentos-modulo-completo/spec.md`

## Summary

Reestruturar a experiência React de Talentos em duas telas: (1) `/talents` ganha um painel de
filtros avançados rico (dropdowns por categoria, aplicação em lote via botão "Filtrar", grid de
5-6 colunas) com fidelidade ao comportamento do Jinja legado; (2) `/talents/:id` deixa de ser
somente-leitura-com-controles-sempre-visíveis e passa a ter um alternador explícito
leitura/edição na mesma página (a rota separada `/talents/:id/edit` é descontinuada como tela
própria e vira um redirect), reorganizada em duas colunas com KPIs de histórico, filtro de
período e uma seção nova de Avaliações/Notas hoje ausente no React. O núcleo de negócio
(`app/talents/talent_ops.py`, `app/talents/rating_ops.py`) ganha 3 capacidades novas
(comparação de altura "=", último evento no histórico, leitura de avaliações por talento) sempre
como funções puras reusadas pelos dois adaptadores (Jinja/API), sem tocar nos templates/rotas
Jinja existentes além da extração pontual (paridade) do endpoint de sugestão de personagens.

## Technical Context

**Language/Version**: Python 3.11 (Flask, SQLAlchemy) + TypeScript 5.7 (React 18, Vite 6)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Login — TanStack Query 5, React Router 6,
Tailwind CSS 3, `@manto/ui` (shadcn/ui-style), Framer Motion, `@manto/api-client`, `@manto/money`.
Nova dependência de teste: `@playwright/test` (não existe no monorepo hoje).

**Storage**: PostgreSQL (produção via Railway; verificação local sempre contra `manto_local`,
cópia local do banco real — nunca SQLite). Sem migration nova: nenhum campo novo em
`app/models.py` é necessário (altura "=", último evento e avaliações são todos derivados de
tabelas já existentes — `Talent`, `EventRole`, `EventRating`, `EventSubRating`).

**Testing**: Backend — script de verificação funcional com Flask test client contra `manto_local`
(padrão já usado no projeto, requests fora de `app_context`). Frontend — `tsc --noEmit` +
`npm run build`. E2E novo — Playwright (`@playwright/test`), a introduzir do zero.

**Target Platform**: Web (SPA servida como estático em produção via Railway; dev local via Vite).

**Project Type**: Web application (frontend React desacoplado + backend Flask API JSON), dentro
de um monorepo já existente.

**Performance Goals**: Sem alvo numérico novo — mesma expectativa do restante do app (interações
percebidas como instantâneas; paginação server-side já existente evita carregar mais de 60
talentos por vez).

**Constraints**: Zero alteração em `app/templates/talents_list.html`, `app/templates/talent_detail.html`,
`app/templates/talent_edit.html` e nas rotas/handlers Jinja de `app/talents/routes.py` (só é
permitida a extração pontual, sem mudança de comportamento, do endpoint de sugestão de
personagens — ver Research). Toda alteração de UI ocorre em `frontend/apps/internal`.

**Scale/Scope**: 2 telas React reestruturadas (`TalentsListPage`, `TalentDetailPage`), 1 tela
removida (`TalentEditPage`, absorvida em `TalentDetailPage`), 1 componente novo no design system
(dropdown de filtro reutilizável), 1 endpoint novo (`GET /api/talents/<id>/ratings`), extensões
pontuais em 2 endpoints existentes (`directory`, detalhe) e no núcleo `talent_ops.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano cumpre |
|---|---|
| I — Reutilizar antes de criar | `talent_ops.py`/`rating_ops.py` existentes são estendidos, não duplicados; `FileUpload` de `@manto/ui` é estendido (suporte a arquivo já existente + remoção) em vez de manter `TalentPhotoField` como implementação paralela; endpoint de sugestão de personagem do Jinja é extraído para função compartilhada em vez de duplicado. |
| II — Padrões de código | Novo componente `FilterDropdown` em TS estrito, com props tipadas; funções Python novas com type hints + docstring Google style. |
| III — Arquitetura em camadas / API First | Toda leitura/escrita nova nasce em `app/api/talents_read.py`/`talents_write.py`, delegando a `*_ops.py`; nenhuma rota nova usa `render_template`. |
| IV — Não quebrar o que funciona | `tsc --noEmit`, `npm run build` e verificação funcional contra `manto_local` antes de cada commit; extração do endpoint de sugestão de personagem preserva o contrato JSON exato consumido pelo Jinja (mesmo formato de resposta), só muda a localização da query. |
| V — UI/UX com feedback | Painel de filtros usa `Skeleton`/loading do TanStack Query já padrão; botão "Filtrar" e "Salvar" usam estado `loading` do `Button`; modo edição preserva os dados digitados em erro de validação (reaproveita padrão já usado em `TalentEditPage`). |
| VI — Planejar antes de codar | Esteira SpecKit completa (`specify` → `plan` → `tasks` → `implement`) sendo seguida agora. |
| VII — Valores monetários em BRL | "Total Faturado" e "Cachê" continuam usando `formatBRL`/`@manto/money`, já em uso na tela atual — nenhuma formatação nova a inventar. |
| VIII — Mobile-first em superfícies públicas | Não se aplica — `/talents` é superfície interna (staff autenticado), não pública; ainda assim o layout usa grid responsivo (1 coluna em mobile → 2 em widescreen), sem quebrar em telas pequenas. |
| IX — Movimento com propósito | Abertura/fechamento dos dropdowns de filtro e a transição leitura↔edição usam Framer Motion (`AnimatePresence` + fade/slide curto), respeitando `useReducedMotion()`. |

Nenhuma violação identificada — Complexity Tracking não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/180-talentos-modulo-completo/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── talents-perfil-e-filtros.md
└── tasks.md              # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── talents/
│   ├── routes.py                 # Jinja legado — só a extração pontual de character_suggestions
│   ├── talent_ops.py             # + suggest_characters(), + height_op "eq", + last_event no histórico
│   └── rating_ops.py             # + get_talent_ratings_overview(talent, viewer_is_superadmin)
└── api/
    ├── talents_read.py           # + GET /api/talents/<id>/ratings, + GET /api/talents/character-suggestions
    └── talents_write.py          # inalterado (nenhuma escrita nova)

frontend/
├── packages/
│   └── ui/src/components/
│       ├── filter-dropdown.tsx   # NOVO — popover de filtro (checkbox list + busca interna opcional)
│       └── file-upload.tsx       # + props existingUrl/existingLabel/onRemoveExisting
└── apps/internal/
    ├── e2e/                      # NOVO — Playwright
    │   ├── talents-list.spec.ts
    │   └── talents-detail.spec.ts
    ├── playwright.config.ts      # NOVO
    └── src/
        ├── App.tsx                # rota /talents/:id/edit vira redirect
        ├── lib/talents.ts         # + TalentRatings types/hook, + last_event no TalentDetail
        ├── components/
        │   ├── TalentMosaic.tsx   # grid 5-6 colunas confirmado, badge de medidas (sem mudança funcional grande)
        │   └── TalentFilterPanel.tsx  # NOVO — extrai o painel de filtros do TalentsListPage
        └── pages/
            ├── TalentsListPage.tsx    # usa TalentFilterPanel + aplica com botão "Filtrar"
            ├── TalentDetailPage.tsx   # + modo leitura/edição, 2 colunas, KPIs, avaliações, aprovação
            └── TalentEditPage.tsx     # REMOVIDA (lógica absorvida em TalentDetailPage)
```

**Structure Decision**: Aplicação web já desacoplada (Option 2 do template, já materializada no
repo como `app/` + `frontend/`). Nenhuma pasta nova de topo-nível — a feature vive inteiramente
dentro das árvores já existentes `app/talents`, `app/api`, `frontend/packages/ui`,
`frontend/apps/internal`.

## Complexity Tracking

*Sem violações da constituição — seção não aplicável.*
