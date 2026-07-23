# Tasks: Design System Global e Shell de Aplicação (FASE A)

**Input**: Design documents from `specs/173-design-system-shell/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-impersonate.md

**Organização**: tarefas agrupadas por user story para permitir implementação e teste
independentes. Verificação funcional automatizada só para o backend (padrão do projeto);
frontend valida por `tsc`/build + conferência no app real.

## Phase 1: Setup — preset de tema compartilhado

**Purpose**: fonte única de tokens consumível pelos dois apps (base de TODAS as stories)

- [X] T001 Criar `frontend/packages/ui/tailwind-preset.ts` com os tokens promovidos de `frontend/apps/internal/tailwind.config.ts` + valores da spec (`sidebar.bg #1f1a30`, `bg #f4f5f7`, paleta accent/gold/verde/vermelho/azul, radii, sombras); exportar via `"./tailwind-preset"` em `frontend/packages/ui/package.json` e adicionar `framer-motion` a peerDependencies
- [X] T002 Consumir o preset em `frontend/apps/internal/tailwind.config.ts` (remover tokens duplicados, manter só `content` + `presets`) e em `frontend/apps/public/tailwind.config.ts` (aditivo, sem mudança visual — conferir que classes existentes do public seguem resolvendo)
- [X] T003 Validar que nada quebrou: `npx tsc --noEmit` + `npm run build` em `frontend/apps/internal` e `frontend/apps/public`

**Checkpoint**: builds verdes com preset compartilhado — pronto para componentes

---

## Phase 2: Foundational — API de identidade estendida

**Purpose**: campos de `/api/auth/me` que a navegação RBAC do shell exige (bloqueia US1 e US2)

- [X] T004 Promover `_IMPERSONABLE_ROLES` de `app/__init__.py` para `IMPERSONABLE_ROLES` em `app/constants.py`; rotas Jinja `/impersonate/*` importam a constante (fonte única)
- [X] T005 Estender `serialize_user` em `app/api/auth.py` com `is_real_superadmin` e `is_educamanto_responsavel` (reusar o helper do context processor de `app/__init__.py:300`); atualizar `AuthUser` em `frontend/apps/internal/src/lib/types.ts`

**Checkpoint**: `/api/auth/me` fornece tudo que o menu precisa

---

## Phase 3: User Story 1 — Shell institucional em todas as telas (P1) 🎯 MVP

**Goal**: sidebar roxa/drawer mobile idêntica em identidade ao Jinja, em 100% das rotas autenticadas, sem regressão

**Independent Test**: visitar todas as rotas logado (desktop + 375px) — shell presente, item ativo correto, menu respeita papel, telas funcionam

- [X] T006 [US1] Criar `frontend/packages/ui/src/components/app-layout.tsx` — `AppLayout` com sidebar fixa desktop (`bg-sidebar-bg`), drawer mobile com overlay (framer-motion + `useReducedMotion`, fecha em navegação/Esc/tocar fora/resize p/ desktop), brand tipográfica Manto, seções com label, `renderLink` render prop, slot `footer`; nav rola internamente com footer fixo; botões só-ícone com `aria-label` + `title`; exportar em `frontend/packages/ui/src/index.ts`
- [X] T007 [P] [US1] Criar `frontend/apps/internal/src/lib/navigation.tsx` — config declarativa dos grupos/itens portada de `app/templates/base.html` (tabela research.md §3: só rotas SPA; `/catalogo/` como link externo), com `isActive(pathname)` e `isVisible(user)` usando papel efetivo (`impersonating ?? roles`), flags `is_educamanto_responsavel` e revendedor-only, ícones lucide-react equivalentes aos SVGs do Jinja
- [X] T008 [US1] Criar `frontend/apps/internal/src/components/AppShell.tsx` — compõe `AppLayout` + `NavLink` do react-router (via `renderLink`) + `useCurrentUser` + `navigation.tsx` + `<Outlet/>`; skeleton do shell enquanto `/api/auth/me` carrega (FR-012); rodapé com usuário (nome, papéis/papel simulado, avatar inicial) e botão Sair (`useLogout`)
- [X] T009 [US1] Refatorar `frontend/apps/internal/src/App.tsx` para layout route: `<Route element={<RequireAuth><AppShell/></RequireAuth>}>` englobando todas as rotas autenticadas (remove os 34 `<RequireAuth>` repetidos); `/login` fora; fallback `*` mantido
- [X] T010 [US1] Varrer as 35 páginas em `frontend/apps/internal/src/pages/` removendo cabeçalhos/navegação ad-hoc que conflitam com o shell (fileira de botões e logout do `DashboardPage.tsx`, links "Voltar" redundantes de topo, wrappers `mx-auto max-w-*` conflitantes — padronizar container do conteúdo no shell)
- [X] T011 [US1] Verificação: `npx tsc --noEmit` + `npm run build` (internal); subir app real (`.\scripts\db\run-local.ps1` + `npm run dev:internal`) e conferir shell em desktop e 375px nas rotas principais

**Checkpoint**: sistema inteiro com a moldura institucional — MVP entregue

---

## Phase 4: User Story 2 — "Ver como" no rodapé da sidebar (P2)

**Goal**: SUPERADMIN simula papéis pela sidebar React com mesmo efeito do Jinja

**Independent Test**: SUPERADMIN ativa CASTING → menu/telas mudam; reset → volta; não-SUPERADMIN não vê o bloco

- [X] T012 [US2] Adicionar `POST /api/auth/impersonate` e `DELETE /api/auth/impersonate` em `app/api/auth.py` conforme `contracts/auth-impersonate.md` (RBAC por função: SUPERADMIN real; 400 papel inválido; retorna `serialize_user`; docstrings + type hints)
- [X] T013 [P] [US2] Criar `specs/173-design-system-shell/verify_173.py` — test client contra `manto_local` (requests FORA de `app_context`): login SUPERADMIN → POST cada papel válido (200, `impersonating` correto) → efeito RBAC real (ex.: `/api/financeiro/dashboard` 403 sob CASTING; menu-relevante) → papel inválido 400 → DELETE 200 idempotente → não-SUPERADMIN 403 → sem sessão 401 → campos novos de `/api/auth/me`; rodar e passar 100%
- [X] T014 [US2] Hooks `useImpersonate`/`useImpersonateReset` em `frontend/apps/internal/src/lib/useAuth.ts` (sucesso: `setQueryData(ME_KEY)` + `invalidateQueries()` global); bloco "Ver como:" com pills (CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO + "Admin" para reset quando ativo) no rodapé do `AppShell.tsx`, visível só para `is_real_superadmin`, com estado pending nos botões e destaque dourado do papel ativo
- [X] T015 [US2] Verificação: rodar `verify_173.py` (backend) + conferir no app real o fluxo completo de simulação/reset e sumiço do bloco para não-SUPERADMIN

**Checkpoint**: paridade de capacidade com o Jinja no shell

---

## Phase 5: User Story 3 — Vocabulário visual denso (P2)

**Goal**: PageHeader/DenseCard/MetricBadge exportados e adotados; zero páginas de fundo branco genérico

**Independent Test**: componentes exportados por `@manto/ui`, cada um com uso real; todas as páginas com `PageHeader` sobre fundo cinza

- [X] T016 [P] [US3] Criar `frontend/packages/ui/src/components/page-header.tsx` (`title`, `subtitle?`, `breadcrumbs?`, `actions?`, `filters?` — tipografia densa, ações à direita, mobile-first) e exportar no index
- [X] T017 [P] [US3] Criar `frontend/packages/ui/src/components/dense-card.tsx` (composto sobre `Card`: cabeçalho compacto, `headerRight?`, `stats?`, divisões `divide-line`, `padding compact|normal`) e `frontend/packages/ui/src/components/metric-badge.tsx` (`tone` neutral/accent/green/red/blue/gold, `size` xs/sm, junção com "•"); exportar ambos no index
- [X] T018 [US3] Adotar `PageHeader` em todas as páginas de `frontend/apps/internal/src/pages/` (título + breadcrumbs onde há hierarquia + ações primárias movidas do corpo p/ o header); usos reais mínimos: `MetricBadge` nas medidas em `TalentsListPage.tsx`/`TalentDetailPage.tsx` e status em `AgendaPage.tsx`; `DenseCard` nos cards do `DashboardPage.tsx` e KPIs do `FinanceiroDashboardPage.tsx`
- [X] T019 [US3] Verificação: `npx tsc --noEmit` + `npm run build` (internal e public); conferência visual desktop + 375px (sem overflow horizontal, alvos ≥44px)

**Checkpoint**: FASE A completa — molde pronto para a FASE B

---

## Phase 6: Polish & Cross-Cutting

- [X] T020 `ruff check app/` limpo nos arquivos tocados; ESLint/format nos TS/TSX novos; revisar ausência de CSS solto/estilos inline
- [X] T021 Atualizar `docs/changelog.html` (entrada: visual institucional do beta + "Ver como" no painel React) e republicar no MESMO artifact existente
- [X] T022 Commit atômico final, merge em `main` e push (stage explícito, nunca `git add -A`)

---

## Dependencies & Execution Order

- **Phase 1 → tudo** (tokens são base); **Phase 2 → US1/US2** (campos do `/me`)
- **US1 (P3)**: núcleo do MVP — precisa de T001–T005
- **US2 (P4)**: independente de US3; T012/T013 (backend) paralelos a US1 se desejado; T014 depende de T008 (rodapé do AppShell)
- **US3 (P5)**: T016/T017 paralelos entre si e a US2; T018 depende de T009 (shell aplicado)
- **Parallel opportunities**: T007 ∥ T006; T013 ∥ T012→depois; T016 ∥ T017 ∥ T014

## Implementation Strategy

MVP = Phases 1–3 (shell em tudo). Depois US2 (capacidade), US3 (vocabulário denso),
polish. Cada checkpoint = commit atômico com builds verdes (Princípio IV).
