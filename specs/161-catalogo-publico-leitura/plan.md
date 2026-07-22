# Implementation Plan: Catálogo Público em React (Leitura)

**Branch**: `161-catalogo-publico-leitura` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/161-catalogo-publico-leitura/spec.md`

## Summary

Primeira fatia da US5 (Superfícies Públicas) — migra as 5 telas do Catálogo Público
(`app/catalogo`, hoje Jinja/vanilla, sem login) para o app `frontend/apps/public` (hoje só
stub), consumindo 4 endpoints JSON novos em `app/api/catalogo_read.py`. Só leitura: grade geral
com busca/filtro client-side, grade de categorias, itens por categoria, detalhe do produto (com
a galeria animada da feature 143 recriada em Framer Motion) e lista de desejos (continua 100%
`localStorage`, sem backend novo). As rotas Jinja `/catalogo/*` continuam no ar em paralelo —
inclusive a de detalhe, cujo HTML server-rendered com tags Open Graph é hoje o que gera a prévia
de link no WhatsApp (SPA client-side não serve prévia a robôs que não executam JS).

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript 5.7 (frontend)

**Primary Dependencies**: Flask + SQLAlchemy (reaproveitados, zero dependência nova no
backend). Frontend: React 18 + Vite + react-router-dom + TanStack Query + Tailwind CSS +
`@manto/ui` (shadcn/ui) + Framer Motion — todas já usadas em `apps/internal`, mas **nenhuma
delas está instalada em `apps/public` ainda** (hoje só tem `react`/`react-dom`, ver
`research.md` §1). Nenhuma dependência nova além das já usadas no monorepo.

**Storage**: PostgreSQL (`manto_local` para verificação) — mesmas tabelas já existentes
(`catalog_items`, `catalog_categories`, `catalog_item_images`), nenhum campo/migration novo.

**Testing**: script com `Flask test client` contra `manto_local` (paridade Jinja×API), fora de
`app.app_context()`; `tsc --noEmit` + `vite build` no frontend.

**Target Platform**: navegador (mobile-first, 320–430px), sem autenticação.

**Project Type**: web (Flask API + SPA React, monorepo `frontend/`).

**Performance Goals**: sem meta numérica nova — mesma carga que a tela Jinja atual atende hoje.

**Constraints**: robôs de prévia de link (WhatsApp/Open Graph) não executam JS — ver decisão em
`research.md` §4 (rota Jinja de detalhe permanece a fonte da prévia nesta fatia).

**Scale/Scope**: 5 telas (grade, categorias, categoria, detalhe, lista de desejos), 4 endpoints
JSON, 1 app frontend novo a configurar do zero (tema Tailwind próprio, roteador, query client).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: zero regra de negócio nova — os 4 endpoints replicam exatamente as
  queries já existentes em `app/catalogo/routes.py` (`index`, `categorias`, `categoria_detail`,
  `detail`), só trocando `render_template` por `jsonify`. A lista de desejos reaproveita
  literalmente a mesma lógica de `catalogo-wishlist.js` (localStorage, mesma chave
  `manto_catalogo_wishlist`, mesma URL de WhatsApp), portada para TS sem mudar o formato salvo
  (compatibilidade: visitante com lista salva na versão Jinja não perde a lista ao cair na
  versão React, mesma origem/`localStorage`). Componentes `@manto/ui` (`Button`, `Card`,
  `Input`, `Skeleton`) são reaproveitados — o app ganha um tema Tailwind próprio (tokens `bg`/
  `panel`/`accent`/etc. mapeados da paleta `--cat-*`), não componentes duplicados.
- **II (padrões de código)**: endpoints novos em `app/api/catalogo_read.py`, type hints/
  docstring; frontend com TypeScript estrito (sem `any`), componentes React pequenos por tela.
- **III (API first)**: 4 endpoints novos, 100% JSON, mesmo envelope de sucesso/erro do contrato
  geral (`specs/144-migracao-react-spa/contracts/api-conventions.md`) — a rota Jinja de detalhe
  segue existindo em paralelo só pelo motivo documentado no Summary (Open Graph), não por regra
  de negócio nova.
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos itens/categorias/
  fotos/relacionados entre a rota Jinja e a rota API, para os mesmos dados. Rotas Jinja
  `/catalogo/*` seguem funcionando sem alteração.
- **V (feedback)**: toda tela usa `useQuery` do TanStack Query — skeleton durante carregamento,
  estado de erro amigável, estado vazio amigável (catálogo sem itens, categoria sem item,
  busca sem resultado, lista de desejos vazia). Botão de favoritar/copiar link nunca fica
  "morto" — muda de aparência no clique (ícone preenchido, texto "Copiado!").
- **VIII (mobile-first)**: superfície pública de maior tráfego externo — todas as 5 telas
  conferidas em 320–430px antes de "pronto" (grade em coluna única, botão flutuante de lista de
  desejos não sobrepõe conteúdo, teclado virtual não esconde a busca).
- **IX (movimento)**: a galeria do detalhe recria a transição da feature 143 (cross-fade +
  altura animada + swipe) com Framer Motion (`useReducedMotion()`), documentado em
  `research.md` §3. Cards da grade e categorias usam hover/entrada suaves já existentes,
  portados para Tailwind/Framer Motion.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/161-catalogo-publico-leitura/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/catalogo-leitura-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/catalogo_read.py                  # NOVO — 4 endpoints JSON (list/categorias/categoria/detail)
app/api/__init__.py                       # + import de catalogo_read

frontend/apps/public/
├── package.json                          # + react-router-dom, @tanstack/react-query,
│                                          #   framer-motion, @manto/api-client, @manto/ui,
│                                          #   tailwindcss/postcss/autoprefixer
├── tailwind.config.ts                    # NOVO — tokens portados de _head_shared.html (--cat-*)
├── postcss.config.js                     # NOVO
├── src/
│   ├── main.tsx                          # + QueryClientProvider (troca do placeholder)
│   ├── App.tsx                           # NOVO — rotas /, /categorias, /categoria/:slug,
│   │                                     #   /:slug, /lista-desejos
│   ├── index.css                         # NOVO — @tailwind + fontes Fraunces/Manrope
│   ├── lib/
│   │   ├── catalogo.ts                   # NOVO — hooks useQuery (catálogo, categorias, etc.)
│   │   └── wishlist.ts                   # NOVO — porta catalogo-wishlist.js p/ TS (mesma chave)
│   ├── components/
│   │   ├── ProductCard.tsx               # NOVO — card reaproveitado por grade/categoria
│   │   ├── WishlistButton.tsx            # NOVO — botão favoritar (usado em card e detalhe)
│   │   ├── WishlistFloat.tsx             # NOVO — botão flutuante com contador
│   │   └── ProductGallery.tsx            # NOVO — galeria animada (Framer Motion)
│   └── pages/
│       ├── CatalogGridPage.tsx           # NOVO — grade geral + busca/filtro
│       ├── CategoriesPage.tsx            # NOVO — grade de categorias
│       ├── CategoryDetailPage.tsx        # NOVO — itens de uma categoria
│       ├── ProductDetailPage.tsx         # NOVO — detalhe + galeria + relacionados
│       └── WishlistPage.tsx              # NOVO — lista de desejos

scripts/db/verify_161_catalogo_publico_leitura.py  # NOVO: paridade Jinja×API (itens/categorias/
                                                     # detalhe/404), sem RBAC (rota pública)
```

**Structure Decision**: núcleo do backend fica só em `app/api/catalogo_read.py` (não em
`app/catalogo/routes.py`, que é Jinja legado intocado) — cada função do endpoint chama
literalmente as mesmas queries já escritas em `app/catalogo/routes.py`, copiadas (não
importadas: são rotas Flask com `render_template`, não helpers extraíveis; nenhuma tem lógica
condicional complexa o bastante para justificar uma extração `_ops` nova, mesma leitura feita
nas fatias de leitura anteriores — 145/154/156 — quando a lógica cabia inteira no endpoint).
`frontend/apps/public` recebe toda a configuração de app que faltava (hoje só tinha
`react`/`react-dom`) — mesma configuração de `apps/internal`, mas com tema Tailwind próprio.

## Complexity Tracking

Nenhuma violação nova.
