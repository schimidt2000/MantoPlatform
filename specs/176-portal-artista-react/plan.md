# Implementation Plan: Portal do Artista — App React (fatia 1)

**Branch**: `176-portal-artista-react` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/176-portal-artista-react/spec.md`

## Summary

Primeira fatia do app React isolado do Portal do Artista (`frontend/apps/portal`, hoje só
scaffold), cobrindo as 5 telas pedidas: Login, Minha Agenda (futuros + histórico), Meus Convites
de Casting (aceitar/recusar), Minha Ficha de Figurino e Atualização de Fotos/Documentos. App
mobile-first (Princípio VIII), com identidade visual própria (não herda o preset do `internal`
— mesmo padrão do `public`). Autenticação: sessão Flask própria do talento (`session["talent_id"]`,
já usada pelo portal Jinja) — login pela API seta o MESMO cookie de sessão, então um talento
autenticado em uma versão continua autenticado na outra. Backend: núcleo de negócio hoje só
dentro das views de `app/talent_portal/routes.py` é extraído para `app/talent_portal/portal_ops.py`
(a view Jinja passa a chamar essas funções, sem duplicar lógica), exposto por um blueprint de API
novo `app/api/portal_*.py`, RBAC "é o dono do recurso" validado por função. Fora de escopo desta
fatia (documentado no spec): primeiro acesso, troca de senha obrigatória, aceite de termos,
esqueci a senha, avaliação de eventos, edição de perfil além de fotos/CNH — continuam só na
versão clássica; login de talento nessas condições é direcionado para lá.

## Technical Context

**Language/Version**: TypeScript 5.x / React 18 (frontend); Python 3.12 / Flask (backend)

**Primary Dependencies**: mesmo conjunto do `apps/public` (react-router-dom, TanStack Query,
framer-motion, react-hook-form+zod, `@manto/ui`, `@manto/api-client`), Tailwind CSS + preset
próprio (tokens do portal clássico, `app/templates/portal/*`) em vez do preset do `internal`.
`@manto/money` para exibir cachê/situação de pagamento no histórico da Agenda.

**Storage**: sem mudança de schema — `Talent`, `EventRole`, `CalendarEvent`, `FigurinoSheet` já
têm todos os campos necessários.

**Testing**: script de verificação funcional com test client Flask contra `manto_local`
(Postgres), cobrindo os endpoints `/api/portal/*` novos (login/logout/me, agenda, convites,
figurino, fotos/documentos) com sucesso/erro/dono-do-recurso; `npx tsc --noEmit` + `npm run
build` em `frontend/apps/portal`; conferência visual OBRIGATÓRIA em viewport mobile (375px,
320px) via Playwright headless — superfície é mobile-first (Princípio VIII).

**Target Platform**: web mobile-first (320–430px prioritário; desktop é bônus, não o alvo).

**Project Type**: web (SPA React isolada + API Flask) — 3º bundle do frontend monorepo, ao lado
de `internal`/`public`.

**Performance Goals**: sessão abre e Agenda carrega em até 30s em conexão de celular comum
(SC-001) — sem novas queries N+1; endpoints reaproveitam os mesmos filtros já usados pelas views
Jinja (`EventRole.filter_by(talent_id=...)`).

**Constraints**: zero regressão nas rotas Jinja de `app/talent_portal` (paridade obrigatória);
sessão do app novo usa a MESMA chave de sessão do portal clássico (não um mecanismo paralelo);
login bloqueado (redirecionado à versão clássica) quando `must_change_password` ou
`terms_accepted_at` pendente — nunca deixa o talento "preso" sem alternativa; ação de recusar
convite exige confirmação (`window.confirm`, padrão do projeto) por ser difícil de desfazer;
upload de foto/CNH reaproveita `app/storage.py` (mesma abstração local/S3 já usada pelo
`app/cadastro`), formatos/limites idênticos ao cadastro público.

**Scale/Scope**: 1 módulo de negócio novo (`app/talent_portal/portal_ops.py`), 4 módulos de API
novos (`app/api/portal_auth.py`, `portal_agenda.py`, `portal_figurino.py`, `portal_profile.py`),
app novo completo em `frontend/apps/portal` (tailwind preset próprio, router, 5 páginas: Login,
Agenda, Convites, Figurino, FotosDocumentos).

## Constitution Check

*GATE: aprovado. Re-checado após Phase 1 — sem violações.*

- **I. Reutilizar antes de criar** ✅ — lógica de agenda/convites/figurino/fotos extraída das
  views Jinja existentes para `portal_ops.py` (fonte única, chamada por Jinja e API); upload
  reusa `app/storage.py`; `_now_sp()`/regras de convite/figurino idênticas às já existentes.
- **II. Padrões de código** ✅ — `portal_ops.py` com type hints/docstring Google style; TS
  estrito sem `any`.
- **III. API First** ✅ — `app/api/portal_*.py` é JSON puro; auth por função
  (`portal_api_login_required`), não decorator Flask-Login (Talent não é `User`/Flask-Login).
- **IV. Não quebrar o que funciona** ✅ — `app/talent_portal/routes.py` passa a delegar a
  `portal_ops.py` sem mudar comportamento; verificação funcional cobre os dois lados.
- **V. UI/UX com feedback** ✅ — Skeleton/loading em toda tela nova; confirmação antes de
  recusar convite; toasts de erro amigáveis (upload inválido, sessão expirada).
- **VII. BRL** — cachê no histórico da Agenda usa `@manto/money` (`formatBRL`), fonte única.
- **VIII. Mobile-first (NÃO-NEGOCIÁVEL)** ✅ — é o requisito central desta fatia: as 5 telas
  são desenhadas mobile-first, conferidas em 320–430px antes de "pronto", alvos de toque ≥44px.
- **IX. Movimento com propósito** ✅ — transições de lista/tela via Framer Motion, respeitando
  `useReducedMotion()`.

## Project Structure

### Documentation (this feature)

```text
specs/176-portal-artista-react/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── talent_portal/
│   ├── routes.py         # Jinja legado — passa a chamar portal_ops.py (sem duplicar lógica)
│   └── portal_ops.py     # NOVO — núcleo de negócio: agenda, convites, figurino, fotos/CNH
└── api/
    ├── portal_auth.py     # NOVO — POST login/logout, GET me (sessão talent_id)
    ├── portal_agenda.py   # NOVO — GET agenda, POST invites/<id>/accept|reject
    ├── portal_figurino.py # NOVO — GET events/<id>/figurino
    └── portal_profile.py  # NOVO — POST photos, POST document (CNH)

frontend/apps/portal/       # até agora só scaffold (index.html, main.tsx, vite.config.ts)
├── package.json             # ganha as deps do padrão public (router, query, ui, api-client, money)
├── tailwind.config.ts        # NOVO — preset próprio (tokens do portal clássico)
├── postcss.config.js         # NOVO
└── src/
    ├── App.tsx                # NOVO — router (login público + shell autenticado)
    ├── components/
    │   └── PortalShell.tsx     # NOVO — nav inferior mobile (Agenda/Convites/Fotos), header
    ├── lib/
    │   ├── portalAuth.ts        # NOVO — useLogin/useLogout/useCurrentTalent
    │   ├── portalAgenda.ts       # NOVO — useAgenda, useAcceptInvite, useRejectInvite
    │   ├── portalFigurino.ts     # NOVO — useFigurino(eventId)
    │   └── portalProfile.ts      # NOVO — usePhotoUpload, useDocumentUpload
    └── pages/
        ├── PortalLoginPage.tsx
        ├── PortalAgendaPage.tsx
        ├── PortalConvitesPage.tsx
        ├── PortalFigurinoPage.tsx
        └── PortalFotosDocumentosPage.tsx
```

**Structure Decision**: 3º bundle do monorepo frontend, paralelo a `internal`/`public`, sem
depender de nenhum dos dois (identidade visual própria, sessão própria). Backend segue o mesmo
padrão de camadas do resto do projeto (`routes.py` Jinja → `*_ops.py` → models; API fina por
cima do mesmo `*_ops.py`).

## Complexity Tracking

*Nenhuma violação da constituição — seção não se aplica.*
