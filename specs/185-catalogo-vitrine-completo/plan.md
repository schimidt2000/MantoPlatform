# Implementation Plan: Catálogo Vitrine Completo — Temas, Personagens e Vídeo

**Branch**: `185-catalogo-vitrine-completo` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/185-catalogo-vitrine-completo/spec.md`

## Summary

Evoluir o módulo de Catálogo em duas superfícies já existentes — Catálogo Público
(`frontend/apps/public`) e Gerenciador Interno (`frontend/apps/internal`) — para suportar uma
relação Tema/Personagem (novo `CatalogCharacter`, filho de `CatalogItem`), vídeo externo
(Drive/MP4/Vimeo) em ambos, vínculo direto de Personagem → Ficha de Figurino, chip input de tags
no gerenciador, `noindex` na vitrine pública, e auto-preenchimento de figurino no formulário de
Novo Evento. Abordagem técnica: migration aditiva (1 tabela nova + 1 coluna nova), reuso máximo
do padrão `*_ops.py`/`json_error`/`@manto/ui`/`@manto/api-client` já estabelecido nas features
133/139/140/141/142/161/169, e extensão dos componentes React existentes (`ProductGallery`,
`wishlist.ts`, `AdminCatalogoFormPage`, `ElencoBlock`) em vez de recriá-los.

## Technical Context

**Language/Version**: Python 3.14 (backend, ver `.python-version`), TypeScript 5.x (frontend, Vite)

**Primary Dependencies**: Flask + SQLAlchemy + Flask-Migrate (backend); React 18 + Vite + Tailwind
CSS + shadcn/ui + Framer Motion + TanStack Query (frontend); `@manto/ui`, `@manto/api-client`,
`@manto/money` (design system e utilitários compartilhados do monorepo)

**Storage**: PostgreSQL (produção Railway; verificação sempre contra `manto_local`, cópia local de
produção — nunca SQLite vazio)

**Testing**: Script Python com test client do Flask (padrão do projeto, requests fora de
`app_context`) contra `manto_local`; `npx tsc --noEmit` + `npm run build` por app; Playwright novo
(setup mínimo, não existe no monorepo ainda) para os fluxos ponta-a-ponta pedidos pelo usuário

**Target Platform**: Web (SPA desacoplada) — navegador do cliente (público, mobile-first) e do
staff (desktop, ERP interno)

**Project Type**: Web application (backend Flask API + 2 frontends React no mesmo monorepo)

**Performance Goals**: Sem meta numérica nova além do padrão do projeto — vídeo é sempre link
externo (nunca servido pelo backend), então não há novo custo de banda no servidor

**Constraints**: Migration 100% aditiva (FR-015); vídeo nunca armazenado no servidor (pedido
explícito do usuário); Vimeo sem SDK adicional (research.md §1, YAGNI)

**Scale/Scope**: 5 User Stories (P1×3, P2×1, P3×1), 17 Functional Requirements, 1 tabela nova + 1
coluna nova, ~6 endpoints novos/estendidos, 2 apps frontend tocados + 1 componente do Agenda

## Constitution Check

*GATE: avaliado antes da Fase 0 e reavaliado após a Fase 1.*

| Princípio | Como esta feature cumpre |
|---|---|
| I — Reutilizar antes de criar | Estende `catalog_ops`/`CatalogItem`/`ProductGallery`/`wishlist.ts`/`AdminCatalogoFormPage`/`ElencoBlock`/`useFigurinoSheets()` existentes em vez de recriar. Nenhum componente novo duplica um já existente (o ChipInput é novo porque não existe hoje — ver research.md, nenhuma lib de terceiros). |
| II — Padrões Python/TS | Novo módulo `app/catalogo/media.py` e `app/admin/catalog_character_ops.py` seguem type hints + docstring Google-style + `CatalogValidationError`; componentes TS novos com interfaces explícitas, zero `any`. |
| III — API First / camadas | Todas as rotas novas em `app/api/*`, delegando a `*_ops.py`; zero `render_template` em código novo; Jinja legado (`app/catalogo/routes.py`) não é tocado. |
| IV — Não quebrar o que funciona | Migration aditiva; produtos existentes sem Personagem/vídeo continuam funcionando (FR-015/SC-005) — verificado no roteiro do `quickstart.md`. |
| V — UI/UX com feedback | Botões de salvar/adicionar usam `loading` do `Button` (`@manto/ui`); erros de validação de `video_url`/nome aparecem no campo via `fieldErrors`, padrão já usado em `AdminCatalogoFormPage`. |
| VI — Planejar antes de codar | Esta esteira (spec → plan → tasks → implement). |
| VII — Dinheiro em BRL | Não aplicável — feature não introduz campo monetário novo. |
| VIII — Mobile-first em superfícies públicas | Galeria com vídeo, seção "Elenco Individual" e botões de ação testados em viewport 320–430px antes de "pronto" (checklist do quickstart). |
| IX — Movimento fluido (Framer Motion) | Extensão do `ProductGallery` (já usa Framer Motion) para vídeo mantém `useReducedMotion()`; sem mudança de estado visual sem transição. |

**Resultado**: PASS — nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/185-catalogo-vitrine-completo/
├── plan.md              # este arquivo
├── research.md           # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── api-catalogo.md   # Fase 1
└── tasks.md               # Fase 2 (/speckit-tasks — ainda não gerado)
```

### Source Code (repository root)

```text
app/
├── models.py                          # + CatalogItem.video_url, + CatalogCharacter (novo)
├── catalogo/
│   ├── routes.py                      # Jinja legado — INTOCADO
│   ├── importer.py                    # reusa _slugify/_rewrite_public_url (sem mudança de assinatura)
│   └── media.py                       # NOVO — classify_video_url() (research.md §2)
├── admin/
│   ├── catalog_ops.py                 # + video_url no create/update_product
│   └── catalog_character_ops.py       # NOVO — CRUD de CatalogCharacter (mesmo padrão de catalog_ops)
└── api/
    ├── catalogo_read.py               # + characters/video_url no detail; + GET /catalogo/elenco-busca
    ├── admin_catalogo_read.py         # + characters/video_url no detail
    └── admin_catalogo_write.py        # + video_url; + POST/PATCH/DELETE .../personagens

migrations/versions/
└── <nova>_catalog_characters_video.py # down_revision=4e6f8a1c2d5b

frontend/apps/public/src/
├── lib/
│   ├── catalogo.ts                    # + tipos CatalogCharacter/video_kind
│   ├── wishlist.ts                    # + kind/parentSlug (research.md §5)
│   └── seo.ts                         # NOVO — useNoIndex()
├── components/
│   ├── ProductGallery.tsx             # + suporte a item de vídeo (mp4/drive/vimeo)
│   ├── CharacterCard.tsx              # NOVO — card do Personagem (Elenco Individual)
│   └── CharacterGrid.tsx              # NOVO — grade "Personagens deste Tema"
└── pages/
    ├── CatalogGridPage.tsx            # + useNoIndex()
    └── ProductDetailPage.tsx          # + useNoIndex(), + <CharacterGrid>, + vídeo do Tema na galeria

frontend/apps/internal/src/
├── lib/
│   ├── adminCatalogo.ts               # + video_url; + hooks de CatalogCharacter (CRUD)
│   └── figurino.ts                    # sem mudança — useFigurinoSheets() reaproveitado
├── components/
│   ├── ChipInput.tsx                  # NOVO — tag input tokenizado genérico (packages/ui candidato futuro)
│   ├── AdminCatalogCharacterPanel.tsx # NOVO — painel de Personagens do formulário do Tema
│   └── EventFormBlocks/
│       └── ElencoBlock.tsx            # + ação "Escolher do catálogo" (prefill figurino_sheet_id)
└── pages/
    └── AdminCatalogoFormPage.tsx      # + campo video_url, + <ChipInput> no lugar do input de tags, + <AdminCatalogCharacterPanel>

frontend/e2e/                          # NOVO — setup mínimo de Playwright (não existia)
└── catalogo.spec.ts
```

**Structure Decision**: Monorepo já existente (`frontend/apps/{public,internal}` + `app/` Flask) —
nenhuma estrutura nova de projeto, só arquivos novos/estendidos dentro dos módulos já
estabelecidos pela migração 144. `ChipInput` nasce local a `apps/internal` (não em
`packages/ui`) porque só há um consumidor até esta feature — promovê-lo a pacote compartilhado é
decisão futura se um segundo consumidor aparecer (YAGNI).

## Complexity Tracking

*Sem violações da Constitution Check — tabela vazia.*
