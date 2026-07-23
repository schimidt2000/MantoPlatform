# Implementation Plan: Design System Global e Shell de Aplicação (FASE A)

**Branch**: `173-design-system-shell` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/173-design-system-shell/spec.md`

## Summary

Devolver a identidade visual clássica da Manto ao beta React: tokens de tema centralizados
num preset Tailwind compartilhado, quatro componentes de shell em `@manto/ui`
(`AppLayout`, `PageHeader`, `DenseCard`, `MetricBadge`) e adoção do `AppLayout` em **todas
as 35 páginas** de `frontend/apps/internal` — incluindo o seletor "Ver como"
(impersonação de papel do SUPERADMIN), que ganha endpoints JSON reusando a mesma sessão
(`impersonate_role`) do sistema clássico. Nenhuma mudança de regra de negócio; o backend
só ganha 2 endpoints finos de auth.

## Technical Context

**Language/Version**: TypeScript 5.x / React 18 (frontend); Python 3.12 / Flask (backend)

**Primary Dependencies**: Vite, Tailwind CSS 3, TanStack Query 5, react-router-dom 6,
framer-motion (já usada no app internal; vira peerDependency de `@manto/ui`),
lucide-react (já em `@manto/ui`), Flask-Login (sessão existente)

**Storage**: nenhum novo — impersonação usa `session["impersonate_role"]` já existente

**Testing**: script de verificação funcional com test client Flask contra `manto_local`
(Postgres) para os endpoints novos; `npx tsc --noEmit` + `npm run build` no frontend

**Target Platform**: web (desktop + mobile ≥320px)

**Project Type**: web (SPA React + API Flask)

**Performance Goals**: shell não adiciona requisição bloqueante além do `/api/auth/me`
já existente (cacheado pelo TanStack Query)

**Constraints**: zero regressão funcional nas 35 páginas; `/login` fora do shell;
`prefers-reduced-motion` respeitado; sem CSS solto (só Tailwind + tokens)

**Scale/Scope**: ~4 componentes novos em `@manto/ui`, 1 preset Tailwind, 1 config de
navegação, 2 endpoints de API, 35 páginas tocadas (troca de wrapper + remoção de
cabeçalhos ad-hoc)

## Constitution Check

*GATE: aprovado. Re-checado após Phase 1 — sem violações.*

- **I. Reutilizar antes de criar** ✅ — tokens já parcialmente portados em
  `frontend/apps/internal/tailwind.config.ts` são PROMOVIDOS a preset compartilhado (não
  duplicados); `Card`/`Skeleton`/`Button` existentes são reusados pelos componentes novos;
  impersonação reusa a sessão e as regras do Jinja (`_IMPERSONABLE_ROLES` promovida a
  `app/constants.py`, fonte única).
- **II. Padrões de código** ✅ — TS estrito sem `any`; props tipadas; Python com type
  hints/docstrings.
- **III. API First** ✅ — endpoints novos são JSON puros em `app/api/auth.py`; sem
  `render_template`. As rotas Jinja `/impersonate/*` continuam existindo (strangler-fig).
- **IV. Não quebrar o que funciona** ✅ — adoção por wrapper preserva o conteúdo de cada
  página; portões `tsc`/build/verificação funcional antes do merge.
- **V. UI/UX com feedback** ✅ — skeleton no estado de carregamento do shell; pills do
  "Ver como" com estado pending; nenhum botão morto.
- **VII. BRL** ✅ — não toca valores monetários.
- **VIII. Mobile-first** ✅ — drawer mobile, sem overflow horizontal, alvos ≥44px.
- **IX. Movimento com propósito** ✅ — drawer/overlay com framer-motion +
  `useReducedMotion()`.

## Project Structure

### Documentation (this feature)

```text
specs/173-design-system-shell/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── auth-impersonate.md   # Contrato dos endpoints novos
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── constants.py                  # + IMPERSONABLE_ROLES (promovida de app/__init__.py)
├── __init__.py                   # rotas Jinja /impersonate/* passam a importar a constante
└── api/
    └── auth.py                   # + POST /api/auth/impersonate, DELETE /api/auth/impersonate

frontend/
├── packages/ui/
│   ├── tailwind-preset.ts        # NOVO — tokens globais (fonte única p/ apps)
│   ├── package.json              # + framer-motion peerDependency; exporta ./tailwind-preset
│   └── src/
│       ├── index.ts              # + exports novos
│       └── components/
│           ├── app-layout.tsx    # NOVO — shell (sidebar desktop + drawer mobile + footer)
│           ├── page-header.tsx   # NOVO
│           ├── dense-card.tsx    # NOVO
│           └── metric-badge.tsx  # NOVO
└── apps/internal/
    ├── tailwind.config.ts        # passa a consumir o preset (remove tokens duplicados)
    ├── src/
    │   ├── components/
    │   │   ├── AppShell.tsx      # NOVO — liga AppLayout a react-router + useAuth + nav
    │   │   └── RequireAuth.tsx   # intocado
    │   ├── lib/
    │   │   ├── navigation.tsx    # NOVO — grupos/itens/ícones/regras de visibilidade
    │   │   └── useAuth.ts        # + useImpersonate/useImpersonateReset
    │   ├── App.tsx               # rotas autenticadas ganham o AppShell (layout route)
    │   └── pages/*.tsx           # 35 páginas: adoção de PageHeader, remoção de headers ad-hoc
```

**Structure Decision**: componentes visuais puros ficam em `@manto/ui` (sem dependência
de react-router/TanStack — recebem dados e callbacks via props); a "cola" com roteamento,
auth e RBAC fica em `frontend/apps/internal/src` (`AppShell.tsx` + `lib/navigation.tsx`).
Tokens saem do config do app e viram `@manto/ui/tailwind-preset` para os dois apps
consumirem (o public só ganha acesso, sem mudança visual nesta fase).

## Decisões-chave (resumo do research.md)

1. **Cores**: adotar os hexes pedidos pelo usuário (`#1f1a30` sidebar, `#f4f5f7` fundo)
   como novos valores dos tokens `sidebar.bg`/`bg` já existentes — diferença imperceptível
   vs. Jinja (`#1e1635`/`#f4f3f8`), mantendo o restante da paleta portada (accent
   `#544596`, dourado `#f7d897`).
2. **Navegação**: config declarativa em `lib/navigation.tsx` espelhando o `base.html`
   (grupos Geral/Casting/Produção/Comercial/Financeiro/Ferramentas/Sistema) com predicado
   de visibilidade por papel efetivo; **apenas rotas SPA existentes** (itens Jinja-only
   ficam fora nesta fase). Papel efetivo no front = `impersonating ?? roles`.
3. **"Ver como"**: endpoints JSON novos (`POST`/`DELETE /api/auth/impersonate`) reusando
   `session["impersonate_role"]`; front invalida TODAS as queries após mudar (o RBAC dos
   endpoints já respeita a sessão). Papéis impersonáveis: CASTING, FIGURINO, COMERCIAL,
   FINANCEIRO, ENSAIO (paridade com Jinja).
4. **`/api/auth/me` ganha `is_educamanto_responsavel`** — necessário para paridade de
   visibilidade de Pipeline/Comissões no menu (reusa o helper existente).
5. **Adoção nas páginas**: layout route no `App.tsx` (`<Route element={<AppShell/>}>`
   com `<Outlet/>`) em vez de editar wrapper página a página; cada página então troca seu
   header ad-hoc por `PageHeader` e remove botões de navegação improvisados (ex.: fileira
   de botões do Dashboard, que a sidebar substitui).
6. **Tooltips**: `title` + `aria-label` nos botões só-ícone (sem dependência Radix nova
   nesta fase — YAGNI; Dialog/Tooltip ricos podem vir na FASE B se necessário).

## Complexity Tracking

Sem violações da constituição — tabela não aplicável.
